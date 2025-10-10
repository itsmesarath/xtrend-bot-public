from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import json
import requests
from collections import defaultdict, deque
import numpy as np

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class APIConfig(BaseModel):
    openrouter_key: Optional[str] = None
    binance_key: Optional[str] = None
    binance_secret: Optional[str] = None
    ai_model: str = "meta-llama/llama-3.3-70b-instruct"

class MarketData(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    buy_volume: float
    sell_volume: float

class VolumeProfileLevel(BaseModel):
    price: float
    volume: float
    is_poc: bool = False
    is_lvn: bool = False
    is_hvn: bool = False

class VolumeProfile(BaseModel):
    symbol: str
    timestamp: datetime
    poc: float
    vah: float
    val: float
    levels: List[VolumeProfileLevel]
    total_volume: float

class OrderFlowMetrics(BaseModel):
    symbol: str
    timestamp: datetime
    cvd: float
    cvd_trend: str  # "positive", "negative", "neutral"
    big_prints: List[Dict[str, Any]]
    buy_volume: float
    sell_volume: float
    imbalance_ratio: float

class TradingSignal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str
    signal_type: str  # "BUY" or "SELL"
    model: str  # "TREND_CONTINUATION" or "MEAN_REVERSION"
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence_score: int
    market_state: str
    key_level: str
    order_flow: str
    reasoning: str
    risk_reward: str
    timeframe_confluence: str

class AIAnalysis(BaseModel):
    symbol: str
    timestamp: datetime
    market_state: str
    key_levels: List[float]
    reasoning: str
    opportunity: Optional[str] = None

# ==================== GLOBAL STATE ====================

class MarketDataStore:
    def __init__(self):
        self.candles = defaultdict(lambda: deque(maxlen=1000))  # Store last 1000 candles per symbol
        self.trades = defaultdict(lambda: deque(maxlen=5000))  # Store last 5000 trades per symbol
        self.volume_profiles = {}  # Current volume profile per symbol
        self.order_flow = {}  # Current order flow metrics per symbol
        self.cvd_values = defaultdict(lambda: deque(maxlen=500))  # CVD history
        self.ai_enabled = False
        self.last_ai_analysis = {}
        self.active_connections = []
        
market_store = MarketDataStore()
api_config = APIConfig()
binance_fetcher = None  # Will be initialized when API keys are provided
binance_simulator = None  # Fallback simulator

# ==================== BINANCE DATA ====================

import random
import time
from binance import AsyncClient, BinanceSocketManager
from binance.enums import *

class BinanceDataFetcher:
    \"\"\"Real Binance data fetcher using API\"\"\"
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = None
        self.bm = None
        self.symbols = [\"BTCUSDT\", \"ETHUSDT\", \"LTCUSDT\", \"DOGEUSDT\"]
        self.running = False
        self.tasks = []
        
    async def start(self):
        \"\"\"Initialize Binance client and start streaming\"\"\"
        try:
            self.client = await AsyncClient.create(self.api_key, self.api_secret)
            self.bm = BinanceSocketManager(self.client)
            self.running = True
            
            logger.info(\"Connected to Binance API - Starting real data stream...\")\n            
            # Start kline streams for each symbol\n            for symbol in self.symbols:\n                task = asyncio.create_task(self.stream_klines(symbol))\n                self.tasks.append(task)\n                \n                task = asyncio.create_task(self.stream_trades(symbol))\n                self.tasks.append(task)\n                \n        except Exception as e:\n            logger.error(f\"Failed to connect to Binance: {e}\")\n            self.running = False\n            raise\n    \n    async def stream_klines(self, symbol: str):\n        \"\"\"Stream 1-minute candles for a symbol\"\"\"\n        try:\n            async with self.bm.kline_socket(symbol=symbol, interval='1m') as stream:\n                while self.running:\n                    res = await stream.recv()\n                    kline = res['k']\n                    \n                    # Only process closed candles\n                    if kline['x']:  # is candle closed\n                        candle = {\n                            \"symbol\": symbol,\n                            \"timestamp\": datetime.fromtimestamp(kline['T'] / 1000, tz=timezone.utc),\n                            \"open\": float(kline['o']),\n                            \"high\": float(kline['h']),\n                            \"low\": float(kline['l']),\n                            \"close\": float(kline['c']),\n                            \"volume\": float(kline['v']),\n                            \"buy_volume\": float(kline['V']),  # Taker buy base asset volume\n                            \"sell_volume\": float(kline['v']) - float(kline['V'])\n                        }\n                        \n                        market_store.candles[symbol].append(candle)\n                        \n                        # Calculate volume profile and order flow\n                        await calculate_volume_profile(symbol)\n                        await calculate_order_flow(symbol)\n                        \n                        # Broadcast update\n                        await broadcast_market_update(symbol)\n                        \n                        # AI analysis if enabled\n                        if market_store.ai_enabled:\n                            await analyze_with_ai(symbol, candle)\n                            \n        except Exception as e:\n            logger.error(f\"Error in kline stream for {symbol}: {e}\")\n    \n    async def stream_trades(self, symbol: str):\n        \"\"\"Stream individual trades for order flow analysis\"\"\"\n        try:\n            async with self.bm.trade_socket(symbol=symbol) as stream:\n                while self.running:\n                    res = await stream.recv()\n                    \n                    trade = {\n                        \"symbol\": symbol,\n                        \"timestamp\": datetime.fromtimestamp(res['T'] / 1000, tz=timezone.utc),\n                        \"price\": float(res['p']),\n                        \"quantity\": float(res['q']),\n                        \"side\": \"buy\" if res['m'] else \"sell\",  # m = is buyer market maker\n                        \"is_big_print\": False  # Will be determined in order flow calc\n                    }\n                    \n                    market_store.trades[symbol].append(trade)\n                    \n        except Exception as e:\n            logger.error(f\"Error in trade stream for {symbol}: {e}\")\n    \n    async def stop(self):\n        \"\"\"Stop all streams and close client\"\"\"\n        self.running = False\n        for task in self.tasks:\n            task.cancel()\n        if self.client:\n            await self.client.close_connection()\n\nclass BinanceDataSimulator:
    def __init__(self):
        self.symbols = ["BTCUSDT", "ETHUSDT", "LTCUSDT", "DOGEUSDT"]
        self.base_prices = {
            "BTCUSDT": 42000.0,
            "ETHUSDT": 2200.0,
            "LTCUSDT": 68.0,
            "DOGEUSDT": 0.08
        }
        self.current_prices = self.base_prices.copy()
        self.running = False
        
    async def generate_candle(self, symbol: str) -> Dict:
        """Generate a realistic candle with volume"""
        current = self.current_prices[symbol]
        volatility = current * 0.002  # 0.2% volatility
        
        open_price = current
        close_price = current + random.gauss(0, volatility)
        high_price = max(open_price, close_price) + abs(random.gauss(0, volatility/2))
        low_price = min(open_price, close_price) - abs(random.gauss(0, volatility/2))
        
        volume = random.uniform(100, 500)
        buy_volume = volume * random.uniform(0.4, 0.6)
        sell_volume = volume - buy_volume
        
        self.current_prices[symbol] = close_price
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": round(volume, 2),
            "buy_volume": round(buy_volume, 2),
            "sell_volume": round(sell_volume, 2)
        }
    
    async def generate_trade(self, symbol: str) -> Dict:
        """Generate a realistic trade"""
        current = self.current_prices[symbol]
        price = current + random.gauss(0, current * 0.0005)
        quantity = random.uniform(0.01, 2.0)
        side = random.choice(["buy", "sell"])
        is_big_print = random.random() < 0.05  # 5% chance of big print
        
        if is_big_print:
            quantity *= random.uniform(5, 15)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc),
            "price": round(price, 2),
            "quantity": round(quantity, 4),
            "side": side,
            "is_big_print": is_big_print
        }
    
    async def start_streaming(self):
        """Start streaming simulated data"""
        self.running = True
        logger.info("Starting Binance data simulation...")
        
        while self.running:
            try:
                for symbol in self.symbols:
                    # Generate candle every 10 seconds for demo purposes
                    if len(market_store.candles[symbol]) == 0 or \
                       (datetime.now(timezone.utc) - market_store.candles[symbol][-1]['timestamp']).seconds >= 10:
                        candle = await self.generate_candle(symbol)
                        market_store.candles[symbol].append(candle)
                        
                        # Calculate volume profile and order flow
                        await calculate_volume_profile(symbol)
                        await calculate_order_flow(symbol)
                        
                        # Broadcast update to websocket clients
                        await broadcast_market_update(symbol)
                        
                        # AI analysis if enabled
                        if market_store.ai_enabled:
                            await analyze_with_ai(symbol, candle)
                    
                    # Generate trades
                    trade = await self.generate_trade(symbol)
                    market_store.trades[symbol].append(trade)
                    
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in data streaming: {e}")
                await asyncio.sleep(5)
    
    def stop_streaming(self):
        self.running = False

