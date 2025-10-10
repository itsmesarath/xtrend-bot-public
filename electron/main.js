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

// Check if MongoDB is accessible
async function checkMongoDB() {
  return new Promise((resolve) => {
    const net = require('net');
    const socket = new net.Socket();
    
    socket.setTimeout(2000);
    socket.on('connect', () => {
      console.log('MongoDB is accessible on localhost:27017');
      socket.destroy();
      resolve(true);
    });
    
    socket.on('timeout', () => {
      console.warn('MongoDB not found on localhost:27017 - backend will use in-memory fallback');
      socket.destroy();
      resolve(false);
    });
    
    socket.on('error', () => {
      console.warn('MongoDB not found - backend will use in-memory fallback');
      socket.destroy();
      resolve(false);
    });
    
    socket.connect(27017, 'localhost');
  });
}

// Start FastAPI Backend
function startBackend() {
  return new Promise((resolve, reject) => {
    console.log('Starting FastAPI backend...');

    const command = isDev ? 'python' : BACKEND_PATH;
    const args = isDev ? [BACKEND_PATH] : [];
    
    // Get user data path for app storage
    const userDataPath = app.getPath('userData');

    backendProcess = spawn(command, args, {
      env: {
        ...process.env,
        MONGO_URL: 'mongodb://localhost:27017',
        DB_NAME: 'amt_trading_bot',
        CORS_ORIGINS: '*',
        PORT: '8001',
        USER_DATA_PATH: userDataPath
      },
      cwd: isDev ? path.join(__dirname, '..', 'backend') : process.resourcesPath
    });

    backendProcess.stdout.on('data', (data) => {
      const output = data.toString();
      console.log(`Backend: ${output}`);
      if (output.includes('Application startup complete') || output.includes('Uvicorn running')) {
        resolve();
      }
    });

    backendProcess.stderr.on('data', (data) => {
      const error = data.toString();
      console.error(`Backend Error: ${error}`);
      // Don't reject on stderr as uvicorn logs to stderr
    });

    backendProcess.on('error', (error) => {
      console.error('Failed to start backend:', error);
      reject(error);
    });

    backendProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`);
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
    // Check MongoDB availability
    const mongoAvailable = await checkMongoDB();
    if (mongoAvailable) {
      console.log('MongoDB is available');
    } else {
      console.log('MongoDB not available - will use in-memory storage');
    }
    
    // Start backend
    await startBackend();
    console.log('Backend started successfully');
    
    // Wait for backend to fully initialize
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    createWindow();
  } catch (error) {
    console.error('Failed to start application:', error);
    // Still create window to show error to user
    createWindow();
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
