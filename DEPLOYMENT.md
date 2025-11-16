# SMART RADAR Production Deployment Guide

This guide covers deploying SMART RADAR to an Ubuntu server in production mode with automatic public IP detection.

## Prerequisites

- Ubuntu 20.04+ server with sudo access
- Internet connection for package installation
- At least 2GB RAM and 10GB disk space
- MongoDB Atlas cluster with connection string
- OpenAI API key (optional, for AI response generation)

## Quick Deployment

1. **Upload the project to your Ubuntu server:**
   ```bash
   # Option 1: Using SCP
   scp -r smart-radar/ user@your-server-ip:/home/user/

   # Option 2: Using Git
   git clone <your-repo-url>
   cd smart-radar
   ```

2. **Set your MongoDB Atlas connection string:**
   ```bash
   export MONGODB_ATLAS_URI="mongodb+srv://username:password@cluster.mongodb.net/smart_radar?retryWrites=true&w=majority"
   ```

3. **Run the deployment script:**
   ```bash
   # Make script executable
   chmod +x deploy.sh

   # Run full setup (requires sudo)
   sudo ./deploy.sh setup
   ```

4. **Access your application:**
   - The script will automatically detect your server's public IP
   - Application will be available at: `http://YOUR_PUBLIC_IP`
   - API documentation: `http://YOUR_PUBLIC_IP/docs`

## Script Commands

The `deploy.sh` script supports the following commands:

### Setup (Run Once)
```bash
sudo ./deploy.sh setup
```
Performs complete installation and configuration:
- Installs system dependencies (Node.js, Python, MongoDB, Redis, Nginx)
- Sets up application directories and permissions
- Creates systemd services for all components
- Configures Nginx reverse proxy
- Sets up firewall rules
- Starts all services

### Service Management
```bash
# Start all services
sudo ./deploy.sh start

# Stop all services
sudo ./deploy.sh stop

# Restart all services
sudo ./deploy.sh restart

# Check service status
./deploy.sh status
```

### Monitoring and Maintenance
```bash
# View all logs
./deploy.sh logs

# View specific service logs
./deploy.sh logs backend
./deploy.sh logs worker
./deploy.sh logs beat
./deploy.sh logs nginx

# Update application (pull latest code and restart)
sudo ./deploy.sh update
```

## What Gets Installed

### System Dependencies
- **Node.js & NPM** - Frontend build and runtime
- **Python 3.11+** - Backend runtime
- **UV** - Python package manager (replaces pip/virtualenv)
- **Redis** - Message broker for Celery tasks
- **Nginx** - Web server and reverse proxy
- **Systemd** - Process management

### Application Services
- **Backend API** - FastAPI server on port 8000
- **Celery Worker** - Background task processing
- **Celery Beat** - Periodic task scheduler
- **Frontend** - Vue.js built for production
- **Database** - MongoDB Atlas (cloud-hosted)

## Configuration

### Environment Variables

The script automatically creates production environment files:

**Backend (.env):**
```bash
MONGODB_URL=your_mongodb_atlas_connection_string
OPENAI_API_KEY=your_openai_api_key_here
REDIS_URL=redis://localhost:6379
DEBUG=false
CORS_ORIGINS=http://YOUR_PUBLIC_IP,https://YOUR_PUBLIC_IP
ENABLE_AUTO_COLLECTION=true
DATA_COLLECTION_INTERVAL_MINUTES=30
NEWS_COLLECTION_INTERVAL_MINUTES=60
ENABLE_NEWS_COLLECTION=true
```

**Frontend (.env):**
```bash
VITE_API_URL=http://YOUR_PUBLIC_IP/api
VITE_WS_URL=ws://YOUR_PUBLIC_IP/ws
NODE_ENV=production
```

### Adding Your API Keys

After deployment, add your API keys:

```bash
# Edit backend environment file
sudo nano /opt/smart-radar/backend/.env

# Update these lines:
MONGODB_URL=your_actual_mongodb_atlas_connection_string
OPENAI_API_KEY=your_actual_openai_api_key_here

# Restart backend service
sudo ./deploy.sh restart
```

## Architecture Overview

