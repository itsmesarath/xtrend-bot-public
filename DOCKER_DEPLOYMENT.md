# Docker Deployment Guide - AMT Trading Bot

Complete guide for deploying the AMT Trading Bot using Docker containers.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Building Images](#building-images)
5. [Running Containers](#running-containers)
6. [Configuration](#configuration)
7. [Production Deployment](#production-deployment)
8. [Cloud Deployments](#cloud-deployments)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Launch the Application

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8001
# API Docs: http://localhost:8001/docs
```

### Stop the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (deletes data)
docker-compose down -v
```

---

## Prerequisites

### Required Software

- **Docker** (v20.10+)
  - Download: https://www.docker.com/get-started
  - Verify: `docker --version`

- **Docker Compose** (v2.0+)
  - Usually included with Docker Desktop
  - Verify: `docker-compose --version`

### System Requirements

- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 5GB free space for images and data
- **OS**: Windows, macOS, or Linux

---

## Architecture

### Container Structure

```
AMT Trading Bot (Docker)
├── frontend (nginx:alpine)
│   ├── React build (static files)
│   ├── nginx proxy
│   └── Port: 80
├── backend (python:3.11-slim)
│   ├── FastAPI server
│   ├── Trading logic
│   └── Port: 8001
└── mongodb (mongo:7.0)
    ├── Database
    ├── Persistent storage
    └── Port: 27017
```

### Network Flow

```
User Browser → Frontend (nginx:80)
              ↓ /api/* requests
              → Backend (FastAPI:8001)
                ↓
                → MongoDB (27017)
```

### Docker Compose Services

1. **mongodb**:
   - Official MongoDB 7.0 image
   - Data persisted in named volumes
   - Health checks enabled

2. **backend**:
   - Custom Python image
   - FastAPI + trading logic
   - Depends on MongoDB

3. **frontend**:
   - Multi-stage build (Node.js → nginx)
   - Serves React app
   - Proxies API requests to backend

---

## Building Images

### Build All Images

```bash
# Build all services
docker-compose build

# Build with no cache (fresh build)
docker-compose build --no-cache

# Build specific service
docker-compose build backend
```

### Build Individual Images

```bash
# Backend
cd backend
docker build -t amt-backend:latest .

# Frontend
cd frontend
docker build -t amt-frontend:latest .
```

### Image Sizes (Approximate)

- **Frontend**: ~50 MB (nginx + React build)
- **Backend**: ~400 MB (Python + dependencies)
- **MongoDB**: ~700 MB (official image)
- **Total**: ~1.15 GB

---

## Running Containers

### Start All Services

```bash
# Start in detached mode (background)
docker-compose up -d

# Start with logs visible
docker-compose up

# Start specific service
docker-compose up -d backend
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 -f
```

### Service Management

```bash
# Check status
docker-compose ps

# Restart service
docker-compose restart backend

# Stop all services
docker-compose stop

# Start stopped services
docker-compose start

# Remove containers (keeps data)
docker-compose down

# Remove containers and volumes (deletes data)
docker-compose down -v
```

### Access Services

- **Frontend**: http://localhost
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **MongoDB**: mongodb://localhost:27017

---

## Configuration

### Environment Variables

Create `.env` file in the root directory:

```env
# MongoDB
MONGO_URL=mongodb://mongodb:27017
DB_NAME=amt_trading_bot

# Backend
CORS_ORIGINS=*
PORT=8001

# API Keys (optional)
OPENROUTER_API_KEY=your_key_here
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
```

Then update `docker-compose.yml`:

```yaml
backend:
  env_file:
    - .env
```

### Custom Ports

Edit `docker-compose.yml` to change exposed ports:

```yaml
frontend:
  ports:
    - "8080:80"  # Access at http://localhost:8080

backend:
  ports:
    - "9000:8001"  # Access at http://localhost:9000
```

### Volume Mounting (Development)

For live code reloading during development:

```yaml
backend:
  volumes:
    - ./backend:/app
    - /app/__pycache__  # Exclude cache

frontend:
  volumes:
    - ./frontend/src:/app/src
```

---

## Production Deployment

### Security Hardening

1. **Environment Variables**:
   ```bash
   # Use secrets instead of .env files
   docker secret create mongo_url mongodb://mongodb:27017
   ```

2. **Non-root User**:
   Add to Dockerfiles:
   ```dockerfile
   RUN useradd -m -u 1000 appuser
   USER appuser
   ```

3. **Limit Resources**:
   ```yaml
   backend:
     deploy:
       resources:
         limits:
           cpus: '1.0'
           memory: 1G
         reservations:
           cpus: '0.5'
           memory: 512M
   ```

### HTTPS/SSL

Use a reverse proxy like Traefik or nginx-proxy with Let's Encrypt:

```yaml
services:
  traefik:
    image: traefik:v2.10
    command:
      - "--certificatesresolvers.le.acme.email=your@email.com"
      - "--certificatesresolvers.le.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"
```

### Backup Strategy

```bash
# Backup MongoDB data
docker-compose exec mongodb mongodump --out /backup

# Copy backup to host
docker cp amt-mongodb:/backup ./mongodb-backup-$(date +%Y%m%d)

# Restore from backup
docker-compose exec -T mongodb mongorestore /backup
```

---

## Cloud Deployments

### AWS (ECS/Fargate)

1. **Push images to ECR**:
   ```bash
   aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
   docker tag amt-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/amt-backend:latest
   docker push <account>.dkr.ecr.<region>.amazonaws.com/amt-backend:latest
   ```

2. **Create ECS Task Definition** with 3 containers
3. **Deploy to Fargate** for serverless containers

### Google Cloud (Cloud Run)

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/amt-backend ./backend
gcloud builds submit --tag gcr.io/PROJECT_ID/amt-frontend ./frontend

# Deploy
gcloud run deploy amt-backend --image gcr.io/PROJECT_ID/amt-backend
gcloud run deploy amt-frontend --image gcr.io/PROJECT_ID/amt-frontend
```

### Azure (Container Instances)

```bash
# Create container group
az container create \
  --resource-group amt-trading-bot \
  --name amt-app \
  --image amt-backend:latest \
  --dns-name-label amt-trading-bot \
  --ports 80 8001
```

### DigitalOcean (App Platform)

1. Connect GitHub repository
2. Auto-detect Dockerfiles
3. Configure environment variables
4. Deploy with one click

### Heroku

```bash
# Install Heroku CLI
heroku container:login

# Push and release
heroku container:push web -a amt-trading-bot
heroku container:release web -a amt-trading-bot
```

---

## Monitoring

### Health Checks

All services include health checks. Check status:

```bash
# View health status
docker-compose ps

# Detailed inspect
docker inspect --format='{{json .State.Health}}' amt-backend
```

### Resource Usage

```bash
# Real-time stats
docker stats

# Check container logs for errors
docker-compose logs --tail=50 backend | grep ERROR
```

### Prometheus + Grafana (Advanced)

Add monitoring stack to `docker-compose.yml`:

```yaml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"

grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  depends_on:
    - prometheus
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Inspect container
docker inspect amt-backend

# Check if port is in use
netstat -tulpn | grep 8001
```

### MongoDB Connection Issues

```bash
# Test MongoDB connection
docker-compose exec backend python -c "from motor.motor_asyncio import AsyncIOMotorClient; client = AsyncIOMotorClient('mongodb://mongodb:27017'); print('Connected')"

# Check MongoDB logs
docker-compose logs mongodb

# Restart MongoDB
docker-compose restart mongodb
```

### Frontend Can't Reach Backend

```bash
# Check nginx config
docker-compose exec frontend cat /etc/nginx/conf.d/default.conf

# Test backend from frontend container
docker-compose exec frontend wget -O- http://backend:8001/api/status

# Check network
docker network inspect amt-trading-network
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase Docker memory limit (Docker Desktop Settings)
# Or add resource limits to docker-compose.yml
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose up -d --build

# Force rebuild (no cache)
docker-compose build --no-cache
docker-compose up -d
```

### Clean Up Old Images

```bash
# Remove unused images
docker image prune -a

# Remove everything (careful!)
docker system prune -a --volumes
```

---

## Performance Optimization

### Multi-stage Builds

Already implemented in frontend Dockerfile to minimize image size.

### Layer Caching

Order Dockerfile commands from least to most frequently changing:

```dockerfile
COPY requirements.txt .    # Changes rarely
RUN pip install -r requirements.txt
COPY . .                   # Changes often
```

### Reduce Image Size

```bash
# Use alpine base images where possible
FROM python:3.11-alpine

# Clean up in same layer
RUN apt-get update && apt-get install -y package \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
```

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build images
        run: docker-compose build
      - name: Push to registry
        run: |
          docker-compose push
```

### GitLab CI

```yaml
build:
  stage: build
  script:
    - docker-compose build
    - docker-compose push
```

---

## Common Commands Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f

# Rebuild
docker-compose up -d --build

# Status
docker-compose ps

# Shell access
docker-compose exec backend bash
docker-compose exec frontend sh

# Database shell
docker-compose exec mongodb mongosh

# Restart service
docker-compose restart backend

# Remove everything
docker-compose down -v
docker system prune -a
```

---

## Security Checklist

- [ ] Use environment variables for secrets (not hardcoded)
- [ ] Enable HTTPS/SSL in production
- [ ] Implement rate limiting
- [ ] Run containers as non-root user
- [ ] Keep base images updated
- [ ] Scan images for vulnerabilities
- [ ] Use Docker secrets for sensitive data
- [ ] Implement network segmentation
- [ ] Enable container logging
- [ ] Regular backups of MongoDB data

---

## Support

For Docker-specific issues:
1. Check logs: `docker-compose logs -f`
2. Review this troubleshooting section
3. Check Docker documentation: https://docs.docker.com

For application issues:
- See main [README.md](README.md)
- Check [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)

---

## License

MIT License

---

**Last Updated**: 2025
**Docker Version**: 20.10+
**Docker Compose Version**: 2.0+