# ==================== DATA SOURCE MANAGER ====================

async def start_data_stream():
    \"\"\"Start appropriate data stream based on configuration\"\"\"\n    global binance_fetcher, binance_simulator\n    \n    if api_config.binance_key and api_config.binance_secret:\n        # Use real Binance data\n        try:\n            logger.info(\"Binance API keys configured - connecting to live data...\")\n            binance_fetcher = BinanceDataFetcher(api_config.binance_key, api_config.binance_secret)\n            await binance_fetcher.start()\n        except Exception as e:\n            logger.error(f\"Failed to connect to Binance API: {e}. Falling back to simulator.\")\n            binance_simulator = BinanceDataSimulator()\n            asyncio.create_task(binance_simulator.start_streaming())\n    else:\n        # Use simulator\n        logger.info(\"No Binance API keys - using simulated data\")\n        binance_simulator = BinanceDataSimulator()\n        asyncio.create_task(binance_simulator.start_streaming())\n\nasync def restart_data_stream():\n    \"\"\"Restart data stream when configuration changes\"\"\"\n    global binance_fetcher, binance_simulator\n    \n    # Stop existing streams\n    if binance_fetcher:\n        await binance_fetcher.stop()\n        binance_fetcher = None\n    \n    if binance_simulator:\n        binance_simulator.stop_streaming()\n        binance_simulator = None\n    \n    # Start new stream\n    await start_data_stream()\n\n# ==================== VOLUME PROFILE CALCULATIONS ====================

