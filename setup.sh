#!/bin/bash

# SMART RADAR MVP - Setup Script for Ubuntu
# Installs all necessary tools and dependencies

echo "🔧 SMART RADAR MVP - Setup Script (Ubuntu)"
echo "==========================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "⚠️  This script is optimized for Ubuntu/Debian Linux."
    echo "Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update package list
echo "📦 Updating package list..."
sudo apt update

# Check and install Python 3.11+
echo ""
echo "🐍 Checking for Python 3.11+..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    echo "Found Python $PYTHON_VERSION"
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
        echo "⚠️  Python 3.11+ required. Installing..."
        sudo apt install -y software-properties-common
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt update
        sudo apt install -y python3.11 python3.11-venv python3.11-dev
    else
        echo "✅ Python version is sufficient"
    fi
else
    echo "Installing Python 3.11..."
    sudo apt install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3.11-dev
fi

# Install pip if not available
echo ""
echo "📦 Checking for pip..."
if ! command -v pip3 &> /dev/null; then
    echo "Installing pip..."
    sudo apt install -y python3-pip
else
    echo "✅ pip already installed"
fi

# Check and install UV
echo ""
echo "📦 Checking for UV package manager..."
if ! command -v uv &> /dev/null; then
    echo "Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add to current session
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "✅ UV already installed"
fi

# Check and install Node.js
echo ""
echo "📦 Checking for Node.js..."
if ! command -v node &> /dev/null; then
    echo "Installing Node.js (LTS version)..."
    curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
    sudo apt install -y nodejs
else
    NODE_VERSION=$(node --version)
    echo "✅ Node.js $NODE_VERSION already installed"
fi

# Check and install MongoDB
echo ""
echo "🍃 Checking for MongoDB..."
if ! command -v mongod &> /dev/null; then
    echo "Installing MongoDB 7.0..."
    # Import MongoDB GPG key
    curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
        sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor

    # Add MongoDB repository
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" | \
        sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

    # Install MongoDB
    sudo apt update
    sudo apt install -y mongodb-org

    # Start and enable MongoDB service
    echo "Starting MongoDB service..."
    sudo systemctl start mongod
    sudo systemctl enable mongod
else
    echo "✅ MongoDB already installed"
    echo "Ensuring MongoDB is running..."
    sudo systemctl start mongod 2>/dev/null || true
    sudo systemctl enable mongod 2>/dev/null || true
fi

# Setup backend
echo ""
echo "🔧 Setting up backend..."
cd "$(dirname "$0")/backend"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# MongoDB Configuration
MONGODB_URL=mongodb://admin:password@localhost:27017/smart_radar?authSource=admin

# OpenAI API Key (REQUIRED - Add your key here)
OPENAI_API_KEY=your_openai_api_key_here

# Debug Mode
DEBUG=true

# CORS Origins
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Automatic Data Collection Configuration
ENABLE_AUTO_COLLECTION=true
DATA_COLLECTION_INTERVAL_MINUTES=30
INTELLIGENCE_PROCESSING_INTERVAL_MINUTES=15
THREAT_MONITORING_INTERVAL_MINUTES=5
DAILY_ANALYTICS_ENABLED=true
WEEKLY_CLEANUP_ENABLED=true
EOF
    echo "⚠️  Please edit backend/.env and add your OPENAI_API_KEY"
fi

# Create virtual environment and install dependencies
echo "Installing Python dependencies with UV..."
uv venv
uv pip install -r requirements.txt

# Setup frontend
echo ""
echo "⚛️  Setting up frontend..."
cd ../frontend

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating frontend .env file..."
    cat > .env << EOF
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
EOF
fi

# Install frontend dependencies
echo "Installing Node.js dependencies..."
npm install

# Create logs directory
echo ""
echo "📁 Creating logs directory..."
cd ..
mkdir -p logs

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Edit backend/.env and add your OPENAI_API_KEY"
echo "   2. Ensure MongoDB is running: brew services start mongodb-community@7.0"
echo "   3. Start all services: ./start_simple.sh"
echo ""
echo "📊 Services will be available at:"
echo "   • Frontend: http://localhost:5173"
echo "   • Backend API: http://localhost:8000"
echo "   • API Docs: http://localhost:8000/docs"
echo ""
