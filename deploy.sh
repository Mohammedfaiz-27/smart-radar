#!/bin/bash

# SMART RADAR Production Deployment Script for Ubuntu
# Supports: setup, start, stop, restart, status commands

set -e

# Configuration
APP_NAME="smart-radar"
APP_DIR="/opt/$APP_NAME"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
LOG_DIR="/var/log/$APP_NAME"
PID_DIR="/var/run/$APP_NAME"
USER="ubuntu"
GROUP="ubuntu"

# Service names
BACKEND_SERVICE="smart-radar-backend"
CELERY_WORKER_SERVICE="smart-radar-celery-worker"
CELERY_BEAT_SERVICE="smart-radar-celery-beat"
NGINX_SERVICE="nginx"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Get public IP address
get_public_ip() {
    local ip
    # Try multiple methods to get public IP
    ip=$(curl -s ifconfig.me 2>/dev/null) || \
    ip=$(curl -s ipinfo.io/ip 2>/dev/null) || \
    ip=$(curl -s icanhazip.com 2>/dev/null) || \
    ip=$(wget -qO- ifconfig.me 2>/dev/null) || \
    ip=$(dig +short myip.opendns.com @resolver1.opendns.com 2>/dev/null)
    
    if [[ -z "$ip" ]]; then
        # Fallback to local IP if public IP detection fails
        ip=$(hostname -I | awk '{print $1}')
        warning "Could not detect public IP, using local IP: $ip" >&2
    else
        log "Detected public IP: $ip" >&2
    fi
    
    echo "$ip"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package lists
    apt update
    
    # Install essential packages
    apt install -y \
        curl \
        wget \
        git \
        nginx \
        redis-server \
        nodejs \
        npm \
        python3 \
        python3-pip \
        python3-venv \
        supervisor \
        ufw \
        htop \
        unzip \
        gnupg \
        lsb-release
    
    # Install UV (Python package manager)
    if ! command -v uv &> /dev/null; then
        log "Installing UV Python package manager..."
        # Install UV to local bin
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        # Copy UV to system-wide location so ubuntu user can access it
        if [ -f "/root/.local/bin/uv" ]; then
            cp /root/.local/bin/uv /usr/local/bin/
            chmod +x /usr/local/bin/uv
            log "UV copied to /usr/local/bin/ for system-wide access"
        fi
        
        # Add local bin to PATH for this session
        export PATH="/root/.local/bin:$PATH"
        
        # Verify installation
        if ! command -v uv &> /dev/null; then
            error "UV installation failed. Please install manually."
            exit 1
        fi
        
        log "UV installed successfully at $(which uv)"
    fi
    
    # This will be checked later after copying files
    log "Environment files will be validated after deployment"
    
    log "System dependencies installed successfully"
}

# Check if .env files exist
check_env_files() {
    if [[ ! -f "$BACKEND_DIR/.env" ]]; then
        error "Backend .env file not found at $BACKEND_DIR/.env"
        error "Please ensure the backend .env file exists with proper configuration"
        exit 1
    fi
    
    if [[ ! -f "$FRONTEND_DIR/.env" ]]; then
        error "Frontend .env file not found at $FRONTEND_DIR/.env"
        error "Please ensure the frontend .env file exists with proper configuration"
        exit 1
    fi
    
    log "Environment files found and will be used as-is"
}

# Setup application directories and users
setup_directories() {
    log "Setting up application directories..."
    
    # Create application directories
    mkdir -p $APP_DIR
    mkdir -p $LOG_DIR
    mkdir -p $PID_DIR
    
    # Set ownership
    chown -R $USER:$GROUP $APP_DIR
    chown -R $USER:$GROUP $LOG_DIR
    chown -R $USER:$GROUP $PID_DIR
    
    log "Application directories created"
}

# Deploy application code
deploy_application() {
    log "Deploying application code..."
    
    # Copy current directory to app directory
    if [ "$(pwd)" != "$APP_DIR" ]; then
        cp -r . $APP_DIR/
        chown -R $USER:$GROUP $APP_DIR
    fi
    
    # Check environment files exist
    check_env_files
    
    # Setup backend
    setup_backend
    
    # Setup frontend
    setup_frontend
    
    log "Application deployed successfully"
}

# Setup backend environment
setup_backend() {
    log "Setting up backend environment..."
    
    cd $BACKEND_DIR
    
    # Create Python virtual environment using UV
    sudo -u $USER uv venv venv
    
    # Install dependencies using pyproject.toml
    sudo -u $USER uv sync
    
    # Get public IP for environment configuration
    PUBLIC_IP=$(get_public_ip 2>/dev/null | tail -1)
    
    # Use existing .env file as-is
    log "Using existing backend .env file (no modifications)"
    chown $USER:$GROUP .env
    
    log "Backend environment configured"
}

# Setup frontend environment
setup_frontend() {
    log "Setting up frontend environment..."
    
    cd $FRONTEND_DIR
    
    # Install Node.js dependencies
    sudo -u $USER npm install
    
    # Get public IP for environment configuration
    PUBLIC_IP=$(get_public_ip 2>/dev/null | tail -1)
    
    # Use existing .env file as-is
    log "Using existing frontend .env file (no modifications)"
    
    # Build for production
    sudo -u $USER npm run build
    
    chown -R $USER:$GROUP .env dist/
    
    log "Frontend environment configured and built"
}

