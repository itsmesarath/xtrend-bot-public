import React, { useState, useEffect, useRef } from 'react';
import '@/App.css';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { ScrollArea } from '@/components/ui/scroll-area';
import { TrendingUp, TrendingDown, Activity, Settings, BarChart3, Zap, AlertCircle, CheckCircle, ArrowUpCircle, ArrowDownCircle, Play, Pause } from 'lucide-react';
import TradingChart from '@/components/TradingChart';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'LTCUSDT', 'DOGEUSDT'];

function App() {
  const [config, setConfig] = useState({
    openrouter_key: '',
    binance_key: '',
    binance_secret: '',
    ai_model: 'meta-llama/llama-3.3-70b-instruct'
  });
  
  const [configStatus, setConfigStatus] = useState({
    has_openrouter_key: false,
    has_binance_key: false,
    has_binance_secret: false,
    data_source: 'simulated'
  });
  
  const [aiEnabled, setAiEnabled] = useState(false);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [marketData, setMarketData] = useState({});
  const [signals, setSignals] = useState([]);
  const [configOpen, setConfigOpen] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [isConfigured, setIsConfigured] = useState(false);
  
  const wsRef = useRef(null);

  // Fetch config status on mount
  useEffect(() => {
    fetchConfigStatus();
    fetchSignals();
    connectWebSocket();
    
    // Fetch market data periodically
    const interval = setInterval(() => {
      SYMBOLS.forEach(symbol => fetchMarketData(symbol));
    }, 5000);
    
    return () => {
      clearInterval(interval);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connectWebSocket = () => {
    try {
      const wsUrl = `${BACKEND_URL}/api/ws`.replace('https://', 'wss://').replace('http://', 'ws://');
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('connected');
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'market_update') {
          setMarketData(prev => ({
            ...prev,
            [data.symbol]: data
          }));
        } else if (data.type === 'new_signal') {
          setSignals(prev => [data.signal, ...prev].slice(0, 50));
          // Show notification
          if (Notification.permission === 'granted') {
            new Notification(`New ${data.signal.signal_type} Signal`, {
              body: `${data.signal.symbol} at ${data.signal.entry_price}`,
              icon: '/favicon.ico'
            });
          }
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('error');
      };
      
      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionStatus('disconnected');
        // Reconnect after 5 seconds
        setTimeout(connectWebSocket, 5000);
      };
      
      wsRef.current = ws;
    } catch (error) {
      console.error('WebSocket connection error:', error);
    }
  };

  const fetchConfigStatus = async () => {
    try {
      const response = await axios.get(`${API}/config`);
      setConfigStatus(response.data);
      setIsConfigured(response.data.has_binance_key && response.data.has_binance_secret);
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  };

  const saveConfig = async () => {
    try {
      await axios.post(`${API}/config`, config);
      await fetchConfigStatus();
      setConfigOpen(false);
      alert('Configuration saved successfully!');
    } catch (error) {
      console.error('Error saving config:', error);
      alert('Error saving configuration');
    }
  };

  const toggleAI = async () => {
    try {
      const newState = !aiEnabled;
      await axios.post(`${API}/ai/toggle?enabled=${newState}`);
      setAiEnabled(newState);
      
      // Request notification permission
      if (newState && Notification.permission === 'default') {
        Notification.requestPermission();
      }
    } catch (error) {
      console.error('Error toggling AI:', error);
    }
  };

  const fetchMarketData = async (symbol) => {
    try {
      const response = await axios.get(`${API}/market/${symbol}`);
      setMarketData(prev => ({
        ...prev,
        [symbol]: response.data
      }));
    } catch (error) {
      console.error(`Error fetching market data for ${symbol}:`, error);
    }
  };

  const fetchSignals = async () => {
    try {
      const response = await axios.get(`${API}/signals?limit=50`);
      setSignals(response.data);
    } catch (error) {
      console.error('Error fetching signals:', error);
    }
  };

  const getMarketStateColor = (data) => {
    if (!data || !data.volume_profile) return 'bg-gray-500';
    const price = data.price;
    const poc = data.volume_profile.poc;
    const vah = data.volume_profile.vah;
    const val = data.volume_profile.val;
    
    if (price > vah || price < val) return 'bg-orange-500';
    return 'bg-emerald-500';
  };

  const getMarketStateText = (data) => {
    if (!data || !data.volume_profile) return 'WARMING UP';
    const price = data.price;
    const vah = data.volume_profile.vah;
    const val = data.volume_profile.val;
    
    if (price > vah || price < val) return 'IMBALANCE';
    return 'BALANCE';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">AMT Signal Bot</h1>
                <p className="text-xs text-slate-400">Auction Market Theory</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Connection Status */}
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${
                    connectionStatus === 'connected' ? 'bg-emerald-500 animate-pulse' : 
                    connectionStatus === 'error' ? 'bg-red-500' : 'bg-gray-500'
                  }`} />
                  <span className="text-xs text-slate-400">
                    {connectionStatus === 'connected' ? 'Live' : connectionStatus === 'error' ? 'Error' : 'Connecting...'}
                  </span>
                </div>
                <div className={`px-2 py-1 rounded text-xs ${
                  configStatus.data_source === 'live' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' : 'bg-amber-500/20 text-amber-400 border border-amber-500/50'
                }`}>
                  {configStatus.data_source === 'live' ? '🔴 Live Data' : '⚡ Demo Data'}
                </div>
              </div>
              
              {/* AI Toggle */}
              <div className="flex items-center gap-3 bg-slate-800/50 px-4 py-2 rounded-lg border border-slate-700">
                <Label htmlFor="ai-toggle" className="text-sm text-slate-300 cursor-pointer">AI Analysis</Label>
                <Switch 
                  id="ai-toggle"
                  checked={aiEnabled} 
                  onCheckedChange={toggleAI}
                  className="data-[state=checked]:bg-emerald-500"
                />
                {aiEnabled && <Zap className="w-4 h-4 text-emerald-400 animate-pulse" />}
              </div>
              
              {/* Config Button */}
              <Dialog open={configOpen} onOpenChange={setConfigOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm" className="border-slate-700 hover:bg-slate-800">
                    <Settings className="w-4 h-4 mr-2" />
                    Configure
                  </Button>
                </DialogTrigger>
                <DialogContent className="bg-slate-900 border-slate-800 text-white max-w-lg">
                  <DialogHeader>
                    <DialogTitle className="text-xl">API Configuration</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label>OpenRouter API Key</Label>
                      <Input 
                        type="password"
                        placeholder="sk-or-..."
                        value={config.openrouter_key}
                        onChange={(e) => setConfig({...config, openrouter_key: e.target.value})}
                        className="bg-slate-800 border-slate-700"
                      />
                      {configStatus.has_openrouter_key && (
                        <p className="text-xs text-emerald-400 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> Configured
                        </p>
                      )}
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Binance API Key</Label>
                      <Input 
                        type="password"
                        placeholder="Your Binance API Key"
                        value={config.binance_key}
                        onChange={(e) => setConfig({...config, binance_key: e.target.value})}
                        className="bg-slate-800 border-slate-700"
                      />
                      {configStatus.has_binance_key && (
                        <p className="text-xs text-emerald-400 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> Configured
                        </p>
                      )}
                    </div>
                    
                    <div className="space-y-2">
                      <Label>Binance API Secret</Label>
                      <Input 
                        type="password"
                        placeholder="Your Binance API Secret"
                        value={config.binance_secret}
                        onChange={(e) => setConfig({...config, binance_secret: e.target.value})}
                        className="bg-slate-800 border-slate-700"
                      />
                      {configStatus.has_binance_secret && (
                        <p className="text-xs text-emerald-400 flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" /> Configured
                        </p>
                      )}
                    </div>
                    
                    <div className="space-y-2">
                      <Label>AI Model</Label>
                      <Input 
                        value={config.ai_model}
                        onChange={(e) => setConfig({...config, ai_model: e.target.value})}
                        className="bg-slate-800 border-slate-700"
                        disabled
                      />
                      <p className="text-xs text-slate-400">Using Llama 3.3 70B Instruct</p>
                    </div>
                    
                    <Alert className={configStatus.data_source === 'live' ? "bg-emerald-500/10 border-emerald-500/50" : "bg-amber-500/10 border-amber-500/50"}>
                      <AlertCircle className={`w-4 h-4 ${configStatus.data_source === 'live' ? 'text-emerald-400' : 'text-amber-400'}`} />
                      <AlertDescription className={`text-xs ${configStatus.data_source === 'live' ? 'text-emerald-300' : 'text-amber-300'}`}>
                        {configStatus.data_source === 'live' 
                          ? '✅ Connected to Binance live market data' 
                          : '⚡ Demo mode: Using simulated data. Add Binance API keys for real-time market data.'}
                      </AlertDescription>
                    </Alert>
                    
                    <Button onClick={saveConfig} className="w-full bg-cyan-600 hover:bg-cyan-700">
                      Save Configuration
                    </Button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-6">
        {!isConfigured ? (
          /* Configuration Required Screen */
          <div className="flex items-center justify-center min-h-[600px]">
            <Card className="bg-slate-800/50 border-slate-700 max-w-2xl w-full">
              <CardHeader>
                <CardTitle className="text-2xl text-center text-white flex items-center justify-center gap-3">
                  <Settings className="w-8 h-8 text-cyan-400" />
                  Configuration Required
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <Alert className="bg-amber-500/10 border-amber-500/50">
                  <AlertCircle className="w-5 h-5 text-amber-400" />
                  <AlertDescription className="text-amber-300">
                    The bot requires Binance API keys to function. No simulated data is available.
                  </AlertDescription>
                </Alert>

                <div className="space-y-4">
                  <h3 className="text-white font-semibold">To get started:</h3>
                  <ol className="list-decimal list-inside space-y-3 text-slate-300">
                    <li>Obtain your Binance API credentials (read-only permission)</li>
                    <li>Click the "Configure" button in the top right</li>
                    <li>Enter your Binance API Key and Secret</li>
                    <li>(Optional) Add OpenRouter API key for AI signal generation</li>
                    <li>Save and the bot will start streaming live market data</li>
                  </ol>
                </div>

                <div className="bg-cyan-500/10 border border-cyan-500/50 rounded-lg p-4 space-y-2">
                  <h4 className="text-cyan-400 font-semibold text-sm">What you'll get:</h4>
                  <ul className="text-sm text-slate-300 space-y-1">
                    <li>• Real-time market data for BTC, ETH, LTC, DOGE</li>
                    <li>• Live volume profile analysis with POC, VAH, VAL</li>
                    <li>• Order flow metrics (CVD, big prints, imbalances)</li>
                    <li>• AI-powered trading signals (when AI enabled)</li>
                    <li>• Interactive charts with marked levels</li>
                  </ul>
                </div>

                <Button 
                  onClick={() => setConfigOpen(true)}
                  className="w-full bg-cyan-600 hover:bg-cyan-700 text-white h-12 text-lg"
                >
                  <Settings className="w-5 h-5 mr-2" />
                  Configure API Keys
                </Button>
              </CardContent>
            </Card>
          </div>
        ) : (
          <Tabs defaultValue="dashboard" className="space-y-6">
            <TabsList className="bg-slate-800/50 border border-slate-700">
              <TabsTrigger value="dashboard" data-testid="dashboard-tab">Dashboard</TabsTrigger>
              <TabsTrigger value="signals" data-testid="signals-tab">Signals</TabsTrigger>
              <TabsTrigger value="analysis" data-testid="analysis-tab">Analysis</TabsTrigger>
            </TabsList>

            {/* Dashboard Tab */}
            <TabsContent value="dashboard" className="space-y-6">
            {/* Market Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {SYMBOLS.map(symbol => {
                const data = marketData[symbol];
                const isLoading = !data;
                
                return (
                  <Card 
                    key={symbol} 
                    className="bg-slate-800/50 border-slate-700 cursor-pointer hover:border-cyan-500 transition-all"
                    onClick={() => setSelectedSymbol(symbol)}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-lg text-white">{symbol.replace('USDT', '')}</CardTitle>
                        <Badge className={`${getMarketStateColor(data)} text-white text-xs`}>
                          {getMarketStateText(data)}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      {isLoading ? (
                        <div className="space-y-2">
                          <div className="h-8 bg-slate-700 rounded animate-pulse" />
                          <div className="h-4 bg-slate-700 rounded animate-pulse" />
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div className="text-2xl font-bold text-white">
                            ${data.price?.toFixed(2) || (data.candles && data.candles.length > 0 ? data.candles[data.candles.length - 1].close.toFixed(2) : '0.00')}
                          </div>
                          {!data.volume_profile ? (
                            <div className="text-xs text-amber-400 flex items-center gap-1">
                              <Activity className="w-3 h-3 animate-pulse" />
                              Collecting data... ({data.candles?.length || 0}/10 candles)
                            </div>
                          ) : (
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              <div>
                                <p className="text-slate-400">POC</p>
                                <p className="text-white font-medium">${data.volume_profile?.poc?.toFixed(2) || '-'}</p>
                              </div>
                              <div>
                                <p className="text-slate-400">CVD</p>
                                <p className={`font-medium ${
                                  data.order_flow?.cvd_trend === 'positive' ? 'text-emerald-400' : 
                                  data.order_flow?.cvd_trend === 'negative' ? 'text-red-400' : 'text-slate-400'
                                }`}>
                                  {data.order_flow?.cvd?.toFixed(2) || '-'}
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>

            {/* Trading Chart */}
            {marketData[selectedSymbol] && marketData[selectedSymbol].candles && (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-white">
                    <BarChart3 className="w-5 h-5" />
                    {selectedSymbol} - Real-Time Chart with Market Levels
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <TradingChart 
                    symbol={selectedSymbol}
                    data={marketData[selectedSymbol].candles || []}
                    volumeProfile={marketData[selectedSymbol].volume_profile}
                    currentPrice={marketData[selectedSymbol].price}
                  />
                </CardContent>
              </Card>
            )}

            {/* Selected Symbol Details */}
            {marketData[selectedSymbol] && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Volume Profile */}
                <Card className="bg-slate-800/50 border-slate-700 lg:col-span-2">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-white">
                      <BarChart3 className="w-5 h-5" />
                      Volume Profile - {selectedSymbol}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <VolumeProfileChart data={marketData[selectedSymbol]} />
                  </CardContent>
                </Card>

                {/* Order Flow */}
                <Card className="bg-slate-800/50 border-slate-700">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-white">
                      <Activity className="w-5 h-5" />
                      Order Flow
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <OrderFlowPanel data={marketData[selectedSymbol]} />
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          {/* Signals Tab */}
          <TabsContent value="signals">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">Trading Signals</CardTitle>
              </CardHeader>
              <CardContent>
                <SignalsList signals={signals} />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Analysis Tab */}
          <TabsContent value="analysis">
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">Market Analysis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-slate-400 text-center py-8">
                  <AlertCircle className="w-12 h-12 mx-auto mb-4 text-slate-600" />
                  <p>Enable AI Analysis to see detailed market insights</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          </Tabs>
        )}
      </main>
    </div>
  );
}

// Volume Profile Chart Component
const VolumeProfileChart = ({ data }) => {
  if (!data || !data.volume_profile || !data.volume_profile.levels) {
    return <div className="text-slate-400 text-center py-8">Loading volume profile...</div>;
  }

  const { poc, vah, val, levels } = data.volume_profile;
  const maxVolume = Math.max(...levels.map(l => l.volume));

  return (
    <div className="space-y-4">
      {/* Key Levels */}
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700">
          <p className="text-slate-400 text-xs mb-1">VAH</p>
          <p className="text-white font-semibold">${vah?.toFixed(2)}</p>
        </div>
        <div className="bg-cyan-500/10 p-3 rounded-lg border border-cyan-500/50">
          <p className="text-cyan-400 text-xs mb-1">POC</p>
          <p className="text-white font-semibold">${poc?.toFixed(2)}</p>
        </div>
        <div className="bg-slate-900/50 p-3 rounded-lg border border-slate-700">
          <p className="text-slate-400 text-xs mb-1">VAL</p>
          <p className="text-white font-semibold">${val?.toFixed(2)}</p>
        </div>
      </div>

      {/* Volume Bars */}
      <ScrollArea className="h-64">
        <div className="space-y-1">
          {levels.slice(0, 30).map((level, idx) => {
            const widthPercent = (level.volume / maxVolume) * 100;
            return (
              <div key={idx} className="flex items-center gap-2 text-xs">
                <span className={`w-16 text-right ${
                  level.is_poc ? 'text-cyan-400 font-bold' : 
                  level.is_lvn ? 'text-orange-400' : 
                  level.is_hvn ? 'text-emerald-400' : 'text-slate-400'
                }`}>
                  ${level.price.toFixed(2)}
                </span>
                <div className="flex-1 bg-slate-900/50 rounded-full h-4 overflow-hidden">
                  <div 
                    className={`h-full transition-all ${
                      level.is_poc ? 'bg-cyan-500' : 
                      level.is_lvn ? 'bg-orange-500' : 
                      level.is_hvn ? 'bg-emerald-500' : 'bg-slate-600'
                    }`}
                    style={{ width: `${widthPercent}%` }}
                  />
                </div>
                <span className="w-12 text-slate-500 text-xs">{level.volume.toFixed(0)}</span>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* Legend */}
      <div className="flex gap-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-cyan-500 rounded" />
          <span className="text-slate-400">POC</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-orange-500 rounded" />
          <span className="text-slate-400">LVN</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 bg-emerald-500 rounded" />
          <span className="text-slate-400">HVN</span>
        </div>
      </div>
    </div>
  );
};

// Order Flow Panel Component
const OrderFlowPanel = ({ data }) => {
  if (!data || !data.order_flow) {
    return <div className="text-slate-400 text-center py-8">Loading order flow...</div>;
  }

  const { cvd, cvd_trend, imbalance_ratio, big_prints } = data.order_flow;

  return (
    <div className="space-y-4">
      {/* CVD */}
      <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
        <p className="text-slate-400 text-xs mb-2">Cumulative Volume Delta</p>
        <div className="flex items-end gap-2">
          <span className={`text-2xl font-bold ${
            cvd_trend === 'positive' ? 'text-emerald-400' : 
            cvd_trend === 'negative' ? 'text-red-400' : 'text-slate-400'
          }`}>
            {cvd?.toFixed(2)}
          </span>
          {cvd_trend === 'positive' ? (
            <TrendingUp className="w-5 h-5 text-emerald-400 mb-1" />
          ) : cvd_trend === 'negative' ? (
            <TrendingDown className="w-5 h-5 text-red-400 mb-1" />
          ) : null}
        </div>
      </div>

      {/* Buy/Sell Imbalance */}
      <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
        <p className="text-slate-400 text-xs mb-2">Buy/Sell Imbalance</p>
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-emerald-400">Buy: {imbalance_ratio?.toFixed(1)}%</span>
            <span className="text-red-400">Sell: {(100 - imbalance_ratio).toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-slate-900 rounded-full overflow-hidden flex">
            <div 
              className="bg-emerald-500 transition-all"
              style={{ width: `${imbalance_ratio}%` }}
            />
            <div 
              className="bg-red-500 transition-all"
              style={{ width: `${100 - imbalance_ratio}%` }}
            />
          </div>
        </div>
      </div>

      {/* Big Prints */}
      <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
        <p className="text-slate-400 text-xs mb-3">Recent Big Prints</p>
        {big_prints && big_prints.length > 0 ? (
          <ScrollArea className="h-32">
            <div className="space-y-2">
              {big_prints.map((print, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs bg-slate-800/50 p-2 rounded">
                  <div className="flex items-center gap-2">
                    {print.side === 'buy' ? (
                      <ArrowUpCircle className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <ArrowDownCircle className="w-4 h-4 text-red-400" />
                    )}
                    <span className="text-white font-medium">${print.price?.toFixed(2)}</span>
                  </div>
                  <span className="text-slate-400">{print.quantity?.toFixed(4)}</span>
                </div>
              ))}
            </div>
          </ScrollArea>
        ) : (
          <p className="text-slate-500 text-xs">No big prints detected</p>
        )}
      </div>
    </div>
  );
};

// Signals List Component
const SignalsList = ({ signals }) => {
  if (!signals || signals.length === 0) {
    return (
      <div className="text-slate-400 text-center py-12">
        <Activity className="w-12 h-12 mx-auto mb-4 text-slate-600" />
        <p className="text-lg">No signals yet</p>
        <p className="text-sm mt-2">Enable AI Analysis to start generating trading signals</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[600px]">
      <div className="space-y-3">
        {signals.map((signal, idx) => (
          <div 
            key={signal.id || idx}
            data-testid={`signal-${idx}`}
            className={`p-4 rounded-lg border-l-4 ${
              signal.signal_type === 'BUY' 
                ? 'bg-emerald-500/10 border-emerald-500' 
                : 'bg-red-500/10 border-red-500'
            }`}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  signal.signal_type === 'BUY' ? 'bg-emerald-500/20' : 'bg-red-500/20'
                }`}>
                  {signal.signal_type === 'BUY' ? (
                    <TrendingUp className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <TrendingDown className="w-5 h-5 text-red-400" />
                  )}
                </div>
                <div>
                  <h3 className="text-white font-semibold">{signal.symbol}</h3>
                  <p className="text-xs text-slate-400">
                    {new Date(signal.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
              <Badge className={signal.signal_type === 'BUY' ? 'bg-emerald-500' : 'bg-red-500'}>
                {signal.signal_type}
              </Badge>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3 text-sm">
              <div>
                <p className="text-slate-400 text-xs">Entry</p>
                <p className="text-white font-medium">${signal.entry_price?.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs">Stop Loss</p>
                <p className="text-white font-medium">${signal.stop_loss?.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs">Take Profit</p>
                <p className="text-white font-medium">${signal.take_profit?.toFixed(2)}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs">Confidence</p>
                <p className="text-white font-medium">{signal.confidence_score}%</p>
              </div>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex gap-2">
                <Badge variant="outline" className="border-slate-600 text-slate-300">
                  {signal.model?.replace('_', ' ')}
                </Badge>
                <Badge variant="outline" className="border-slate-600 text-slate-300">
                  {signal.market_state}
                </Badge>
              </div>
              <p className="text-slate-300 leading-relaxed">{signal.reasoning}</p>
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
};

export default App;
