#!/bin/bash
#
# Lambda Cut Installer
# Automated setup for Lambda Cut - YouTube Shorts Pipeline
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Lambda Cut Installer${NC}"
echo "========================"
echo ""

# Check if running as root or has sudo
if [ "$EUID" -ne 0 ] && ! sudo -v 2>/dev/null; then
    echo -e "${YELLOW}Note: Some commands may require sudo${NC}"
fi

# Check Python version
echo -e "${GREEN}Checking prerequisites...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo -e "${RED}Error: Python 3.10+ required. Found: $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python $python_version"

# Check ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${RED}Error: ffmpeg not found. Install with: sudo pacman -S ffmpeg${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} ffmpeg"

# Check git
if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: git not found. Install with: sudo pacman -S git${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} git"

echo ""

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Clone or update repository
if [ -d ".git" ]; then
    echo -e "${GREEN}Updating existing installation...${NC}"
else
    echo -e "${YELLOW}This doesn't appear to be a git repository.${NC}"
    echo "For fresh install, clone first:"
    echo "  git clone https://github.com/judecabodil22/lambda-cut-project.git"
    echo ""
    echo "Continuing with local setup..."
fi

# Create virtual environment
echo ""
echo -e "${GREEN}Creating virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# Install requirements
echo ""
echo -e "${GREEN}Installing Python dependencies...${NC}"
pip install -r requirements.txt 2>/dev/null || echo -e "${YELLOW}Note: requirements.txt may not exist yet${NC}"

# Copy .env.example if .env doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo -e "${GREEN}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your API keys!${NC}"
else
    echo -e "${GREEN}✓${NC} .env already exists"
fi

# Make scripts executable
chmod +x workflows/lambda_cut.py 2>/dev/null || true

echo ""
echo -e "${GREEN}========================"
echo -e "${GREEN}Installation complete!${NC}"
echo -e "${GREEN}========================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: python3 workflows/lambda_cut.py onboard"
echo "  3. Start listener: python3 workflows/lambda_cut.py listen"
echo ""
echo "For help, see README.md"
