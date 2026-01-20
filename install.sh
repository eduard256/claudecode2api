#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/eduard256/claudecode2api.git"
INSTALL_DIR="$HOME/claudecode2api"
SERVICE_NAME="claudecode2api"
REQUIRED_PYTHON_VERSION="3.10"

echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Claude Code API Gateway Installation    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if running as root
check_not_root() {
    if [ "$EUID" -eq 0 ]; then
        echo -e "${RED}ERROR: Do not run this script as root!${NC}"
        echo -e "${YELLOW}Run as normal user: curl -fsSL https://raw.githubusercontent.com/eduard256/claudecode2api/main/install.sh | bash${NC}"
        exit 1
    fi
}

# Request sudo password upfront
request_sudo() {
    echo -e "${YELLOW}╔════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  This script requires sudo access         ║${NC}"
    echo -e "${YELLOW}║  You will be prompted for your password   ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════╝${NC}"
    echo ""
    sudo -v

    # Keep sudo alive
    while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null &
}

# Update system and install base packages
install_system_dependencies() {
    echo -e "\n${BLUE}[1/8] Updating system and installing dependencies...${NC}"

    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y \
            curl \
            git \
            python3 \
            python3-pip \
            python3-venv \
            build-essential \
            ca-certificates
        echo -e "${GREEN}✓ System dependencies installed (apt)${NC}"
    elif command -v yum &> /dev/null; then
        sudo yum update -y
        sudo yum install -y \
            curl \
            git \
            python3 \
            python3-pip \
            python3-devel \
            gcc \
            ca-certificates
        echo -e "${GREEN}✓ System dependencies installed (yum)${NC}"
    elif command -v dnf &> /dev/null; then
        sudo dnf update -y
        sudo dnf install -y \
            curl \
            git \
            python3 \
            python3-pip \
            python3-devel \
            gcc \
            ca-certificates
        echo -e "${GREEN}✓ System dependencies installed (dnf)${NC}"
    else
        echo -e "${RED}ERROR: Unsupported package manager. Please install dependencies manually.${NC}"
        exit 1
    fi
}

# Check Python version
check_python_version() {
    echo -e "\n${BLUE}[2/8] Checking Python version...${NC}"

    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: Python 3 is not installed!${NC}"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')

    if [ "$(printf '%s\n' "$REQUIRED_PYTHON_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON_VERSION" ]; then
        echo -e "${RED}ERROR: Python $REQUIRED_PYTHON_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"
}

# Install Claude Code CLI
install_claude_code() {
    echo -e "\n${BLUE}[3/8] Installing Claude Code CLI...${NC}"

    # Always run the installer - it handles existing installations
    if curl -fsSL https://claude.ai/install.sh | bash; then
        # Add to PATH permanently
        if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' ~/.bashrc; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
            echo -e "${GREEN}✓ Added ~/.local/bin to PATH in ~/.bashrc${NC}"
        fi

        # Update PATH for current session
        export PATH="$HOME/.local/bin:$PATH"

        # Check installation
        if [ -f "$HOME/.local/bin/claude" ]; then
            CLAUDE_VERSION=$($HOME/.local/bin/claude --version 2>/dev/null || echo "unknown")
            echo -e "${GREEN}✓ Claude Code installed: $CLAUDE_VERSION${NC}"
        else
            echo -e "${RED}ERROR: Claude Code installation failed!${NC}"
            exit 1
        fi
    else
        echo -e "${RED}ERROR: Failed to install Claude Code!${NC}"
        exit 1
    fi
}

# Clone or update repository
setup_repository() {
    echo -e "\n${BLUE}[4/8] Setting up repository...${NC}"

    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}Repository already exists, updating...${NC}"
        cd "$INSTALL_DIR"

        # Stash any local changes
        git stash save "Auto-stash before update" 2>/dev/null || true

        # Pull latest changes
        git pull origin main
        echo -e "${GREEN}✓ Repository updated${NC}"
    else
        echo -e "${YELLOW}Cloning repository to $INSTALL_DIR...${NC}"
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
        echo -e "${GREEN}✓ Repository cloned${NC}"
    fi
}

# Setup Python virtual environment
setup_virtualenv() {
    echo -e "\n${BLUE}[5/8] Setting up Python virtual environment...${NC}"

    cd "$INSTALL_DIR"

    if [ -d "venv" ]; then
        echo -e "${YELLOW}Virtual environment exists, recreating...${NC}"
        rm -rf venv
    fi

    python3 -m venv venv
    source venv/bin/activate

    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    echo -e "${GREEN}✓ Virtual environment created and dependencies installed${NC}"
}

