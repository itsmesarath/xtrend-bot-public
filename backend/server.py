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
import random
import time
from binance import AsyncClient, BinanceSocketManager
from binance.enums import *

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
        self.candles = defaultdict(lambda: deque(maxlen=2000))  # Store last 2000 candles (1440 for 24h at 1m)
        self.trades = defaultdict(lambda: deque(maxlen=10000))  # Store last 10000 trades per symbol
        self.volume_profiles = {}  # Current volume profile per symbol (last 50 candles)
        self.volume_profiles_day = {}  # Full day volume profile per symbol (all candles)
        self.order_flow = {}  # Current order flow metrics per symbol
        self.cvd_values = defaultdict(lambda: deque(maxlen=500))  # CVD history
        self.ai_enabled = False
        self.last_ai_analysis = {}
        self.active_connections = []
        self.aggregated_candles = defaultdict(lambda: {})  # Store aggregated timeframes
        
market_store = MarketDataStore()
api_config = APIConfig()
binance_fetcher = None  # Will be initialized when API keys are provided
binance_simulator = None  # Fallback simulator
use_demo_mode = True  # Toggle between demo and live mode

# ==================== BINANCE DATA ====================

class BinanceDataFetcher:
    """Real Binance data fetcher using API"""
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = None
        self.bm = None
        self.symbols = ["BTCUSDT", "ETHUSDT", "LTCUSDT", "DOGEUSDT"]
        self.running = False
        self.tasks = []
        
    async def start(self):
        """Initialize Binance client and start streaming"""
        try:
            self.client = await AsyncClient.create(self.api_key, self.api_secret)
            self.bm = BinanceSocketManager(self.client)
            self.running = True
            
            logger.info("Connected to Binance API - Starting real data stream...")
            
            # Start kline streams for each symbol
            for symbol in self.symbols:
                task = asyncio.create_task(self.stream_klines(symbol))
                self.tasks.append(task)
                
                task = asyncio.create_task(self.stream_trades(symbol))
                self.tasks.append(task)
                
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self.running = False
            raise
    
    async def stream_klines(self, symbol: str):
        """Stream 1-minute candles for a symbol"""
        try:
            async with self.bm.kline_socket(symbol=symbol, interval='1m') as stream:
                while self.running:
                    res = await stream.recv()
                    kline = res['k']
                    
                    # Only process closed candles
                    if kline['x']:  # is candle closed
                        candle = {
                            "symbol": symbol,
                            "timestamp": datetime.fromtimestamp(kline['T'] / 1000, tz=timezone.utc),
                            "open": float(kline['o']),
                            "high": float(kline['h']),
                            "low": float(kline['l']),
                            "close": float(kline['c']),
                            "volume": float(kline['v']),
                            "buy_volume": float(kline['V']),  # Taker buy base asset volume
                            "sell_volume": float(kline['v']) - float(kline['V'])
                        }
                        
                        market_store.candles[symbol].append(candle)
                        
                        # Calculate both volume profiles and order flow
                        await calculate_volume_profile(symbol, 50, "current")  # Last 50 candles
                        await calculate_volume_profile(symbol, -1, "day")       # All candles (full day)
                        await calculate_order_flow(symbol)
                        
                        # Broadcast update
                        await broadcast_market_update(symbol)
                        
                        # AI analysis if enabled
                        if market_store.ai_enabled:
                            await analyze_with_ai(symbol, candle)
                            
        except Exception as e:
            logger.error(f"Error in kline stream for {symbol}: {e}")
    
    async def stream_trades(self, symbol: str):
        """Stream individual trades for order flow analysis"""
        try:
            async with self.bm.trade_socket(symbol=symbol) as stream:
                while self.running:
                    res = await stream.recv()
                    
                    trade = {
                        "symbol": symbol,
                        "timestamp": datetime.fromtimestamp(res['T'] / 1000, tz=timezone.utc),
                        "price": float(res['p']),
                        "quantity": float(res['q']),
                        "side": "buy" if res['m'] else "sell",  # m = is buyer market maker
                        "is_big_print": False  # Will be determined in order flow calc
                    }
                    
                    market_store.trades[symbol].append(trade)
                    
        except Exception as e:
            logger.error(f"Error in trade stream for {symbol}: {e}")
    
    async def stop(self):
        """Stop all streams and close client"""
        self.running = False
        for task in self.tasks:
            task.cancel()
        if self.client:
            await self.client.close_connection()

