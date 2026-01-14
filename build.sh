#!/bin/bash
# Build script for Clipberry

set -e

echo "================================"
echo "Clipberry Build Script"
echo "================================"

# Detect platform
PLATFORM=$(uname -s)
echo "Platform: $PLATFORM"

# Create build directory
BUILD_DIR="build"
DIST_DIR="dist"
mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Function to setup Python environment
setup_python() {
    echo ""
    echo "Setting up Python environment..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        echo "ERROR: Python 3 not found"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "Python version: $PYTHON_VERSION"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    # Install development dependencies
    pip install pytest pytest-asyncio black flake8 mypy pyinstaller
}

# Function to run tests
run_tests() {
    echo ""
    echo "Running tests..."
    
    if [ -d "tests" ]; then
        pytest tests/ -v
    else
        echo "No tests directory found, skipping tests"
    fi
}

# Function to format code
format_code() {
    echo ""
    echo "Formatting code with black..."
    black src/
}

# Function to check code quality
check_code() {
    echo ""
    echo "Checking code with flake8..."
    flake8 src/ --max-line-length=120 --ignore=E203,W503 || true
    
    echo ""
    echo "Type checking with mypy..."
    mypy src/clipberry/ --ignore-missing-imports || true
}

# Function to build standalone executable
build_executable() {
    echo ""
    echo "Building standalone executable..."
    
    # Determine platform-specific options
    if [ "$PLATFORM" = "Darwin" ]; then
        # macOS
        pyinstaller \
            --onefile \
            --windowed \
            --noconfirm \
            --name clipberry \
            --add-data "src/clipberry:clipberry" \
            src/clipberry/main.py
    else
        # Linux
        pyinstaller \
            --onefile \
            --windowed \
            --noconfirm \
            --name clipberry \
            --add-data "src/clipberry:clipberry" \
            src/clipberry/main.py
    fi
    
    echo "Executable created in dist/"
}

# Function to create source distribution
create_source_dist() {
    echo ""
    echo "Creating source distribution..."
    
    python setup.py sdist
    
    echo "Source distribution created in dist/"
}

# Function to create platform package
create_package() {
    echo ""
    echo "Creating platform package..."
    
    if [ "$PLATFORM" = "Darwin" ]; then
        # macOS - create .app bundle
        echo "Creating .app bundle..."
        pip install py2app
        python setup.py py2app
        
        # Create DMG (requires create-dmg tool)
        if command -v create-dmg &> /dev/null; then
            create-dmg \
                --volname "Clipberry" \
                --window-pos 200 120 \
                --window-size 800 400 \
                --icon-size 100 \
                --app-drop-link 600 185 \
                "$DIST_DIR/Clipberry.dmg" \
                "dist/Clipberry.app"
        fi
    else
        # Linux - create AppImage or deb package
        echo "Creating Linux package..."
        
        # For now, just create a tarball
        cd dist
        tar czf clipberry-linux-x86_64.tar.gz clipberry
        cd ..
    fi
}

# Function to clean build artifacts
clean() {
    echo ""
    echo "Cleaning build artifacts..."
    
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info/
    rm -rf src/*.egg-info/
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type f -name "*.spec" -delete
    
    echo "Clean complete"
}

# Parse command line arguments
case "${1:-all}" in
    clean)
        clean
        ;;
    setup)
        setup_python
        ;;
    test)
        setup_python
        run_tests
        ;;
    format)
        setup_python
        format_code
        ;;
    check)
        setup_python
        check_code
        ;;
    build)
        setup_python
        run_tests
        check_code
        build_executable
        ;;
    package)
        setup_python
        run_tests
        build_executable
        create_package
        ;;
    dist)
        setup_python
        create_source_dist
        ;;
    all)
        setup_python
        format_code
        check_code
        run_tests
        build_executable
        ;;
    *)
        echo "Usage: $0 {clean|setup|test|format|check|build|package|dist|all}"
        echo ""
        echo "Commands:"
        echo "  clean   - Remove build artifacts"
        echo "  setup   - Setup Python environment"
        echo "  test    - Run tests"
        echo "  format  - Format code with black"
        echo "  check   - Check code quality"
        echo "  build   - Build standalone executable"
        echo "  package - Create platform-specific package"
        echo "  dist    - Create source distribution"
        echo "  all     - Run everything (default)"
        exit 1
        ;;
esac

echo ""
echo "================================"
echo "Build complete!"
echo "================================"
