# Live Binance Data Integration Guide

## Overview
The AMT Trading Signal Bot now supports **both simulated and live Binance market data**. The system automatically switches between data sources based on your API configuration.

## Data Source Indicator
Look for the data source badge in the top right corner of the dashboard:
- **⚡ Demo Data** - Using simulated market data (safe for testing)
- **🔴 Live Data** - Connected to real Binance market data

## How to Switch to Live Data

### Step 1: Get Binance API Keys
1. Log in to your Binance account
2. Go to API Management: https://www.binance.com/en/my/settings/api-management
3. Create a new API key
4. **Important**: For this bot, you only need **READ permissions** (no trading permissions required)
5. Save your API Key and Secret Key securely

### Step 2: Configure the Bot
1. Click the **"Configure"** button in the top right
2. Enter your Binance API Key
3. Enter your Binance API Secret
4. (Optional) Enter your OpenRouter API Key for AI signal generation
5. Click **"Save Configuration"**

### Step 3: Verify Connection
After saving:
- The data source indicator should change to **"🔴 Live Data"**
- The configuration alert should show: "✅ Connected to Binance live market data"
- Market cards will start showing real-time prices from Binance

## What Happens When You Connect?

### Real-Time Data Streaming
Once connected, the bot will:
1. **Stream 1-minute candles** for all 4 trading pairs (BTCUSDT, ETHUSDT, LTCUSDT, DOGEUSDT)
2. **Stream individual trades** for order flow analysis
3. Calculate volume profiles and order flow metrics in real-time
4. Update the dashboard every second with live data

### Data Collected
- **OHLCV Data**: Open, High, Low, Close, Volume for each 1-minute candle
- **Trade Data**: Individual trades with price, quantity, and side (buy/sell)
- **Volume Profile**: POC, VAH, VAL, LVNs, HVNs calculated from live data
- **Order Flow**: CVD, big prints, buy/sell imbalance ratios

## Switching Back to Demo Mode

To switch back to simulated data:
1. Open Configuration
2. Clear the Binance API Key and Secret fields
3. Click "Save Configuration"
4. The bot will automatically restart with simulated data

## Technical Details

### Binance WebSocket Streams
The bot uses Binance WebSocket API for real-time data:
- **Kline Stream**: 1-minute candlestick data
- **Trade Stream**: Individual trade updates
- **Automatic Reconnection**: Handles disconnections gracefully

### Data Processing Pipeline
```
Binance API → WebSocket → Candle/Trade Processing → Volume Profile Calculation → 
Order Flow Analysis → Dashboard Update → AI Analysis (if enabled)
```

### Failover Mechanism
If the Binance connection fails:
- The bot automatically falls back to simulated data
- An error is logged with details
- You'll see "⚡ Demo Data" indicator
- No data loss - the bot continues operating

## Security Notes

### API Key Permissions
**Required Permissions**: 
- ✅ Enable Reading (read-only access)

**NOT Required**:
- ❌ Enable Spot & Margin Trading
- ❌ Enable Futures Trading
- ❌ Enable Withdrawals

### API Key Storage
- API keys are stored in-memory only (not persisted to disk)
- Keys are sent securely over HTTPS
- Never logged or exposed in error messages
- You need to re-enter keys after server restart

### IP Whitelisting (Optional)
For extra security, you can whitelist the server IP in your Binance API settings.

## Troubleshooting

### "Demo Data" won't switch to "Live Data"
1. Verify your API keys are correct (no extra spaces)
2. Check that your API key has "Enable Reading" permission
3. Check backend logs: `tail -f /var/log/supervisor/backend.err.log`
4. Look for error messages about Binance connection

### Data seems delayed
- Binance streams data in real-time with minimal latency (~100-500ms)
- If you see delays, check your internet connection
- WebSocket may need to reconnect (automatic)

### Connection keeps dropping
- Check firewall settings (WebSocket needs outbound port 443/9443)
- Verify Binance API is not rate-limited
- Check Binance API status: https://www.binance.com/en/support/announcement

## API Rate Limits

### Binance Limits
- **WebSocket Connections**: 5 connections per IP
- **Messages per second**: No hard limit for data streams
- This bot uses 8 WebSocket connections (4 pairs × 2 streams)

### What if I hit limits?
- The bot handles rate limits gracefully
- Automatic backoff and retry
- Falls back to simulator if needed

## Cost Considerations

### Binance API
- **Free**: WebSocket data streams are completely free
- **No fees**: Reading market data has no cost
- **No subscription**: No monthly fees for API access

### Data Usage
- Minimal bandwidth (~1-2 MB per hour for 4 trading pairs)
- Suitable for most internet connections

## Testing the Integration

### Quick Test
1. Configure your Binance API keys
2. Watch the data source indicator change to "🔴 Live Data"
3. Compare prices with Binance.com to verify accuracy
4. Check Volume Profile updates every minute

### Validation Points
- ✅ Data source shows "Live Data"
- ✅ Prices match Binance.com spot prices
- ✅ New candles appear every 60 seconds
- ✅ Volume Profile updates with each candle
- ✅ Big prints appear in Order Flow panel

## Next Steps

Once connected to live data:
1. **Let it collect data** (at least 10 candles for volume profile)
2. **Enable AI Analysis** to start generating signals
3. **Monitor signals** based on real market conditions
4. **Review** signal quality and confidence scores

## Support

If you encounter issues:
1. Check this guide first
2. Review backend logs for error details
3. Verify Binance API key permissions
4. Test with demo data first to rule out bot issues

---

**Remember**: This bot is for **signal generation only**. It does not place trades automatically. Always verify signals manually before trading.