async def calculate_volume_profile(symbol: str) -> Optional[VolumeProfile]:
    """Calculate volume profile from candle data"""
    try:
        candles = list(market_store.candles[symbol])
        if len(candles) < 10:
            return None
        
        # Use last 50 candles for profile calculation
        recent_candles = candles[-50:]
        
        # Find price range
        all_prices = []
        for c in recent_candles:
            all_prices.extend([c['high'], c['low']])
        
        min_price = min(all_prices)
        max_price = max(all_prices)
        
        # Create price bins (50 bins)
        num_bins = 50
        bin_size = (max_price - min_price) / num_bins
        
        if bin_size == 0:
            return None
        
        # Volume by price
        volume_by_price = defaultdict(float)
        
        for candle in recent_candles:
            # Distribute volume across the candle's range
            candle_range = candle['high'] - candle['low']
            if candle_range == 0:
                bin_idx = int((candle['close'] - min_price) / bin_size)
                bin_price = min_price + (bin_idx * bin_size) + (bin_size / 2)
                volume_by_price[round(bin_price, 2)] += candle['volume']
            else:
                # Distribute proportionally
                num_price_levels = max(1, int(candle_range / bin_size))
                vol_per_level = candle['volume'] / num_price_levels
                
                for i in range(num_price_levels):
                    price = candle['low'] + (i * bin_size)
                    bin_idx = int((price - min_price) / bin_size)
                    bin_price = min_price + (bin_idx * bin_size) + (bin_size / 2)
                    volume_by_price[round(bin_price, 2)] += vol_per_level
        
        # Find POC (Point of Control)
        poc_price = max(volume_by_price.items(), key=lambda x: x[1])[0]
        poc_volume = volume_by_price[poc_price]
        
        # Calculate Value Area (70% of volume)
        total_volume = sum(volume_by_price.values())
        target_volume = total_volume * 0.70
        
        sorted_levels = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        
        value_area_prices = []
        accumulated_volume = 0
        
        for price, vol in sorted_levels:
            value_area_prices.append(price)
            accumulated_volume += vol
            if accumulated_volume >= target_volume:
                break
        
        vah = max(value_area_prices)
        val = min(value_area_prices)
        
        # Identify LVNs and HVNs
        avg_volume = total_volume / len(volume_by_price)
        lvn_threshold = avg_volume * 0.5
        hvn_threshold = avg_volume * 1.5
        
        levels = []
        for price, vol in sorted(volume_by_price.items()):
            level = VolumeProfileLevel(
                price=price,
                volume=vol,
                is_poc=(price == poc_price),
                is_lvn=(vol < lvn_threshold),
                is_hvn=(vol > hvn_threshold)
            )
            levels.append(level)
        
        profile = VolumeProfile(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            poc=poc_price,
            vah=vah,
            val=val,
            levels=levels,
            total_volume=total_volume
        )
        
        market_store.volume_profiles[symbol] = profile
        return profile
        
    except Exception as e:
        logger.error(f"Error calculating volume profile for {symbol}: {e}")
        return None

