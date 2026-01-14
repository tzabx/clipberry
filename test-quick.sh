#!/bin/bash

# Quick test script for Clipberry

echo "================================"
echo "Clipberry Quick Test"
echo "================================"
echo ""

# Check if built
if [ ! -f "dist/clipberry" ]; then
    echo "❌ Executable not found. Building..."
    ./build.sh build
    if [ $? -ne 0 ]; then
        echo "❌ Build failed!"
        exit 1
    fi
fi

echo "✅ Executable found: dist/clipberry"
echo ""

# Run tests
echo "Running unit tests..."
source venv/bin/activate
pytest tests/ -v --tb=short

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "To run the application:"
    echo "  ./dist/clipberry"
    echo ""
    echo "Or install it:"
    echo "  ./install.sh"
    echo ""
else
    echo ""
    echo "❌ Some tests failed!"
    exit 1
fi
