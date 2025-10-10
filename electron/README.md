# AMT Trading Bot - Electron Desktop Application

This directory contains the Electron wrapper that packages the AMT Trading Bot as a Windows desktop application.

## Quick Start

### Development Mode

```bash
# Ensure backend and frontend dependencies are installed
cd ../backend && pip install -r requirements.txt
cd ../frontend && yarn install
cd ../electron && yarn install

# Run in development mode (starts Electron with system backend/frontend)
yarn dev
```

### Production Build

See [BUILD_INSTRUCTIONS.md](../BUILD_INSTRUCTIONS.md) for complete build instructions.

**Quick build command:**
```bash
# On Windows
build.bat

# Manual build
yarn build
```

## Project Structure

```
electron/
├── main.js              # Electron main process (app lifecycle, window management)
├── preload.js           # Preload script (secure context bridge)
├── package.json         # Electron dependencies and build configuration
├── build.bat            # Windows build automation script
├── assets/              # Application icons and resources
│   └── icon_readme.txt  # Instructions for icon files
└── dist/                # Build output directory (created during build)
```

## How It Works

### Architecture

1. **Electron Shell** (`main.js`):
   - Creates application window
   - Manages app lifecycle (startup, shutdown)
   - Spawns FastAPI backend as subprocess
   - Checks MongoDB availability

2. **Backend Integration**:
   - Starts `server.exe` (bundled FastAPI) on `localhost:8001`
   - Sets environment variables for internal access
   - Monitors backend health

3. **Frontend Loading**:
   - **Dev Mode**: Loads from `http://localhost:3000` (React dev server)
   - **Production**: Loads from bundled `build/index.html`
   - Frontend auto-detects Electron and uses `localhost:8001` for API

4. **Data Storage**:
   - Checks for MongoDB on `localhost:27017`
   - Falls back to in-memory storage if MongoDB unavailable
   - User data stored in `app.getPath('userData')`

### Environment Detection

The frontend uses `config.js` to detect if running in Electron:

```javascript
const isElectron = () => window.electron !== undefined;
const backendUrl = isElectron() ? 'http://localhost:8001' : process.env.REACT_APP_BACKEND_URL;
```

## Configuration

### Build Settings

Edit `package.json` to configure:

- **Version**: `"version": "1.0.0"`
- **App ID**: `"appId": "com.amt.tradingbot"`
- **Product Name**: `"productName": "AMT Trading Bot"`
- **Build Target**: `"target": ["nsis"]` (Windows installer)

### Electron Window

Edit `main.js` to configure:

```javascript
new BrowserWindow({
  width: 1400,      // Window width
  height: 900,      // Window height
  title: 'AMT Trading Bot',
  // ... other options
})
```

### Backend Configuration

Backend environment variables are set in `main.js`:

```javascript
env: {
  MONGO_URL: 'mongodb://localhost:27017',
  DB_NAME: 'amt_trading_bot',
  CORS_ORIGINS: '*',
  PORT: '8001'
}
```

## Development Tips

### Testing Electron in Dev Mode

1. Start backend manually:
   ```bash
   cd backend && python server.py
   ```

2. Start frontend manually:
   ```bash
   cd frontend && yarn start
   ```

3. Launch Electron:
   ```bash
   cd electron && yarn dev
   ```

This allows hot-reload for both backend and frontend.

### Debugging

**Enable DevTools in production:**

Edit `main.js`:
```javascript
mainWindow.webContents.openDevTools();
```

**View Electron logs:**
- Windows: `%APPDATA%\AMT Trading Bot\logs`
- Or run from command line to see console output

**Check backend status:**
```bash
# Check if backend is running
netstat -ano | findstr :8001

# Test API manually
curl http://localhost:8001/api/status
```

## Building

### Prerequisites

- Node.js 18+
- Python 3.9+
- PyInstaller (`pip install pyinstaller`)
- Yarn (`npm install -g yarn`)

### Build Steps

1. **Build Backend**:
   ```bash
   cd ../backend
   pyinstaller --onefile --name server server.py --distpath ./dist
   ```

2. **Build Frontend**:
   ```bash
   cd ../frontend
   yarn build
   ```

3. **Package Electron**:
   ```bash
   cd ../electron
   yarn build
   ```

**Automated build:**
```bash
cd electron
build.bat  # Windows
```

### Build Output

```
electron/dist/
├── AMT Trading Bot Setup 1.0.0.exe  # Windows installer
└── win-unpacked/                     # Unpacked application
    ├── AMT Trading Bot.exe           # Main executable
    └── resources/
        ├── backend/server.exe        # Bundled backend
        └── frontend/build/           # Bundled frontend
```

## Troubleshooting

### App won't start

1. Check if port 8001 is already in use
2. Verify `backend/dist/server.exe` exists
3. Verify `frontend/build/` exists with `index.html`
4. Run Electron from terminal to see error messages

### Backend connection errors

- Frontend shows "Backend not available"
- **Solution**: Ensure backend starts successfully. Check logs in dev tools.

### Blank window

- Window opens but nothing loads
- **Solution**: Check console for errors. Verify frontend build path in `main.js`.

### MongoDB errors

- App works but data doesn't persist
- **Solution**: MongoDB is optional. App uses in-memory storage as fallback.

### Build fails

- **PyInstaller error**: `pip install -r requirements.txt` then rebuild
- **Frontend error**: `rm -rf node_modules && yarn install` then rebuild
- **Electron error**: Check `electron-builder` version compatibility

## Distribution

### Installer

The NSIS installer (`AMT Trading Bot Setup 1.0.0.exe`) includes:
- Application executable
- Backend server (embedded)
- Frontend static files
- Uninstaller
- Desktop and Start Menu shortcuts

### Installation

Users simply double-click the installer and follow prompts:
1. Choose installation directory
2. Wait for installation
3. Launch from desktop shortcut

No separate installation of Python, Node.js, or dependencies required.

## Advanced

### Code Signing

For trusted distribution, sign the executable:

1. Obtain Windows code signing certificate
2. Configure in `package.json`:
   ```json
   "win": {
     "certificateFile": "path/to/cert.pfx",
     "certificatePassword": "your-password"
   }
   ```

### Auto-Update

Implement automatic updates:

```bash
yarn add electron-updater
```

Configure update server and implement update logic in `main.js`.

### Custom Icon

1. Create `icon.ico` (256x256)
2. Place in `electron/assets/`
3. Reference in `package.json`:
   ```json
   "win": {
     "icon": "assets/icon.ico"
   }
   ```

## Support

For detailed instructions, see [BUILD_INSTRUCTIONS.md](../BUILD_INSTRUCTIONS.md).

## License

MIT License
