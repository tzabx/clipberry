#!/bin/bash

# Clipberry Installation Script for Linux

echo "================================"
echo "Clipberry Installer"
echo "================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    INSTALL_DIR="/usr/local/bin"
    DESKTOP_DIR="/usr/share/applications"
    ICON_DIR="/usr/share/icons/hicolor/256x256/apps"
else
    INSTALL_DIR="$HOME/.local/bin"
    DESKTOP_DIR="$HOME/.local/share/applications"
    ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
fi

echo "Installation directory: $INSTALL_DIR"
echo ""

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

# Copy executable
echo "Installing clipberry executable..."
cp dist/clipberry "$INSTALL_DIR/clipberry"
chmod +x "$INSTALL_DIR/clipberry"

# Create desktop entry
echo "Creating desktop entry..."
cat > "$DESKTOP_DIR/clipberry.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Clipberry
Comment=Cross-platform Clipboard Sync
Exec=$INSTALL_DIR/clipberry
Terminal=false
Categories=Utility;
EOF

chmod +x "$DESKTOP_DIR/clipberry.desktop"

echo ""
echo "================================"
echo "Installation complete!"
echo "================================"
echo ""
echo "You can now:"
echo "  1. Run 'clipberry' from terminal"
echo "  2. Find 'Clipberry' in your application menu"
echo ""
echo "For more information, see:"
echo "  - LEEME.md (Quick start in Spanish)"
echo "  - docs/SETUP.md (Detailed setup)"
echo "  - docs/ARCHITECTURE.md (Technical details)"
echo ""