# ==================== ORDER FLOW CALCULATIONS ====================

async def calculate_order_flow(symbol: str) -> Optional[OrderFlowMetrics]:
    """Calculate order flow metrics including CVD and big prints"""
    try:
        trades = list(market_store.trades[symbol])
        if len(trades) < 10:
            return None
        
        # Calculate CVD (Cumulative Volume Delta)
        cvd = 0
        buy_volume = 0
        sell_volume = 0
        big_prints = []
        
        # Calculate average trade size for big print detection
        trade_sizes = [t['quantity'] for t in trades[-100:]]
        avg_size = np.mean(trade_sizes) if trade_sizes else 1.0
        big_print_threshold = avg_size * 3
        
        for trade in trades[-100:]:  # Last 100 trades
            if trade['side'] == 'buy':
                cvd += trade['quantity']
                buy_volume += trade['quantity'] * trade['price']
            else:
                cvd -= trade['quantity']
                sell_volume += trade['quantity'] * trade['price']
            
            # Detect big prints
            if trade['quantity'] >= big_print_threshold:
                big_prints.append({
                    'timestamp': trade['timestamp'].isoformat(),
                    'price': trade['price'],
                    'quantity': trade['quantity'],
                    'side': trade['side']
                })
        
        # Store CVD history
        market_store.cvd_values[symbol].append(cvd)
        
        # Determine CVD trend
        cvd_history = list(market_store.cvd_values[symbol])
        if len(cvd_history) >= 2:
            if cvd_history[-1] > cvd_history[-2]:
                cvd_trend = "positive"
            elif cvd_history[-1] < cvd_history[-2]:
                cvd_trend = "negative"
            else:
                cvd_trend = "neutral"
        else:
            cvd_trend = "neutral"
        
        # Calculate imbalance ratio
        total_vol = buy_volume + sell_volume
        imbalance_ratio = (buy_volume / total_vol * 100) if total_vol > 0 else 50.0
        
        metrics = OrderFlowMetrics(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            cvd=round(cvd, 4),
            cvd_trend=cvd_trend,
            big_prints=big_prints[-5:],  # Last 5 big prints
            buy_volume=round(buy_volume, 2),
            sell_volume=round(sell_volume, 2),
            imbalance_ratio=round(imbalance_ratio, 2)
        )
        
        market_store.order_flow[symbol] = metrics
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating order flow for {symbol}: {e}")
        return None

# ==================== AI ANALYSIS ====================