class BinanceDataSimulator:
    def __init__(self):
        self.symbols = ["BTCUSDT", "ETHUSDT", "LTCUSDT", "DOGEUSDT"]
        self.base_prices = {}
        self.current_prices = {}
        self.running = False
        self.initialized = False
        
    async def initialize_prices(self):
        """Fetch real current prices from public APIs (no auth required)"""
        try:
            import aiohttp
            
            # Try multiple public APIs to get real current prices
            async with aiohttp.ClientSession() as session:
                # Try CoinGecko first (no rate limit for basic usage)
                try:
                    coingecko_ids = {
                        "BTCUSDT": "bitcoin",
                        "ETHUSDT": "ethereum",
                        "LTCUSDT": "litecoin",
                        "DOGEUSDT": "dogecoin"
                    }
                    
                    ids_str = ",".join(coingecko_ids.values())
                    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids_str}&vs_currencies=usd"
                    
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            for symbol, coin_id in coingecko_ids.items():
                                if coin_id in data and 'usd' in data[coin_id]:
                                    price = float(data[coin_id]['usd'])
                                    self.base_prices[symbol] = price
                                    self.current_prices[symbol] = price
                                    logger.info(f"Demo Mode: {symbol} initialized at ${price:.2f} (CoinGecko)")
                            self.initialized = True
                            return
                except Exception as e:
                    logger.warning(f"CoinGecko API failed: {e}")
                
                # Fallback to CryptoCompare
                try:
                    symbols_str = "BTC,ETH,LTC,DOGE"
                    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={symbols_str}&tsyms=USD"
                    
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            mapping = {
                                "BTC": "BTCUSDT",
                                "ETH": "ETHUSDT", 
                                "LTC": "LTCUSDT",
                                "DOGE": "DOGEUSDT"
                            }
                            for coin, symbol in mapping.items():
                                if coin in data and 'USD' in data[coin]:
                                    price = float(data[coin]['USD'])
                                    self.base_prices[symbol] = price
                                    self.current_prices[symbol] = price
                                    logger.info(f"Demo Mode: {symbol} initialized at ${price:.2f} (CryptoCompare)")
                            self.initialized = True
                            return
                except Exception as e:
                    logger.warning(f"CryptoCompare API failed: {e}")
                
        except Exception as e:
            logger.warning(f"All price APIs failed: {e}")
        
        # Ultimate fallback - use reasonable current market prices
        logger.info("Using fallback prices for demo mode")
        self.base_prices = {
            "BTCUSDT": 103500.0,
            "ETHUSDT": 3850.0,
            "LTCUSDT": 115.0,
            "DOGEUSDT": 0.38
        }
        self.current_prices = self.base_prices.copy()
        self.initialized = True
        
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
        # Initialize with real current prices first
        if not self.initialized:
            await self.initialize_prices()
        
        self.running = True
        logger.info(f"Starting Binance data simulation with prices: BTC=${self.base_prices.get('BTCUSDT', 0):.0f}")
        
        # Generate initial historical data (last 6 hours worth = 360 candles at 1m)
        logger.info("Generating initial historical data (6 hours)...")
        start_time = datetime.now(timezone.utc) - timedelta(minutes=360)
        
        for symbol in self.symbols:
            for i in range(360):
                candle = await self.generate_candle(symbol)
                # Set timestamp in proper ascending order
                candle['timestamp'] = start_time + timedelta(minutes=i)
                market_store.candles[symbol].append(candle)
        
        logger.info(f"Generated {len(market_store.candles['BTCUSDT'])} historical candles")
        
        # Calculate initial volume profile for all symbols
        for symbol in self.symbols:
            await calculate_volume_profile(symbol, 50, "current")  # Last 50 candles
            await calculate_volume_profile(symbol, 60, "1h")        # Last 1 hour (60 candles)
            await calculate_volume_profile(symbol, -1, "day")       # All candles (full day)
            await calculate_order_flow(symbol)
        
        while self.running:
            try:
                for symbol in self.symbols:
                    # Generate candle every 10 seconds for demo purposes
                    if len(market_store.candles[symbol]) == 0 or \
                       (datetime.now(timezone.utc) - market_store.candles[symbol][-1]['timestamp']).seconds >= 10:
                        candle = await self.generate_candle(symbol)
                        market_store.candles[symbol].append(candle)
                        
                        # Calculate both volume profiles and order flow
                        await calculate_volume_profile(symbol, 50, "current")  # Last 50 candles
                        await calculate_volume_profile(symbol, -1, "day")       # All candles (full day)
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
    """Start appropriate data stream based on configuration"""
    global binance_fetcher, binance_simulator, use_demo_mode
    
    if not api_config.binance_key or not api_config.binance_secret:
        # No API keys - bot is idle
        logger.info("No Binance API keys configured - bot is idle. Waiting for configuration.")
        return
    
    if use_demo_mode:
        # Use demo mode with real current prices
        logger.info("Starting DEMO MODE with real current prices from public APIs...")
        binance_simulator = BinanceDataSimulator()
        asyncio.create_task(binance_simulator.start_streaming())
    else:
        # Use real Binance live data
        try:
            logger.info("Starting LIVE BINANCE MODE - connecting to real-time WebSocket...")
            binance_fetcher = BinanceDataFetcher(api_config.binance_key, api_config.binance_secret)
            await binance_fetcher.start()
            logger.info("✅ Connected to Binance live data successfully!")
        except Exception as e:
            logger.error(f"Failed to connect to Binance API: {e}")
            logger.error("Binance API may be geo-restricted from this server location.")
            logger.info("Consider switching to Demo Mode or deploying to a Binance-supported region.")
            raise

