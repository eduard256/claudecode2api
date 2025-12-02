#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Claude Code API Gateway Installation ===${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed!${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Python $REQUIRED_VERSION or higher is required (found $PYTHON_VERSION)${NC}"
    exit 1
fi
echo -e "${GREEN}Python $PYTHON_VERSION detected${NC}"

# Check if Claude Code is available
echo -e "\n${YELLOW}Checking Claude Code CLI...${NC}"
if command -v claude &> /dev/null; then
    CLAUDE_PATH=$(which claude)
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    echo -e "${GREEN}Claude Code found: $CLAUDE_PATH ($CLAUDE_VERSION)${NC}"
else
    echo -e "${RED}Claude Code CLI not found in PATH!${NC}"
    echo -e "${YELLOW}Please install Claude Code first: https://claude.ai/code${NC}"
    exit 1
fi

# Create virtual environment
echo -e "\n${YELLOW}Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment already exists, skipping...${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created${NC}"
fi

# Activate and install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}Dependencies installed${NC}"

# Create .env if not exists
echo -e "\n${YELLOW}Setting up configuration...${NC}"
if [ -f ".env" ]; then
    echo -e "${YELLOW}.env file already exists, skipping...${NC}"
else
    cp .env.example .env
    echo -e "${GREEN}.env file created from template${NC}"
    echo -e "${RED}IMPORTANT: Edit .env file to set AUTH_USER and AUTH_PASSWORD!${NC}"
fi

# Ask about systemd installation
echo -e "\n${YELLOW}Install as systemd service?${NC}"
read -p "This will enable auto-start on boot (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Get current user
    CURRENT_USER=$(whoami)

    # Update service file with correct paths
    echo -e "\n${YELLOW}Configuring systemd service...${NC}"

    # Create service file with actual paths
    cat > claudecode2api.service << EOF
[Unit]
Description=Claude Code API Gateway
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$SCRIPT_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9876
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Copy service file
    sudo cp claudecode2api.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable claudecode2api

    echo -e "${GREEN}Systemd service installed and enabled${NC}"
    echo -e "${YELLOW}Start with: sudo systemctl start claudecode2api${NC}"
    echo -e "${YELLOW}View logs: sudo journalctl -u claudecode2api -f${NC}"
else
    echo -e "${YELLOW}Skipping systemd installation${NC}"
    echo -e "Manual start: source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 9876"
fi

echo -e "\n${GREEN}=== Installation Complete ===${NC}"
echo -e ""
echo -e "Next steps:"
echo -e "1. Edit .env file to set AUTH_USER and AUTH_PASSWORD"
echo -e "2. Start the server:"
echo -e "   - Systemd: ${YELLOW}sudo systemctl start claudecode2api${NC}"
echo -e "   - Manual:  ${YELLOW}source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 9876${NC}"
echo -e "3. Test: ${YELLOW}curl http://localhost:9876/health${NC}"
echo -e "4. API Docs: ${YELLOW}http://localhost:9876/docs${NC}"
