# Docker on Windows - Troubleshooting Guide

Quick fixes for common Docker issues on Windows.

---

## Error: "yarn.lock": not found

### Problem
```
failed to calculate checksum of ref: "/yarn.lock": not found
```

### Solution 1: Generate yarn.lock (Recommended)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (this creates yarn.lock)
yarn install

# Go back to root
cd ..

# Now build Docker
docker compose up -d --build
```

### Solution 2: Use the Fix Script

```bash
# Run the automated fix
docker-fix-windows.bat

# Then build
docker compose up -d --build
```

### Why This Happens
The `yarn.lock` file is created when you run `yarn install` locally. Docker needs this file to ensure consistent dependency versions. The Dockerfile has been updated to make this optional, but it's best practice to have it.

---

## Error: Version Attribute Warning

### Problem
```
level=warning msg="the attribute `version` is obsolete"
```

### Solution
This is just a warning, not an error. The docker-compose.yml has been updated to remove the version field. You can safely ignore this warning, or update your file by removing the first line if it says `version: '3.8'`.

---

## Error: Port Already in Use

### Problem
```
Error starting userland proxy: listen tcp 0.0.0.0:80: bind: address already in use
```

### Solution

**Option 1: Stop the conflicting service**
```bash
# Find what's using port 80
netstat -ano | findstr :80

# Stop IIS (if installed)
iisreset /stop

# Or stop other web servers
```

**Option 2: Change the port in docker-compose.yml**
```yaml
frontend:
  ports:
    - "8080:80"  # Change 80 to 8080
```

Then access at: http://localhost:8080

---

## Error: Docker Not Running

### Problem
```
error during connect: This error may indicate that the docker daemon is not running
```

### Solution
1. Open Docker Desktop
2. Wait for Docker to fully start (whale icon in system tray)
3. Try again

---

## Error: WSL 2 Installation Error

### Problem
Docker Desktop requires WSL 2 on Windows.

### Solution
1. Open PowerShell as Administrator
2. Run:
   ```powershell
   wsl --install
   wsl --set-default-version 2
   ```
3. Restart computer
4. Open Docker Desktop

---

## Error: Drive Not Shared

### Problem
```
Error: Drive has not been shared
```

### Solution
1. Open Docker Desktop
2. Settings → Resources → File Sharing
3. Add `C:\` drive
4. Apply & Restart

---

## Error: MongoDB Connection Failed

### Problem
Backend can't connect to MongoDB.

### Solution

**Check MongoDB is running:**
```bash
docker compose ps
```

**Check MongoDB logs:**
```bash
docker compose logs mongodb
```

**Restart MongoDB:**
```bash
docker compose restart mongodb
```

**Rebuild everything:**
```bash
docker compose down -v
docker compose up -d --build
```

---

## Error: Frontend Shows 502 Bad Gateway

### Problem
nginx can't reach the backend.

### Solution

**Check backend is running:**
```bash
docker compose ps
```

**Check backend logs:**
```bash
docker compose logs backend
```

**Check if backend is healthy:**
```bash
docker inspect amt-backend
```

**Restart backend:**
```bash
docker compose restart backend
```

---

## Performance Issues on Windows

### Problem
Docker is slow on Windows.

### Solutions

1. **Use WSL 2 backend** (Settings → General → Use WSL 2)
2. **Allocate more resources** (Settings → Resources):
   - CPUs: 4+
   - Memory: 4GB+
   - Swap: 2GB+
3. **Move project to WSL 2 filesystem**:
   ```bash
   # In WSL 2
   cd ~
   git clone <your-repo>
   cd xtrend-bot-public
   docker compose up -d --build
   ```

---

## Line Ending Issues (CRLF vs LF)

### Problem
```
/bin/sh: ./script.sh: not found
```

### Solution
Windows uses CRLF line endings, Docker needs LF.

**Fix globally:**
```bash
git config --global core.autocrlf input
```

**Fix for this project:**
```bash
cd /path/to/project
git config core.autocrlf input
git rm --cached -r .
git reset --hard
```

---

## Build is Very Slow

### Problem
Docker build takes 10+ minutes.

### Solutions

1. **Check antivirus isn't scanning Docker folders**
   - Exclude: `C:\ProgramData\Docker`
   - Exclude: `C:\Users\<username>\.docker`

2. **Use BuildKit** (already enabled in newer Docker)

3. **Clear Docker cache**:
   ```bash
   docker builder prune -a
   ```

4. **Use faster DNS**:
   Docker Desktop → Settings → Docker Engine:
   ```json
   {
     "dns": ["8.8.8.8", "8.8.4.4"]
   }
   ```

---

## Complete Reset

### When All Else Fails

```bash
# Stop everything
docker compose down -v

# Remove all containers, images, volumes
docker system prune -a --volumes

# Restart Docker Desktop

# Rebuild from scratch
docker compose up -d --build
```

---

## Pre-flight Checklist

Before running `docker compose up -d --build`, ensure:

- [ ] Docker Desktop is running
- [ ] WSL 2 is installed (Windows 10/11)
- [ ] At least 4GB RAM allocated to Docker
- [ ] `frontend/yarn.lock` exists (run `cd frontend && yarn install`)
- [ ] Ports 80, 8001, 27017 are free
- [ ] `.env` files configured (optional for demo mode)
- [ ] Antivirus not blocking Docker

---

## Quick Commands Reference

```bash
# Build and start
docker compose up -d --build

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f backend

# Check status
docker compose ps

# Restart service
docker compose restart backend

# Stop all
docker compose down

# Stop and remove volumes
docker compose down -v

# Clean up everything
docker system prune -a
```

---

## Getting Help

1. **Check logs**: `docker compose logs -f`
2. **Check this guide**: Common issues listed above
3. **Docker Docs**: https://docs.docker.com/desktop/windows/
4. **Full deployment guide**: [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

---

## Success Checklist

Once running, verify:

1. All containers running:
   ```bash
   docker compose ps
   ```
   Should show: mongodb (healthy), backend (healthy), frontend (healthy)

2. Frontend accessible:
   - Open browser: http://localhost
   - Should see AMT Trading Bot interface

3. Backend accessible:
   - Open browser: http://localhost:8001/docs
   - Should see FastAPI documentation

4. WebSocket working:
   - Open browser console on http://localhost
   - Should see "WebSocket connected"

5. Demo mode works:
   - Toggle "Demo" in header
   - Should see simulated market data

---

**If you've followed these steps and still have issues, please share:**
- Error message
- Output of `docker compose ps`
- Output of `docker compose logs backend`
- Windows version
- Docker Desktop version
