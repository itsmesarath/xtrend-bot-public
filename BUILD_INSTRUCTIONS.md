# Building AMT Trading Signal Bot as Electron Desktop App

## Prerequisites

### Required Software
1. **Node.js & npm** (v18+)
2. **Python** (v3.10+)
3. **MongoDB** (Download portable version)
4. **PyInstaller** (for packaging Python backend)

### Install Build Tools

```bash
# Install PyInstaller
pip install pyinstaller

# Install Electron dependencies
cd electron
npm install
```

## Build Process

### Step 1: Prepare Frontend

```bash
cd frontend
npm run build
# This creates production build in frontend/build/
```

### Step 2: Package Backend with PyInstaller

```bash
cd backend

# Windows
pyinstaller --onefile --name server ^
  --hidden-import uvicorn ^
  --hidden-import fastapi ^
  --hidden-import motor ^
  --collect-all pydantic ^
  server.py

# Mac/Linux
pyinstaller --onefile --name server \
  --hidden-import uvicorn \
  --hidden-import fastapi \
  --hidden-import motor \
  --collect-all pydantic \
  server.py

# Output: backend/dist/server (or server.exe on Windows)
```

### Step 3: Download Portable MongoDB

**Windows:**
```bash
# Download from: https://www.mongodb.com/try/download/community
# Extract to: electron/mongodb/
# Structure: electron/mongodb/bin/mongod.exe
```

**Mac:**
```bash
# Download MongoDB Community Server
# Extract to: electron/mongodb/
# Structure: electron/mongodb/bin/mongod
```

**Linux:**
```bash
# Download from MongoDB website
# Extract to: electron/mongodb/
# Structure: electron/mongodb/bin/mongod
```

### Step 4: Build Electron App

```bash
cd electron

# Build for current platform
npm run build

# Or build for specific platforms:
npm run build:win    # Windows
npm run build:mac    # macOS
npm run build:linux  # Linux
```

### Output Locations

- **Windows**: `electron/dist/AMT Trading Bot Setup.exe`
- **Mac**: `electron/dist/AMT Trading Bot.dmg`
- **Linux**: `electron/dist/AMT Trading Bot.AppImage`

## Alternative: Simplified Build (Without MongoDB)

If bundling MongoDB is too complex, use SQLite instead:

### 1. Install SQLite Support

```bash
pip install aiosqlite sqlalchemy
```

### 2. Update Backend to Use SQLite

Replace MongoDB connection in `backend/server.py`:

```python
# Instead of MongoDB
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import aiosqlite

# SQLite database will be in user's AppData folder
db_path = os.path.join(app.getPath('userData'), 'amt_bot.db')
DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
```

### 3. Smaller Build Size

Without MongoDB, your app will be:
- **Windows**: ~150MB (vs 500MB with MongoDB)
- **Mac**: ~200MB (vs 600MB with MongoDB)
- **Linux**: ~180MB (vs 550MB with MongoDB)

## Development Mode

Test before building:

```bash
# Terminal 1: Start MongoDB
mongod --dbpath ./data

# Terminal 2: Start Backend
cd backend
python server.py

# Terminal 3: Start Frontend
cd frontend
npm start

# Terminal 4: Start Electron (connects to running services)
cd electron
npm start
```

## Troubleshooting

### Backend Not Starting

**Issue**: PyInstaller missing dependencies

**Solution**: Add to PyInstaller command:
```bash
--hidden-import <module_name>
--collect-all <package_name>
```

### MongoDB Won't Start

**Issue**: Port 27017 already in use

**Solution**: Change port in `main.js`:
```javascript
'--port', '27018'  // Use different port
```

### App Crashes on Startup

**Issue**: Services not fully initialized

**Solution**: Increase timeout in `main.js`:
```javascript
setTimeout(() => resolve(), 15000); // Increase from 10s to 15s
```

## Distribution

### Code Signing (Optional but Recommended)

**Windows**: Get code signing certificate
```bash
electron-builder --win --sign
```

**Mac**: Use Apple Developer certificate
```bash
electron-builder --mac --sign
```

### Auto-Updates (Optional)

Add electron-updater for automatic updates:
```bash
npm install electron-updater
```

## File Sizes (Approximate)

| Platform | With MongoDB | Without MongoDB (SQLite) |
|----------|--------------|-------------------------|
| Windows  | ~500 MB      | ~150 MB                |
| macOS    | ~600 MB      | ~200 MB                |
| Linux    | ~550 MB      | ~180 MB                |

## Recommended Approach

### For Distribution:
1. **Use SQLite** instead of MongoDB (simpler, smaller)
2. **Build for each platform separately** (requires respective OS)
3. **Test thoroughly** on each platform before distribution
4. **Consider code signing** for production releases

### For Personal Use:
1. Keep MongoDB if you prefer (full functionality)
2. Build only for your platform
3. No code signing needed

## Next Steps

1. Choose database approach (MongoDB or SQLite)
2. Follow build steps above
3. Test the generated installer
4. Distribute to users

## Support

For build issues, check:
- PyInstaller logs in `backend/build/`
- Electron builder logs in `electron/dist/`
- Runtime logs in app's console (F12 in dev mode)
