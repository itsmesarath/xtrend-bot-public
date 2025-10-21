// Configuration utility to handle different environments
// Detects if running in Electron and uses appropriate backend URL

const isElectron = () => {
  // Check if running in Electron
  return (
    typeof window !== 'undefined' &&
    window.electron !== undefined
  );
};

const getBackendUrl = () => {
  if (isElectron()) {
    // Internal API access for Electron desktop app
    return 'http://localhost:8001';
  }
  
  // Docker deployment: REACT_APP_BACKEND_URL is set to '/api' for nginx proxy
  // Otherwise use full URL for standard web deployment
  const envUrl = process.env.REACT_APP_BACKEND_URL;
  
  // If envUrl starts with '/', it's a relative path (Docker with nginx)
  if (envUrl && envUrl.startsWith('/')) {
    return ''; // Empty string so API_URL becomes '/api'
  }
  
  return envUrl || 'http://localhost:8001';
};

export const BACKEND_URL = getBackendUrl();
export const API_URL = `${BACKEND_URL}/api`;
export const WS_URL = BACKEND_URL.replace('http', 'ws');
export const IS_ELECTRON = isElectron();

// Log configuration on load
if (process.env.NODE_ENV === 'development') {
  console.log('Environment Configuration:', {
    isElectron: IS_ELECTRON,
    backendUrl: BACKEND_URL,
    apiUrl: API_URL,
    wsUrl: WS_URL
  });
}
