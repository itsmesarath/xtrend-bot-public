# AMT Trading Signal Bot

An automated trading signal bot built on Fabio Valentini's Auction Market Theory (AMT) for cryptocurrency trading. Available as both a web application and Windows desktop application.

## Overview

This application analyzes cryptocurrency markets (BTC, ETH, LTC, DOGE) using:
- **Auction Market Theory** framework
- **Volume Profile Analysis** (POC, VAH/VAL, LVN/HVN)
- **Order Flow Metrics** (CVD, Big Prints, Footprint Analysis)
- **AI-Powered Analysis** (OpenRouter integration with Llama 3.3)
- **Real-time WebSocket Data** streaming

## Features

✅ **Real-time Market Analysis** - Live data from Binance or simulated demo mode  
✅ **Dual Volume Profiles** - Current candle and full day analysis  
✅ **Trading Signals** - Trend Continuation and Mean Reversion models  
✅ **AI Integration** - Continuous per-candle market analysis  
✅ **Desktop & Web** - Available as Windows installer or web app  
✅ **Data Mode Toggle** - Switch between demo and live data seamlessly

## Technology Stack

- **Frontend**: React 18, Shadcn/UI, Tailwind CSS
- **Backend**: FastAPI (Python), WebSocket
- **Database**: MongoDB (optional, falls back to in-memory)
- **Desktop**: Electron 28
- **AI**: OpenRouter API (meta-llama/llama-3.3-70b-instruct)
- **Data Source**: Binance API or Simulator

## Quick Start

### 🐳 Docker (Recommended - Easiest)

```bash
# Start all services with one command
docker-compose up -d

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8001
# API Docs: http://localhost:8001/docs
```

See **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** for complete Docker guide.

### 🌐 Web Application

```bash
# Install dependencies
cd frontend && yarn install
cd ../backend && pip install -r requirements.txt

# Start services
sudo supervisorctl restart all

# Access at: https://trade-bot-36.preview.emergentagent.com
```

### 💻 Desktop Application (Windows)

See **[BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)** for complete build guide.

**Quick build:**
```bash
cd electron
build.bat
```

Installer will be created at: `electron/dist/AMT Trading Bot Setup 1.0.0.exe`

## Project Structure

```
/app/
├── backend/              # FastAPI backend
│   ├── server.py        # Main server with trading logic
│   └── requirements.txt
├── frontend/             # React frontend
│   ├── src/
│   │   ├── App.js       # Main application
│   │   ├── config.js    # Environment detection (Web/Electron)
│   │   └── components/
│   └── package.json
├── electron/             # Desktop application wrapper
│   ├── main.js          # Electron main process
│   ├── preload.js       # Preload script
│   ├── package.json     # Electron config
│   ├── build.bat        # Windows build script
│   └── README.md        # Electron-specific docs
├── BUILD_INSTRUCTIONS.md # Complete build guide
└── README.md            # This file
```

## Configuration

### Demo Mode (No API Keys Required)

The bot includes a realistic data simulator - perfect for testing and development.

1. Launch the application
2. Toggle "Demo" mode in the header
3. Start analyzing!

### Live Mode (Requires API Keys)

1. **Binance API Keys** (for live market data):
   - Create at: https://www.binance.com/en/my/settings/api-management
   - Required permissions: Read-only
   
2. **OpenRouter API Key** (optional, for AI analysis):
   - Get at: https://openrouter.ai/keys
   - Used for AI-powered signal analysis

3. Configure via the settings panel in the app

## Development

### Prerequisites

- Node.js 18+
- Python 3.9+
- Yarn package manager
- MongoDB (optional)

### Environment Variables

**Frontend** (`frontend/.env`):
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

**Backend** (`backend/.env`):
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=amt_trading_bot
CORS_ORIGINS=*
```

### Running Locally

```bash
# Terminal 1: Backend
cd backend
python server.py

# Terminal 2: Frontend
cd frontend
yarn start

# Access at http://localhost:3000
```

## Building Desktop Application

Complete instructions in **[BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)**

### Quick Build Steps

1. **Build Backend**:
   ```bash
   cd backend
   pyinstaller --onefile --name server server.py --distpath ./dist
   ```

2. **Build Frontend**:
   ```bash
   cd frontend
   yarn build
   ```

3. **Package Electron**:
   ```bash
   cd electron
   yarn build
   ```

**Automated Build (Windows)**:
```bash
cd electron
build.bat
```

## Documentation

- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Docker container deployment guide
- **[BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)** - Windows desktop build guide
- **[QUICK_START.md](QUICK_START.md)** - Quick reference for all platforms
- **[electron/README.md](electron/README.md)** - Electron-specific documentation
- **[LIVE_DATA_INTEGRATION.md](LIVE_DATA_INTEGRATION.md)** - Live data integration guide

## Trading Models

### 1. Trend Continuation
- Identifies strong directional moves
- Uses volume profile and order flow confirmation
- Targets breakout scenarios

### 2. Mean Reversion
- Detects overextended prices
- Targets returns to value area
- Uses LVN/HVN analysis

Both models calculate confidence scores (0-100) with ≥70% threshold for signal generation.

## Volume Profile Visualization

The application displays two synchronized volume profiles:

- **Current Candle Profile**: Real-time volume distribution for active candle
- **Full Day Profile**: Complete daily volume analysis

Key levels marked:
- POC (Point of Control) - Highest volume price
- VAH/VAL (Value Area High/Low) - 70% volume range
- HVN/LVN (High/Low Volume Nodes) - Support/resistance

## API Endpoints

### REST API

- `GET /api/status` - Server status and configuration
- `POST /api/config` - Update API keys
- `GET /api/config/status` - Check configuration status
- `GET /api/market/{symbol}` - Get market data
- `POST /api/analyze` - AI analysis request
- `POST /api/data-mode` - Switch demo/live mode

### WebSocket

- `ws://localhost:8001/api/ws` - Real-time market updates and signals

## Troubleshooting

### Web Application

**Backend won't start:**
```bash
# Check logs
tail -f /var/log/supervisor/backend.*.log

# Restart services
sudo supervisorctl restart all
```

**Frontend connection errors:**
- Verify `REACT_APP_BACKEND_URL` in `frontend/.env`
- Check backend is running on port 8001

### Desktop Application

**App won't start:**
- Check if port 8001 is available
- Verify `backend/dist/server.exe` exists
- Run from command line to see error logs

**Blank window:**
- Verify `frontend/build/` exists
- Check Electron DevTools console for errors

**See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) Troubleshooting section for more**

## Support

For issues or questions:
1. Check documentation in this repo
2. Review logs (web: `/var/log/supervisor/`, desktop: console output)
3. Verify all prerequisites installed

## License

MIT License

## Changelog

### Version 1.0.0 (Current)
- Initial release
- Web and Windows desktop support
- Demo and live data modes
- Dual volume profile visualization
- AI analysis integration
- Real-time WebSocket updates
- Trading signal generation (Trend + Mean Reversion)

---

**Built with ❤️ using Auction Market Theory**