# Configure .env file
configure_env() {
    echo -e "\n${BLUE}[6/8] Configuring environment...${NC}"

    cd "$INSTALL_DIR"

    # Check if .env already exists and has credentials
    if [ -f ".env" ]; then
        if grep -q "^AUTH_USER=" .env && grep -q "^AUTH_PASSWORD=" .env; then
            EXISTING_USER=$(grep "^AUTH_USER=" .env | cut -d= -f2)
            if [ "$EXISTING_USER" != "admin" ] && [ "$EXISTING_USER" != "changeme" ]; then
                echo -e "${GREEN}✓ .env file already configured${NC}"
                return
            fi
        fi
    fi

    # Create base .env if not exists
    if [ ! -f ".env" ]; then
        cat > .env << 'EOF'
HOST=0.0.0.0
PORT=9876
LOG_LEVEL=DEBUG
EOF
    fi

    # Add CLAUDE_PATH if not present
    if ! grep -q "^CLAUDE_PATH=" .env; then
        echo "CLAUDE_PATH=$HOME/.local/bin/claude" >> .env
    fi

    # Ask for credentials
    echo -e "\n${YELLOW}═══════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  API Authentication Configuration${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
    echo ""

    # Use /dev/tty to read from terminal even when piped
    read -p "Enter API username: " API_USER < /dev/tty
    while [ -z "$API_USER" ]; do
        echo -e "${RED}Username cannot be empty!${NC}"
        read -p "Enter API username: " API_USER < /dev/tty
    done

    read -sp "Enter API password: " API_PASSWORD < /dev/tty
    echo ""
    while [ -z "$API_PASSWORD" ]; do
        echo -e "${RED}Password cannot be empty!${NC}"
        read -sp "Enter API password: " API_PASSWORD < /dev/tty
        echo ""
    done

    # Update or add credentials
    if grep -q "^AUTH_USER=" .env; then
        sed -i "s/^AUTH_USER=.*/AUTH_USER=$API_USER/" .env
    else
        echo "AUTH_USER=$API_USER" >> .env
    fi

    if grep -q "^AUTH_PASSWORD=" .env; then
        sed -i "s/^AUTH_PASSWORD=.*/AUTH_PASSWORD=$API_PASSWORD/" .env
    else
        echo "AUTH_PASSWORD=$API_PASSWORD" >> .env
    fi

    echo -e "${GREEN}✓ Credentials configured${NC}"
}

# Setup systemd service
setup_systemd() {
    echo -e "\n${BLUE}[7/8] Setting up systemd service...${NC}"

    cd "$INSTALL_DIR"

    # Create service file
    cat > /tmp/${SERVICE_NAME}.service << EOF
[Unit]
Description=Claude Code API Gateway
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9876
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Install service
    sudo cp /tmp/${SERVICE_NAME}.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME

    # Stop if running, then start
    sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
    sudo systemctl start $SERVICE_NAME

    # Wait a bit for service to start
    sleep 2

    # Check status
    if sudo systemctl is-active --quiet $SERVICE_NAME; then
        echo -e "${GREEN}✓ Service started and enabled${NC}"
    else
        echo -e "${YELLOW}⚠ Service installed but may not be running. Check: sudo systemctl status $SERVICE_NAME${NC}"
    fi
}

# Claude Code login
claude_login() {
    echo -e "\n${BLUE}[8/8] Claude Code authentication...${NC}"
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   Installation Complete!                  ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Last step: You need to login to Claude Code${NC}"
    echo -e "${YELLOW}The Claude Code CLI will open now...${NC}"
    echo ""
    echo -e "Press Enter to continue..."
    read < /dev/tty

    # Run claude login (will open browser or show instructions)
    export PATH="$HOME/.local/bin:$PATH"

    # Check if already logged in
    if claude user 2>/dev/null | grep -q "@"; then
        echo -e "${GREEN}✓ Already logged in to Claude Code${NC}"
    else
        # Open claude for login
        claude < /dev/tty
    fi
}

# Display final information
show_final_info() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          Installation Summary              ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Service Status:${NC}"
    echo -e "  • Status: ${GREEN}$(sudo systemctl is-active $SERVICE_NAME)${NC}"
    echo -e "  • Autostart: ${GREEN}enabled${NC}"
    echo ""
    echo -e "${BLUE}API Information:${NC}"
    echo -e "  • URL: ${YELLOW}http://localhost:9876${NC}"
    echo -e "  • Health: ${YELLOW}http://localhost:9876/health${NC}"
    echo -e "  • Docs: ${YELLOW}http://localhost:9876/docs${NC}"
    echo ""
    echo -e "${BLUE}Service Management:${NC}"
    echo -e "  • Start: ${YELLOW}sudo systemctl start $SERVICE_NAME${NC}"
    echo -e "  • Stop: ${YELLOW}sudo systemctl stop $SERVICE_NAME${NC}"
    echo -e "  • Restart: ${YELLOW}sudo systemctl restart $SERVICE_NAME${NC}"
    echo -e "  • Status: ${YELLOW}sudo systemctl status $SERVICE_NAME${NC}"
    echo -e "  • Logs: ${YELLOW}sudo journalctl -u $SERVICE_NAME -f${NC}"
    echo ""
    echo -e "${BLUE}Configuration:${NC}"
    echo -e "  • Location: ${YELLOW}$INSTALL_DIR/.env${NC}"
    echo ""
    echo -e "${GREEN}Test the API:${NC}"
    echo -e "  curl http://localhost:9876/health"
    echo ""
}

# Main installation flow
main() {
    check_not_root
    request_sudo
    install_system_dependencies
    check_python_version
    install_claude_code
    setup_repository
    setup_virtualenv
    configure_env
    setup_systemd
    show_final_info
    claude_login
}

# Run main function
main