### Directory Structure
```
/opt/smart-radar/           # Application root
├── backend/                # Python FastAPI application
│   ├── venv/              # UV virtual environment
│   └── .env               # Backend configuration
├── frontend/              # Vue.js application
│   ├── dist/              # Production build
│   └── .env               # Frontend configuration
/var/log/smart-radar/      # Application logs
/var/run/smart-radar/      # PID files
```

### Network Architecture
```
Internet → Nginx (Port 80) → {
    / → Frontend (Static Files)
    /api/ → Backend API (Port 8000)
    /ws → WebSocket (Port 8000)
    /docs → API Documentation
}
```

### Service Dependencies
```
MongoDB Atlas ← Backend API ← Nginx
Redis         ← Celery Worker
              ← Celery Beat
```

## Security Features

### Firewall Configuration
- SSH (22) - Allowed
- HTTP (80) - Allowed  
- HTTPS (443) - Allowed
- Backend (8000) - Allowed (for direct API access)
- All other ports - Denied

### Application Security
- MongoDB Atlas with built-in security and authentication
- Nginx security headers configured
- CORS properly configured for public IP
- Static file serving with gzip compression

## Monitoring and Troubleshooting

### Check Service Status
```bash
# Individual service status
sudo systemctl status smart-radar-backend
sudo systemctl status smart-radar-celery-worker
sudo systemctl status smart-radar-celery-beat
sudo systemctl status nginx
sudo systemctl status redis-server
```

### View Logs
```bash
# Application logs
tail -f /var/log/smart-radar/backend.log
tail -f /var/log/smart-radar/celery-worker.log
tail -f /var/log/smart-radar/celery-beat.log

# System logs
sudo journalctl -u smart-radar-backend -f
sudo journalctl -u nginx -f

# Nginx access logs
tail -f /var/log/nginx/access.log
```

### Common Issues

**Services won't start:**
```bash
# Check service logs
sudo journalctl -u smart-radar-backend
sudo journalctl -u smart-radar-celery-worker

# Verify dependencies
sudo systemctl status mongod
sudo systemctl status redis-server
```

**Can't access application:**
```bash
# Check nginx configuration
sudo nginx -t

# Verify firewall rules
sudo ufw status

# Check if services are listening
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :8000
```

**Database connection issues:**
```bash
# Test MongoDB connection
mongosh "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"

# Check MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log
```

## Updating the Application

### Automated Update
```bash
# Pull latest code and restart (if using git)
sudo ./deploy.sh update
```

### Manual Update
```bash
# Stop services
sudo ./deploy.sh stop

# Update code (copy new files or git pull)
# ...

# Restart services
sudo ./deploy.sh start
```

## Performance Optimization

### For High Traffic
```bash
# Increase Nginx worker processes
sudo nano /etc/nginx/nginx.conf
# Set: worker_processes auto;

# Add more Celery workers
sudo nano /etc/systemd/system/smart-radar-celery-worker.service
# Add: --concurrency=4

# Reload systemd and restart
sudo systemctl daemon-reload
sudo ./deploy.sh restart
```

### Database Optimization
```bash
# Enable MongoDB oplog for better performance
mongosh "mongodb://admin:password@localhost:27017/smart_radar?authSource=admin"
# Run: rs.initiate()
```

## Backup and Recovery

### Backup Database
```bash
# Create backup
mongodump --uri="mongodb://admin:password@localhost:27017/smart_radar?authSource=admin" --out=/opt/backups/

# Restore backup
mongorestore --uri="mongodb://admin:password@localhost:27017/smart_radar?authSource=admin" /opt/backups/smart_radar/
```

### Backup Application
```bash
# Create application backup
tar -czf smart-radar-backup-$(date +%Y%m%d).tar.gz /opt/smart-radar/
```

## SSL/HTTPS Setup (Optional)

To enable HTTPS with Let's Encrypt:

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

## Support

For issues and questions:
- Check logs: `./deploy.sh logs`
- View status: `./deploy.sh status`
- Restart services: `sudo ./deploy.sh restart`
- Review this documentation

The deployment script handles all major configuration automatically, including public IP detection and environment setup.