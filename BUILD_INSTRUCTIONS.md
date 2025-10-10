# AMT Trading Signal Bot - Electron Desktop Build Instructions

This guide provides step-by-step instructions to build and package the AMT Trading Signal Bot as a Windows desktop application.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Overview](#project-overview)
3. [Development Setup](#development-setup)
4. [Building for Production](#building-for-production)
5. [Distribution](#distribution)
6. [Troubleshooting](#troubleshooting)
7. [Configuration](#configuration)

---

## Prerequisites

### Required Software

1. **Node.js** (v18.x or higher)
   - Download from: https://nodejs.org/
   - Verify installation: `node --version` and `npm --version`

2. **Yarn Package Manager**
   - Install: `npm install -g yarn`
   - Verify: `yarn --version`

3. **Python** (v3.9 or higher)
   - Download from: https://www.python.org/downloads/
   - Verify: `python --version`
   - **Important**: Check "Add Python to PATH" during installation

4. **PyInstaller** (for backend packaging)
   - Install: `pip install pyinstaller`
   - Verify: `pyinstaller --version`

5. **MongoDB** (Optional - for persistent storage)
   - Download from: https://www.mongodb.com/try/download/community
   - If not installed, app will use in-memory storage
   - Default port: 27017

6. **Git** (for version control)
   - Download from: https://git-scm.com/

### System Requirements

- **OS**: Windows 10/11 (64-bit)
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 2GB free space for build artifacts
- **Internet**: Required for initial dependency installation

---

## Project Overview

### Architecture

```
AMT Trading Bot Desktop App
├── Electron (Desktop Shell)
│   ├── Window Management
│   ├── Process Lifecycle
│   └── Backend Subprocess Control
├── React Frontend (UI)
│   ├── Market Data Visualization
│   ├── Volume Profile Charts
│   ├── Signal Dashboard
│   └── Configuration Panel
└── FastAPI Backend (Python)
    ├── Data Processing
    ├── WebSocket Server
    ├── Trading Signal Generation
    └── AI Integration (OpenRouter)
```

### Technology Stack

- **Desktop Framework**: Electron 28.x
- **Frontend**: React 18 with Shadcn/UI components
- **Backend**: FastAPI (Python)
- **Database**: MongoDB (optional) or In-Memory
- **Build Tools**: electron-builder, PyInstaller, Webpack

---

## Development Setup

### 1. Clone and Install Dependencies

```bash
# Navigate to project root
cd /path/to/amt-trading-bot

# Install frontend dependencies
cd frontend
yarn install
cd ..

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Install Electron dependencies
cd electron
yarn install
cd ..
```

### 2. Environment Configuration

#### Frontend (.env)
Create or verify `frontend/.env`:
```env
# Development uses system MongoDB
REACT_APP_BACKEND_URL=http://localhost:8001
WDS_SOCKET_PORT=443
```

#### Backend (.env)
Create or verify `backend/.env`:
```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=amt_trading_bot
CORS_ORIGINS=*
```

### 3. Run in Development Mode

```bash
# Terminal 1: Start MongoDB (if installed)
mongod --dbpath /path/to/data

# Terminal 2: Start Backend
cd backend
python server.py

# Terminal 3: Start Frontend
cd frontend
yarn start

# Terminal 4: Start Electron (optional for desktop testing)
cd electron
yarn dev
```

**Development URLs:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8001
- API Docs: http://localhost:8001/docs

---

## Building for Production

### Step 1: Prepare Python Backend

```bash
cd backend

# Clean previous builds
rm -rf dist build *.spec

# Build standalone executable
pyinstaller --onefile --name server server.py --distpath ./dist

# Verify output
ls -l dist/server.exe
```

**Expected Output:**
- `backend/dist/server.exe` (20-50 MB)

### Step 2: Build React Frontend

```bash
cd frontend

# Clean previous builds
rm -rf build

# Build optimized production bundle
yarn build

# Verify output
ls -l build/
```

**Expected Output:**
- `frontend/build/` directory with `index.html` and static assets

### Step 3: Package Electron Application

```bash
cd electron

# Build Windows installer
yarn build

# Alternative: Create unpacked directory (faster testing)
yarn pack
```

**Build Output:**
```
electron/dist/
├── AMT Trading Bot Setup 1.0.0.exe  # NSIS Installer (~100-150 MB)
└── win-unpacked/                     # Unpacked app directory
    ├── AMT Trading Bot.exe
    ├── resources/
    │   ├── app.asar
    │   ├── backend/
    │   │   └── server.exe
    │   └── frontend/
    │       └── build/
    └── ...
```

### Build Time Expectations

- **Backend build**: 2-5 minutes
- **Frontend build**: 1-3 minutes
- **Electron packaging**: 3-7 minutes
- **Total**: 10-15 minutes (first build may take longer)

---

## Distribution

### Installation Package

The final installer is located at:
```
electron/dist/AMT Trading Bot Setup 1.0.0.exe
```

### Installer Features

- **Custom Installation Path**: Users can choose install directory
- **Desktop Shortcut**: Created automatically
- **Start Menu Entry**: Added for easy access
- **Uninstaller**: Included for clean removal

### Installation Steps (End User)

1. Download `AMT Trading Bot Setup 1.0.0.exe`
2. Double-click to run installer
3. Choose installation directory (default: `C:\Program Files\AMT Trading Bot`)
4. Wait for installation to complete
5. Launch from desktop shortcut or Start Menu

### First Run Setup

1. **Configure API Keys** (if using live data):
   - OpenRouter API Key (for AI analysis)
   - Binance API Key & Secret (for live market data)

2. **Choose Data Mode**:
   - **Demo Mode**: Uses simulated market data (no API keys needed)
   - **Live Mode**: Connects to Binance real-time data

3. **MongoDB** (optional):
   - If MongoDB is installed and running on port 27017, app will use it
   - Otherwise, uses in-memory storage (data clears on app restart)

---

## Troubleshooting

### Common Issues

#### 1. PyInstaller Build Fails

**Error**: `ModuleNotFoundError` during backend build

**Solution**:
```bash
# Install missing dependencies
pip install -r requirements.txt

# Ensure all imports are available
python server.py  # Test server runs without errors

# Rebuild
pyinstaller --onefile --name server server.py --distpath ./dist
```

#### 2. Frontend Build Errors

**Error**: `Module not found` or dependency issues

**Solution**:
```bash
cd frontend

# Clear node_modules and reinstall
rm -rf node_modules yarn.lock
yarn install

# Rebuild
yarn build
```

#### 3. Electron App Won't Start

**Symptom**: App window opens but shows blank screen or error

**Solution**:
1. Check console logs in Electron developer tools
2. Verify backend.exe exists in `resources/backend/`
3. Verify frontend build exists in `resources/frontend/build/`
4. Check that backend starts correctly:
   ```bash
   cd electron/dist/win-unpacked/resources/backend
   ./server.exe
   # Should start without errors
   ```

#### 4. Backend Connection Errors

**Error**: Frontend shows "Backend not available" or connection refused

**Solution**:
1. Ensure backend is running on port 8001:
   ```bash
   netstat -ano | findstr :8001
   ```
2. Check Windows Firewall isn't blocking port 8001
3. Verify `config.js` is correctly detecting Electron environment

#### 5. MongoDB Connection Issues

**Symptom**: App runs but data doesn't persist

**Solution**:
- App automatically falls back to in-memory storage if MongoDB unavailable
- To use MongoDB:
  1. Install MongoDB Community Edition
  2. Start MongoDB service: `net start MongoDB`
  3. Verify running: `mongod --version`
  4. Restart the app

#### 6. Build Size Too Large

**Issue**: Installer exceeds 200 MB

**Solution**:
```bash
# Optimize backend build
pyinstaller --onefile --strip --name server server.py

# Optimize frontend build
cd frontend
GENERATE_SOURCEMAP=false yarn build

# Use UPX compression (optional)
# Download UPX from https://upx.github.io/
# Place upx.exe in PATH
# PyInstaller will automatically use it
```

---

## Configuration

### Application Icon

Replace placeholder icon with custom icon:

1. Create/obtain icon in multiple formats:
   - `icon.ico` (256x256 for Windows)
   - `icon.png` (512x512 source)

2. Place in `electron/assets/`

3. Rebuild: `yarn build`

### Backend Port Configuration

Default port is 8001. To change:

**File**: `electron/main.js`
```javascript
env: {
  ...process.env,
  PORT: '8001'  // Change this
}
```

**File**: `frontend/src/config.js`
```javascript
return 'http://localhost:8001';  // Change this
```

### Build Version Numbering

**File**: `electron/package.json`
```json
{
  "version": "1.0.0"  // Change this before building
}
```

Version number appears in:
- Installer filename
- Windows Add/Remove Programs
- App About dialog

---

## Advanced Configuration

### Code Signing (Optional)

For production distribution, sign the executable:

1. Obtain code signing certificate
2. Configure in `electron/package.json`:
```json
"win": {
  "certificateFile": "path/to/cert.pfx",
  "certificatePassword": "password"
}
```

### Auto-Update (Optional)

Implement electron-updater for automatic updates:

```bash
cd electron
yarn add electron-updater
```

Configure update server in `main.js`.

### Custom Splash Screen

Add loading screen while backend starts:

1. Create splash.html in `electron/`
2. Load in `main.js` before main window
3. Close when backend ready

---

## Build Checklist

Before building production release:

- [ ] Update version number in `electron/package.json`
- [ ] Test in development mode (`yarn dev`)
- [ ] Verify all dependencies installed
- [ ] Build backend: `cd backend && pyinstaller ...`
- [ ] Build frontend: `cd frontend && yarn build`
- [ ] Test backend.exe runs standalone
- [ ] Test frontend build serves correctly
- [ ] Package Electron: `cd electron && yarn build`
- [ ] Test installer on clean Windows machine
- [ ] Verify app starts without errors
- [ ] Test demo mode functionality
- [ ] Test live mode with API keys (if applicable)
- [ ] Test data persistence with MongoDB
- [ ] Check Windows Defender doesn't flag executable
- [ ] Document any manual setup steps for users

---

## File Size Reference

**Typical build sizes:**
- Backend executable: 30-50 MB
- Frontend build: 5-10 MB
- Electron framework: 80-120 MB
- **Total installer**: 120-180 MB

---

## Support

For build issues or questions:

1. Check Electron logs: `%APPDATA%\AMT Trading Bot\logs`
2. Check backend logs: Console output in dev mode
3. Review this document's Troubleshooting section
4. Check GitHub Issues (if applicable)

---

## License

MIT License - See LICENSE file for details

---

## Changelog

### Version 1.0.0
- Initial release
- Windows x64 support
- Demo and Live data modes
- Volume profile visualization
- AI analysis integration
- WebSocket real-time updates

---

**Last Updated**: 2025
**Build System Version**: 1.0
**Electron Version**: 28.x
**Node Version**: 18.x
**Python Version**: 3.9+
