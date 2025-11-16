#!/bin/bash

# SMART RADAR MVP - Nginx Setup Script
# Installs and configures Nginx as reverse proxy

echo "🌐 SMART RADAR MVP - Nginx Setup"
echo "================================="
echo ""

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Linux*)
        if [ "$EUID" -ne 0 ]; then
            echo "⚠️  This script requires sudo privileges"
            echo "Running with sudo..."
            sudo "$0" "$@"
            exit $?
        fi

        echo "📦 Installing Nginx on Linux..."
        if command -v apt &> /dev/null; then
            apt update
            apt install -y nginx
        elif command -v yum &> /dev/null; then
            yum install -y nginx
        else
            echo "❌ Unsupported package manager. Please install nginx manually."
            exit 1
        fi
        ;;
    Darwin*)
        echo "📦 Installing Nginx on macOS..."
        if ! command -v brew &> /dev/null; then
            echo "❌ Homebrew not found. Please install Homebrew first: https://brew.sh"
            exit 1
        fi
        brew install nginx 2>/dev/null || brew upgrade nginx
        ;;
    *)
        echo "❌ Unsupported operating system: $OS"
        exit 1
        ;;
esac

# Get server IP/hostname
echo ""
echo "🔍 Detecting server IP address..."
case "$OS" in
    Linux*)
        SERVER_IP=$(hostname -I | awk '{print $1}')
        NGINX_CONF_DIR="/etc/nginx"
        NGINX_SITES_AVAILABLE="$NGINX_CONF_DIR/sites-available"
        NGINX_SITES_ENABLED="$NGINX_CONF_DIR/sites-enabled"
        ;;
    Darwin*)
        SERVER_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
        NGINX_CONF_DIR="/opt/homebrew/etc/nginx"
        [ ! -d "$NGINX_CONF_DIR" ] && NGINX_CONF_DIR="/usr/local/etc/nginx"
        NGINX_SITES_AVAILABLE="$NGINX_CONF_DIR/servers"
        NGINX_SITES_ENABLED="$NGINX_CONF_DIR/servers"
        mkdir -p "$NGINX_SITES_AVAILABLE"
        ;;
esac

echo "Detected IP: $SERVER_IP"
echo ""
read -p "Enter server IP/domain (press Enter to use $SERVER_IP): " CUSTOM_IP
if [ -n "$CUSTOM_IP" ]; then
    SERVER_IP=$CUSTOM_IP
fi

# Get project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

echo ""
echo "📁 Project directory: $PROJECT_DIR"
echo "📁 Nginx config directory: $NGINX_CONF_DIR"
echo ""

# Create Nginx configuration
echo "⚙️  Creating Nginx configuration..."

CONF_FILE="$NGINX_SITES_AVAILABLE/smart-radar"
if [ "$OS" = "Darwin" ]; then
    CONF_FILE="$NGINX_SITES_AVAILABLE/smart-radar.conf"
fi

cat > "$CONF_FILE" << EOF
# SMART RADAR MVP - Nginx Configuration
# Generated on $(date)

upstream backend_api {
    server 127.0.0.1:8000;
}

upstream frontend_dev {
    server 127.0.0.1:5173;
}

