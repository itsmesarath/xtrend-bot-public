const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const isDev = process.env.NODE_ENV === 'development';

let mainWindow;
let backendProcess;

// Paths for bundled executables
const BACKEND_PATH = isDev 
  ? path.join(__dirname, '..', 'backend', 'server.py')
  : path.join(process.resourcesPath, 'backend', 'server.exe');

const PYTHON_PATH = isDev
  ? 'python'
  : path.join(process.resourcesPath, 'python', 'python.exe');

// Start MongoDB
function startMongoDB() {
  return new Promise((resolve, reject) => {
    const fs = require('fs');
    
    // Create MongoDB data directory if it doesn't exist
    if (!fs.existsSync(MONGO_DATA_PATH)) {
      fs.mkdirSync(MONGO_DATA_PATH, { recursive: true });
    }

    console.log('Starting MongoDB...');
    
    mongoProcess = spawn(MONGO_PATH, [
      '--dbpath', MONGO_DATA_PATH,
      '--port', '27017',
      '--noauth'
    ], {
      env: { ...process.env }
    });

    mongoProcess.stdout.on('data', (data) => {
      console.log(`MongoDB: ${data}`);
      if (data.toString().includes('Waiting for connections')) {
        resolve();
      }
    });

    mongoProcess.stderr.on('data', (data) => {
      console.error(`MongoDB Error: ${data}`);
    });

    mongoProcess.on('error', (error) => {
      console.error('Failed to start MongoDB:', error);
      reject(error);
    });

    // Timeout after 10 seconds
    setTimeout(() => {
      resolve(); // Resolve anyway, backend will retry connection
    }, 10000);
  });
}

// Start FastAPI Backend
function startBackend() {
  return new Promise((resolve, reject) => {
    console.log('Starting FastAPI backend...');

    const pythonCommand = isDev ? 'python' : BACKEND_PATH;
    const args = isDev ? [BACKEND_PATH] : [];

    backendProcess = spawn(pythonCommand, args, {
      env: {
        ...process.env,
        MONGO_URL: 'mongodb://localhost:27017',
        DB_NAME: 'amt_trading_bot',
        CORS_ORIGINS: 'http://localhost:3000',
        PORT: '8001'
      }
    });

    backendProcess.stdout.on('data', (data) => {
      console.log(`Backend: ${data}`);
      if (data.toString().includes('Application startup complete')) {
        resolve();
      }
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`Backend Error: ${data}`);
    });

    backendProcess.on('error', (error) => {
      console.error('Failed to start backend:', error);
      reject(error);
    });

    // Timeout after 15 seconds
    setTimeout(() => {
      resolve(); // Resolve anyway, will show error in app if needed
    }, 15000);
  });
}

// Create main window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    title: 'AMT Trading Signal Bot'
  });

  // Load React app
  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'build', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// App lifecycle
app.whenReady().then(async () => {
  try {
    // Start services in sequence
    await startMongoDB();
    console.log('MongoDB started successfully');
    
    await startBackend();
    console.log('Backend started successfully');
    
    // Wait a bit for backend to fully initialize
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    createWindow();
  } catch (error) {
    console.error('Failed to start application:', error);
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  console.log('Shutting down services...');
  
  // Kill backend
  if (backendProcess) {
    backendProcess.kill('SIGTERM');
    setTimeout(() => backendProcess.kill('SIGKILL'), 5000);
  }
  
  // Kill MongoDB
  if (mongoProcess) {
    mongoProcess.kill('SIGTERM');
    setTimeout(() => mongoProcess.kill('SIGKILL'), 5000);
  }
});

// Handle crashes
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});