async def analyze_with_ai(symbol: str, candle: Dict):
    """Analyze market with AI and potentially generate signals"""
    try:
        if not api_config.openrouter_key:
            logger.warning("OpenRouter API key not configured")
            return
        
        profile = market_store.volume_profiles.get(symbol)
        order_flow = market_store.order_flow.get(symbol)
        
        if not profile or not order_flow:
            return
        
        # Build AI prompt
        prompt = f"""You are monitoring {symbol} using Auction Market Theory principles.

**New Candle Data**:
- Timeframe: 1m
- Open: {candle['open']}, High: {candle['high']}, Low: {candle['low']}, Close: {candle['close']}
- Volume: {candle['volume']}
- Buy volume: {candle['buy_volume']}, Sell volume: {candle['sell_volume']}

**Volume Profile**:
- POC: {profile.poc}
- VAH: {profile.vah}
- VAL: {profile.val}
- Total volume: {profile.total_volume}

**Order Flow**:
- CVD: {order_flow.cvd}
- CVD trend: {order_flow.cvd_trend}
- Buy/Sell ratio: {order_flow.imbalance_ratio:.1f}% buy
- Recent big prints: {len(order_flow.big_prints)}

**Question**: Does this candle create or confirm a trading signal according to Fabio's Auction Market Theory playbook?

Check for:
1. Is price at a key LVN?
2. Is there order flow aggression in the expected direction?
3. Does the setup match Model 1 (Trend) or Model 2 (Mean Reversion)?
4. What is the confidence level? (0-100%)

Respond in JSON format:
{{
  "signal_detected": true/false,
  "direction": "BUY" or "SELL" or "NONE",
  "model": "TREND_CONTINUATION" or "MEAN_REVERSION" or "NONE",
  "confidence_score": 0-100,
  "entry_price": number,
  "stop_loss": number,
  "take_profit": number,
  "reasoning": "brief explanation",
  "market_state": "BALANCE" or "IMBALANCE"
}}
"""
        
        # Call OpenRouter API
        headers = {
            "Authorization": f"Bearer {api_config.openrouter_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": api_config.ai_model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # Try to parse JSON response
            try:
                # Extract JSON from response (might be wrapped in markdown)
                if '```json' in ai_response:
                    ai_response = ai_response.split('```json')[1].split('```')[0].strip()
                elif '```' in ai_response:
                    ai_response = ai_response.split('```')[1].split('```')[0].strip()
                
                signal_data = json.loads(ai_response)
                
                # If signal detected, create and store it
                if signal_data.get('signal_detected') and signal_data.get('confidence_score', 0) >= 70:
                    signal = TradingSignal(
                        symbol=symbol,
                        signal_type=signal_data['direction'],
                        model=signal_data['model'],
                        entry_price=signal_data['entry_price'],
                        stop_loss=signal_data['stop_loss'],
                        take_profit=signal_data['take_profit'],
                        confidence_score=signal_data['confidence_score'],
                        market_state=signal_data['market_state'],
                        key_level=f"POC: {profile.poc}",
                        order_flow=f"CVD: {order_flow.cvd}, Trend: {order_flow.cvd_trend}",
                        reasoning=signal_data['reasoning'],
                        risk_reward="1:2",
                        timeframe_confluence="1m"
                    )
                    
                    # Store in database
                    doc = signal.model_dump()
                    doc['timestamp'] = doc['timestamp'].isoformat()
                    await db.signals.insert_one(doc)
                    
                    # Broadcast to websocket clients
                    await broadcast_signal(signal)
                    
                    logger.info(f"Signal generated for {symbol}: {signal.signal_type} at {signal.entry_price}")
            
            except json.JSONDecodeError:
                logger.warning(f"Could not parse AI response as JSON: {ai_response}")
        
    except Exception as e:
        logger.error(f"Error in AI analysis for {symbol}: {e}")

# ==================== WEBSOCKET ====================

async def broadcast_market_update(symbol: str):
    """Broadcast market update to all connected clients"""
    try:
        profile = market_store.volume_profiles.get(symbol)
        order_flow = market_store.order_flow.get(symbol)
        candles = list(market_store.candles[symbol])
        
        if not profile or not order_flow or not candles:
            return
        
        update = {
            "type": "market_update",
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "price": candles[-1]['close'],
            "volume_profile": {
                "poc": profile.poc,
                "vah": profile.vah,
                "val": profile.val,
                "levels": [l.model_dump() for l in profile.levels[:20]]  # Send top 20 levels
            },
            "order_flow": order_flow.model_dump()
        }
        
        # Send to all connected websocket clients
        for connection in market_store.active_connections:
            try:
                await connection.send_json(update)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error broadcasting market update: {e}")

async def broadcast_signal(signal: TradingSignal):
    """Broadcast new signal to all connected clients"""
    try:
        update = {
            "type": "new_signal",
            "signal": signal.model_dump()
        }
        update['signal']['timestamp'] = update['signal']['timestamp'].isoformat()
        
        for connection in market_store.active_connections:
            try:
                await connection.send_json(update)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error broadcasting signal: {e}")

# ==================== API ROUTES ====================

@api_router.post("/config")
async def save_config(config: APIConfig):
    """Save API configuration"""
    global api_config
    old_binance_key = api_config.binance_key
    api_config = config
    
    # If Binance keys changed, restart data stream
    if old_binance_key != config.binance_key:
        logger.info("Binance API keys updated - restarting data stream...")
        asyncio.create_task(restart_data_stream())
        
    return {"status": "success", "message": "Configuration saved. Data stream restarting..."}

@api_router.get("/config")
async def get_config():
    """Get current configuration (without sensitive data)"""
    return {
        "has_openrouter_key": bool(api_config.openrouter_key),
        "has_binance_key": bool(api_config.binance_key),
        "has_binance_secret": bool(api_config.binance_secret),
        "ai_model": api_config.ai_model
    }

@api_router.post("/ai/toggle")
async def toggle_ai(enabled: bool):
    """Toggle AI analysis on/off"""
    market_store.ai_enabled = enabled
    status = "enabled" if enabled else "disabled"
    logger.info(f"AI analysis {status}")
    return {"status": "success", "ai_enabled": enabled}

@api_router.get("/ai/status")
async def get_ai_status():
    """Get AI status"""
    return {"ai_enabled": market_store.ai_enabled}

@api_router.get("/market/{symbol}")
async def get_market_data(symbol: str):
    """Get current market data for a symbol"""
    candles = list(market_store.candles[symbol])[-50:]  # Last 50 candles
    profile = market_store.volume_profiles.get(symbol)
    order_flow = market_store.order_flow.get(symbol)
    
    return {
        "symbol": symbol,
        "candles": candles,
        "volume_profile": profile.model_dump() if profile else None,
        "order_flow": order_flow.model_dump() if order_flow else None
    }

@api_router.get("/signals", response_model=List[TradingSignal])
async def get_signals(limit: int = 50):
    """Get recent trading signals"""
    signals = await db.signals.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    
    # Convert ISO string timestamps back to datetime
    for signal in signals:
        if isinstance(signal['timestamp'], str):
            signal['timestamp'] = datetime.fromisoformat(signal['timestamp'])
    
    return signals

@api_router.get("/signals/{symbol}")
async def get_signals_by_symbol(symbol: str, limit: int = 20):
    """Get signals for specific symbol"""
    signals = await db.signals.find({"symbol": symbol}, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    
    for signal in signals:
        if isinstance(signal['timestamp'], str):
            signal['timestamp'] = datetime.fromisoformat(signal['timestamp'])
    
    return signals

@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    market_store.active_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        market_store.active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in market_store.active_connections:
            market_store.active_connections.remove(websocket)

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    logger.info("Starting Trading Signal Bot...")
    # Start data streaming in background
    await start_data_stream()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global binance_fetcher, binance_simulator
    
    if binance_fetcher:
        await binance_fetcher.stop()
    if binance_simulator:
        binance_simulator.stop_streaming()
    
    client.close()