server {
    listen 80;
    listen [::]:80;
    server_name $SERVER_IP _;

    # Increase buffer sizes for API responses
    client_max_body_size 50M;
    proxy_buffer_size 128k;
    proxy_buffers 4 256k;
    proxy_busy_buffers_size 256k;

    # Logging
    access_log /var/log/nginx/smart-radar-access.log;
    error_log /var/log/nginx/smart-radar-error.log;

    # API endpoints
    location /api/ {
        proxy_pass http://backend_api/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;

        # CORS headers (if needed)
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization' always;

        # Handle preflight requests
        if (\$request_method = 'OPTIONS') {
            return 204;
        }
    }

    # WebSocket endpoint
    location /ws {
        proxy_pass http://backend_api/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }

    # API docs
    location /docs {
        proxy_pass http://backend_api/docs;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /redoc {
        proxy_pass http://backend_api/redoc;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /openapi.json {
        proxy_pass http://backend_api/openapi.json;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Frontend (Vite dev server or production build)
    location / {
        # Development mode - proxy to Vite dev server
        proxy_pass http://frontend_dev;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;

        # For Vite HMR
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Production mode - serve static files
        # Uncomment these lines and comment out the proxy_pass above when using production build
        # root $PROJECT_DIR/frontend/dist;
        # try_files \$uri \$uri/ /index.html;
    }

    # Static assets for production (optional)
    location /assets/ {
        # Production only
        # root $PROJECT_DIR/frontend/dist;
        # expires 1y;
        # add_header Cache-Control "public, immutable";

        # Development - proxy to Vite
        proxy_pass http://frontend_dev/assets/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }
}
EOF

# Enable the site (Linux only - sites-enabled pattern)
if [ "$OS" = "Linux" ]; then
    echo "🔗 Enabling Smart Radar site..."
    ln -sf "$NGINX_SITES_AVAILABLE/smart-radar" "$NGINX_SITES_ENABLED/"

    # Remove default site if it exists
    if [ -f "$NGINX_SITES_ENABLED/default" ]; then
        echo "🗑️  Removing default Nginx site..."
        rm "$NGINX_SITES_ENABLED/default"
    fi
fi

# Test Nginx configuration
echo ""
echo "🧪 Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    # Reload Nginx
    echo ""
    echo "🔄 Reloading Nginx..."
    case "$OS" in
        Linux*)
            systemctl reload nginx
            systemctl enable nginx
            ;;
        Darwin*)
            brew services restart nginx
            ;;
    esac

    echo ""
    echo "✅ Nginx setup complete!"
    echo ""
    echo "📋 Configuration Summary:"
    echo "   • Nginx config: $CONF_FILE"
    if [ "$OS" = "Linux" ]; then
        echo "   • Access logs: /var/log/nginx/smart-radar-access.log"
        echo "   • Error logs: /var/log/nginx/smart-radar-error.log"
    else
        echo "   • Access logs: $NGINX_CONF_DIR/logs/smart-radar-access.log"
        echo "   • Error logs: $NGINX_CONF_DIR/logs/smart-radar-error.log"
    fi
    echo ""
    echo "🌐 Access your application:"
    echo "   • Frontend: http://$SERVER_IP"
    echo "   • API: http://$SERVER_IP/api/"
    echo "   • API Docs: http://$SERVER_IP/docs"
    echo "   • WebSocket: ws://$SERVER_IP/ws"
    echo ""
    echo "⚠️  Production mode:"
    echo "   1. Build frontend: cd frontend && npm run build"
    echo "   2. Edit $CONF_FILE"
    echo "   3. Uncomment production static file serving"
    echo "   4. Comment out development proxy_pass"
    if [ "$OS" = "Linux" ]; then
        echo "   5. Reload: sudo systemctl reload nginx"
    else
        echo "   5. Reload: brew services restart nginx"
    fi
    echo ""
    echo "🔧 Useful commands:"
    if [ "$OS" = "Linux" ]; then
        echo "   • Check status: sudo systemctl status nginx"
        echo "   • Reload config: sudo systemctl reload nginx"
        echo "   • View logs: sudo tail -f /var/log/nginx/smart-radar-error.log"
    else
        echo "   • Check status: brew services list | grep nginx"
        echo "   • Reload config: brew services restart nginx"
        echo "   • View logs: tail -f $NGINX_CONF_DIR/logs/smart-radar-error.log"
        echo "   • Test config: nginx -t"
    fi
    echo ""
else
    echo ""
    echo "❌ Nginx configuration test failed!"
    echo "Please check the configuration file: $CONF_FILE"
    exit 1
fi