async def restart_data_stream():
    """Restart data stream when configuration changes"""
    global binance_fetcher, binance_simulator
    
    # Stop existing streams
    if binance_fetcher:
        await binance_fetcher.stop()
        binance_fetcher = None
    
    if binance_simulator:
        binance_simulator.stop_streaming()
        binance_simulator = None
    
    # Start new stream
    await start_data_stream()

# ==================== CANDLE AGGREGATION ====================

def aggregate_candles(candles: list, timeframe_minutes: int) -> list:
    """Aggregate 1-minute candles into higher timeframes with proper time bucketing"""
    if not candles or timeframe_minutes == 1:
        return candles
    
    if len(candles) == 0:
        return []
    
    aggregated = []
    
    # Group candles by timeframe buckets
    current_bucket = []
    bucket_start_time = None
    
    for candle in candles:
        candle_time = candle['timestamp']
        
        # Get the bucket start time for this candle
        if isinstance(candle_time, str):
            candle_time = datetime.fromisoformat(candle_time.replace('Z', '+00:00'))
        
        # Calculate which bucket this candle belongs to
        minutes_since_epoch = int(candle_time.timestamp() / 60)
        bucket_minutes = (minutes_since_epoch // timeframe_minutes) * timeframe_minutes
        bucket_time = datetime.fromtimestamp(bucket_minutes * 60, tz=timezone.utc)
        
        # Start new bucket if needed
        if bucket_start_time is None:
            bucket_start_time = bucket_time
            current_bucket = [candle]
        elif bucket_time == bucket_start_time:
            # Same bucket, add candle
            current_bucket.append(candle)
        else:
            # New bucket started, aggregate previous bucket
            if current_bucket:
                agg_candle = {
                    "symbol": current_bucket[0]['symbol'],
                    "timestamp": bucket_start_time,
                    "open": current_bucket[0]['open'],
                    "high": max(c['high'] for c in current_bucket),
                    "low": min(c['low'] for c in current_bucket),
                    "close": current_bucket[-1]['close'],
                    "volume": sum(c['volume'] for c in current_bucket),
                    "buy_volume": sum(c.get('buy_volume', 0) for c in current_bucket),
                    "sell_volume": sum(c.get('sell_volume', 0) for c in current_bucket)
                }
                aggregated.append(agg_candle)
            
            # Start new bucket
            bucket_start_time = bucket_time
            current_bucket = [candle]
    
    # Don't forget the last bucket
    if current_bucket and len(current_bucket) >= timeframe_minutes * 0.5:  # At least 50% complete
        agg_candle = {
            "symbol": current_bucket[0]['symbol'],
            "timestamp": bucket_start_time,
            "open": current_bucket[0]['open'],
            "high": max(c['high'] for c in current_bucket),
            "low": min(c['low'] for c in current_bucket),
            "close": current_bucket[-1]['close'],
            "volume": sum(c['volume'] for c in current_bucket),
            "buy_volume": sum(c.get('buy_volume', 0) for c in current_bucket),
            "sell_volume": sum(c.get('sell_volume', 0) for c in current_bucket)
        }
        aggregated.append(agg_candle)
    
    return aggregated

# ==================== VOLUME PROFILE CALCULATIONS ====================

async def calculate_volume_profile(symbol: str, num_candles: int = 50, profile_type: str = "current") -> Optional[VolumeProfile]:
    """Calculate volume profile from candle data
    
    Args:
        symbol: Trading symbol
        num_candles: Number of recent candles to use (-1 for all)
        profile_type: Type of profile ("current", "1h", or "day")
    """
    try:
        candles = list(market_store.candles[symbol])
        if len(candles) < 10:
            return None
        
        # Select candles based on num_candles parameter
        if num_candles == -1:
            recent_candles = candles  # All candles for day profile
        else:
            recent_candles = candles[-num_candles:]
        
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
        
        # Store in appropriate location based on profile type
        if profile_type == "day":
            market_store.volume_profiles_day[symbol] = profile
        else:
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
    global binance_fetcher, binance_simulator, use_demo_mode
    
    # Determine actual data source
    if binance_fetcher and binance_fetcher.running:
        data_source = "live"
    elif binance_simulator and binance_simulator.running:
        data_source = "demo"
    else:
        data_source = "idle"
    
    return {
        "has_openrouter_key": bool(api_config.openrouter_key),
        "has_binance_key": bool(api_config.binance_key),
        "has_binance_secret": bool(api_config.binance_secret),
        "ai_model": api_config.ai_model,
        "data_source": data_source,
        "use_demo_mode": use_demo_mode
    }

@api_router.post("/data-mode/toggle")
async def toggle_data_mode():
    """Toggle between demo mode and live Binance mode"""
    global use_demo_mode
    
    if not api_config.binance_key or not api_config.binance_secret:
        return {
            "status": "error",
            "message": "Binance API keys required to use any data mode"
        }
    
    # Toggle mode
    use_demo_mode = not use_demo_mode
    mode_name = "Demo Mode (Real Prices)" if use_demo_mode else "Live Binance Mode"
    
    logger.info(f"Data mode toggled to: {mode_name}")
    
    # Restart data stream with new mode
    asyncio.create_task(restart_data_stream())
    
    return {
        "status": "success",
        "use_demo_mode": use_demo_mode,
        "mode": mode_name,
        "message": f"Switched to {mode_name}. Data stream restarting..."
    }

@api_router.get("/data-mode")
async def get_data_mode():
    """Get current data mode"""
    global use_demo_mode, binance_fetcher, binance_simulator
    
    mode = "demo" if use_demo_mode else "live"
    
    # Check actual status
    is_running = False
    if use_demo_mode:
        is_running = binance_simulator and binance_simulator.running
    else:
        is_running = binance_fetcher and binance_fetcher.running
    
    return {
        "mode": mode,
        "use_demo_mode": use_demo_mode,
        "is_running": is_running,
        "description": "Demo Mode (Real Current Prices)" if use_demo_mode else "Live Binance WebSocket"
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
async def get_market_data(symbol: str, limit: int = 100):
    """Get current market data for a symbol with two volume profiles"""
    candles = list(market_store.candles[symbol])[-limit:]
    
    profile_current = market_store.volume_profiles.get(symbol)
    profile_day = market_store.volume_profiles_day.get(symbol)
    order_flow = market_store.order_flow.get(symbol)
    
    return {
        "symbol": symbol,
        "candles": candles,
        "volume_profile": profile_current.model_dump() if profile_current else None,
        "volume_profile_day": profile_day.model_dump() if profile_day else None,
        "order_flow": order_flow.model_dump() if order_flow else None
    }

@api_router.get("/market/{symbol}/history")
async def get_historical_data(symbol: str, timeframe: str = "1m"):
    """Get full day's historical data with timeframe support"""
    base_candles = list(market_store.candles[symbol])
    
    # Map timeframe to minutes
    timeframe_map = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
        "1d": 1440
    }
    
    minutes = timeframe_map.get(timeframe, 1)
    
    # Aggregate if needed
    if minutes > 1:
        candles = aggregate_candles(base_candles, minutes)
    else:
        candles = base_candles
    
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": candles,
        "count": len(candles)
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
