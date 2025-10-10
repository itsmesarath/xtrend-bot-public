# Quick Start Guide - AMT Trading Bot

## For End Users (Windows Desktop)

### Download & Install

1. Get the installer: `AMT Trading Bot Setup 1.0.0.exe`
2. Double-click to install
3. Follow installation wizard
4. Launch from desktop shortcut

### First Time Setup

1. **Demo Mode (No API Keys)**:
   - Just launch the app
   - Toggle "Demo" in header
   - Start exploring!

2. **Live Mode (With API Keys)**:
   - Click "Configure" button
   - Enter Binance API Key & Secret
   - (Optional) Add OpenRouter key for AI
   - Toggle "Live" mode
   - Start trading!

---

## For Developers (Building from Source)

### Prerequisites Check

```bash
# Verify installations
node --version    # Need 18+
python --version  # Need 3.9+
yarn --version    # Need latest
pyinstaller --version  # Need latest
```

### Quick Build (Windows)

```bash
cd electron
build.bat
```

That's it! Installer will be at: `electron/dist/AMT Trading Bot Setup 1.0.0.exe`

### Manual Build (Step-by-Step)

```bash
# 1. Build Backend
cd backend
pyinstaller --onefile --name server server.py --distpath ./dist

# 2. Build Frontend
cd ../frontend
yarn build

# 3. Package Electron
cd ../electron
yarn install
yarn build
```

### Development Mode

```bash
# Terminal 1: Backend
cd backend && python server.py

# Terminal 2: Frontend  
cd frontend && yarn start

# Terminal 3: Electron (optional)
cd electron && yarn dev
```

---

## Web Application (Current Deployment)

Already running at: https://auction-market-3.preview.emergentagent.com

**To restart services:**
```bash
sudo supervisorctl restart all
```

**To check logs:**
```bash
tail -f /var/log/supervisor/backend.*.log
tail -f /var/log/supervisor/frontend.*.log
```

---

## Common Issues

### Desktop App

**Won't start?**
- Check if MongoDB installed (optional, app has fallback)
- Check if port 8001 is free
- Run from command line to see errors

**Blank screen?**
- Open DevTools (Ctrl+Shift+I in dev mode)
- Check for JavaScript errors
- Verify frontend build exists

### Building

**PyInstaller fails?**
```bash
pip install -r requirements.txt
python server.py  # Test it runs first
```

**Electron build fails?**
```bash
cd electron
rm -rf node_modules
yarn install
```

---

## More Help

- **Complete Build Guide**: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)
- **Electron Details**: [electron/README.md](electron/README.md)
- **Project Overview**: [README.md](README.md)

---

## Support

Need help?
1. Check the documentation files above
2. Review error logs
3. Verify prerequisites installed

---

**Happy Trading! 📈**
