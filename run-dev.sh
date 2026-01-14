#!/bin/bash

# Clipberry Development Runner
# Run the application directly from source without installing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================"
echo "Clipberry Development Runner"
echo "================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    echo ""
    echo "Run first:"
    echo "  ./build.sh setup"
    echo ""
    exit 1
fi

# Activate venv
echo -e "${GREEN}✓${NC} Activating virtual environment..."
source venv/bin/activate

# Check if package is installed in development mode
if ! python -c "import clipberry" 2>/dev/null; then
    echo -e "${YELLOW}⚠${NC}  Package not installed in development mode. Installing..."
    pip install -e . > /dev/null
fi

echo -e "${GREEN}✓${NC} Environment ready"
echo ""

# Parse arguments
VERBOSE=""
DEBUG=""
CONFIG=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        -d|--debug)
            DEBUG="--debug"
            shift
            ;;
        -c|--config)
            CONFIG="--config $2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose    Enable verbose logging"
            echo "  -d, --debug      Enable debug mode"
            echo "  -c, --config     Specify custom config file"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Run normally"
            echo "  $0 --verbose          # Run with verbose output"
            echo "  $0 --debug            # Run in debug mode"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Display info
echo "Starting Clipberry..."
echo "Mode: Development"
if [ -n "$VERBOSE" ]; then
    echo "Verbose: Enabled"
fi
if [ -n "$DEBUG" ]; then
    echo "Debug: Enabled"
fi
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "================================"
echo ""

# Run the application
python -m clipberry.main $VERBOSE $DEBUG $CONFIG
