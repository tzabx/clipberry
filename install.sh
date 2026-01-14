#!/bin/bash

# Clibpard Installation Script for Linux

echo "================================"
echo "Clibpard Installer"
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
echo "Installing clibpard executable..."
cp dist/clibpard "$INSTALL_DIR/clibpard"
chmod +x "$INSTALL_DIR/clibpard"

# Create desktop entry
echo "Creating desktop entry..."
cat > "$DESKTOP_DIR/clibpard.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Clibpard
Comment=Cross-platform Clipboard Sync
Exec=$INSTALL_DIR/clibpard
Terminal=false
Categories=Utility;
EOF

chmod +x "$DESKTOP_DIR/clibpard.desktop"

echo ""
echo "================================"
echo "Installation complete!"
echo "================================"
echo ""
echo "You can now:"
echo "  1. Run 'clibpard' from terminal"
echo "  2. Find 'Clibpard' in your application menu"
echo ""
echo "For more information, see:"
echo "  - LEEME.md (Quick start in Spanish)"
echo "  - docs/SETUP.md (Detailed setup)"
echo "  - docs/ARCHITECTURE.md (Technical details)"
echo ""
