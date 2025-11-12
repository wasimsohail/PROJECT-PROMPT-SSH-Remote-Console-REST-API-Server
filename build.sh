#!/bin/bash
# Build script for SSH Console API Server

echo "SSH Console API Server - Build Script"
echo "======================================"
echo ""

# Check if PyInstaller is installed
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/ dist/

# Build the executable
echo "Building executable..."
pyinstaller build.spec

# Check if build was successful
if [ -f "dist/ssh-console-api" ] || [ -f "dist/ssh-console-api.exe" ]; then
    echo ""
    echo "✓ Build successful!"
    echo ""
    echo "Executable location:"
    if [ -f "dist/ssh-console-api.exe" ]; then
        echo "  - dist/ssh-console-api.exe"
    else
        echo "  - dist/ssh-console-api"
    fi
    echo ""
    echo "To deploy:"
    echo "1. Copy the executable to your target system"
    echo "2. Create a config.ini file in the same directory"
    echo "3. Run the executable"
    echo ""
else
    echo ""
    echo "✗ Build failed. Check the output above for errors."
    exit 1
fi
