#!/bin/bash
# Error Collector MCP - Quick Setup Script (Shell Wrapper)
# This script provides a simple way to run the Python setup script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║           🚀 Error Collector MCP - Quick Setup              ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is required but not installed.${NC}"
    echo -e "${YELLOW}Please install Python 3.9+ and try again.${NC}"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}❌ Python $PYTHON_VERSION found, but Python $REQUIRED_VERSION+ is required.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"

# Run the Python setup script
echo -e "${BLUE}🚀 Running interactive setup...${NC}"

# Check if package is installed
if python3 -c "import error_collector_mcp" 2>/dev/null; then
    echo -e "${GREEN}✅ Package already installed, running configuration setup...${NC}"
    python3 quick_setup.py
else
    echo -e "${YELLOW}📦 Package not installed, running full setup...${NC}"
    python3 setup.py
fi

echo -e "${GREEN}🎉 Setup complete!${NC}"