# Create systemd service files
create_systemd_services() {
    log "Creating systemd service files..."
    
    # Backend service
    cat > /etc/systemd/system/$BACKEND_SERVICE.service << EOF
[Unit]
Description=SMART RADAR Backend API
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$BACKEND_DIR
Environment=PATH=/root/.local/bin:$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$BACKEND_DIR/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=file:$LOG_DIR/backend.log
StandardError=file:$LOG_DIR/backend-error.log

[Install]
WantedBy=multi-user.target
EOF

    # Celery Worker service
    cat > /etc/systemd/system/$CELERY_WORKER_SERVICE.service << EOF
[Unit]
Description=SMART RADAR Celery Worker
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$BACKEND_DIR
Environment=PATH=/root/.local/bin:$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$BACKEND_DIR/venv/bin/python -m celery -A app.core.celery_app worker --loglevel=info
Restart=always
RestartSec=10
StandardOutput=file:$LOG_DIR/celery-worker.log
StandardError=file:$LOG_DIR/celery-worker-error.log

[Install]
WantedBy=multi-user.target
EOF

    # Celery Beat service
    cat > /etc/systemd/system/$CELERY_BEAT_SERVICE.service << EOF
[Unit]
Description=SMART RADAR Celery Beat Scheduler
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=$USER
Group=$GROUP
WorkingDirectory=$BACKEND_DIR
Environment=PATH=/root/.local/bin:$BACKEND_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$BACKEND_DIR/venv/bin/python -m celery -A app.core.celery_app beat --loglevel=info
Restart=always
RestartSec=10
StandardOutput=file:$LOG_DIR/celery-beat.log
StandardError=file:$LOG_DIR/celery-beat-error.log

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    systemctl daemon-reload
    
    log "Systemd services created"
}

# Configure Nginx
setup_nginx() {
    log "Configuring Nginx..."
    
    # Get public IP without log output
    PUBLIC_IP=$(get_public_ip 2>/dev/null | tail -1)
    
    # Create Nginx configuration
    cat > /etc/nginx/sites-available/$APP_NAME << EOF
server {
    listen 80;
    server_name $PUBLIC_IP;
    
    # Frontend (serve static files)
    location / {
        root $FRONTEND_DIR/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
        
        # Enable gzip compression
        gzip on;
        gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    }
    
    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # API docs
    location /docs {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
EOF

    # Enable the site
    ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
    
    # Remove default site
    rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    nginx -t
    
    log "Nginx configured successfully"
}

# Configure firewall
setup_firewall() {
    log "Configuring firewall..."
    
    # Reset UFW
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH
    ufw allow ssh
    
    # Allow HTTP and HTTPS
    ufw allow 80
    ufw allow 443
    
    # Allow backend port (for direct access if needed)
    ufw allow 8000
    
    # Enable UFW
    ufw --force enable
    
    log "Firewall configured"
}

# Start all services
start_services() {
    log "Starting all services..."
    
    # Start Redis service
    systemctl start redis-server
    
    # Start application services
    systemctl start $BACKEND_SERVICE
    systemctl start $CELERY_WORKER_SERVICE
    systemctl start $CELERY_BEAT_SERVICE
    
    # Start web server
    systemctl start nginx
    
    # Enable services to start on boot
    systemctl enable redis-server
    systemctl enable $BACKEND_SERVICE
    systemctl enable $CELERY_WORKER_SERVICE
    systemctl enable $CELERY_BEAT_SERVICE
    systemctl enable nginx
    
    log "All services started and enabled"
}

# Stop all services
stop_services() {
    log "Stopping all services..."
    
    systemctl stop nginx
    systemctl stop $CELERY_BEAT_SERVICE
    systemctl stop $CELERY_WORKER_SERVICE
    systemctl stop $BACKEND_SERVICE
    
    log "All services stopped"
}

# Restart all services
restart_services() {
    log "Restarting all services..."
    
    stop_services
    sleep 5
    start_services
    
    log "All services restarted"
}


# Full setup
full_setup() {
    log "Starting full SMART RADAR setup..."
    
    check_root
    install_dependencies
    setup_directories
    deploy_application
    create_systemd_services
    setup_nginx
    setup_firewall
    start_services
    
    PUBLIC_IP=$(get_public_ip 2>/dev/null | tail -1)
    
    log "Setup completed successfully!"
    echo ""
    echo -e "${GREEN}=== SMART RADAR is now running! ===${NC}"
    echo -e "Access your application at: ${BLUE}http://$PUBLIC_IP${NC}"
    echo -e "API documentation: ${BLUE}http://$PUBLIC_IP/docs${NC}"
    echo ""
    echo -e "Use the following commands to manage your application:"
    echo -e "  ${YELLOW}sudo ./deploy.sh start${NC}     - Start all services"
    echo -e "  ${YELLOW}sudo ./deploy.sh stop${NC}      - Stop all services"
    echo -e "  ${YELLOW}sudo ./deploy.sh restart${NC}   - Restart all services"
}

# Main script logic
if [[ $# -eq 0 ]]; then
    error "No command specified"
    echo "Usage: $0 {setup|start|stop|restart}"
    echo ""
    echo "Commands:"
    echo "  setup   - Full installation and setup (run once)"
    echo "  start   - Start all services"
    echo "  stop    - Stop all services"
    echo "  restart - Restart all services"
    exit 1
fi

case "$1" in
    "setup")
        full_setup
        ;;
    "start")
        check_root
        start_services
        ;;
    "stop")
        check_root
        stop_services
        ;;
    "restart")
        check_root
        restart_services
        ;;
    *)
        error "Invalid command: $1"
        echo "Usage: $0 {setup|start|stop|restart}"
        echo ""
        echo "Commands:"
        echo "  setup   - Full installation and setup (run once)"
        echo "  start   - Start all services"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        exit 1
        ;;
esac