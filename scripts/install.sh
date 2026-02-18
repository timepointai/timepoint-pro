#!/bin/bash

# Installation script for timepoint-pro
# Handles grpcio build issues on macOS

echo "🚀 Installing timepoint-pro dependencies..."

# Check if Poetry is installed
if command -v poetry &> /dev/null; then
    echo "✓ Poetry found"
    
    # Clean cache and lock file
    echo "🧹 Cleaning Poetry cache..."
    poetry cache clear pypi --all -n 2>/dev/null || true
    rm -f poetry.lock
    
    # Set environment variables for macOS compatibility
    export GRPC_PYTHON_BUILD_SYSTEM_OPENSSL=1
    export GRPC_PYTHON_BUILD_SYSTEM_ZLIB=1
    
    echo "📦 Installing dependencies with Poetry..."
    poetry install
    
    if [ $? -eq 0 ]; then
        echo "✅ Installation successful!"
        echo ""
        echo "To activate the environment:"
        echo "  poetry shell"
        echo ""
        echo "To run the CLI:"
        echo "  poetry run python cli.py mode=autopilot"
    else
        echo "❌ Poetry installation failed. Trying alternative method..."
        echo "Installing grpcio separately..."
        poetry run pip install --upgrade grpcio
        poetry install
    fi
else
    echo "⚠️  Poetry not found. Using pip..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install grpcio first with pre-built wheels
    echo "📦 Installing grpcio (this may take a moment)..."
    pip install --upgrade grpcio
    
    # Install other dependencies
    echo "📦 Installing other dependencies..."
    pip install -r requirements.txt
    
    if [ $? -eq 0 ]; then
        echo "✅ Installation successful!"
        echo ""
        echo "To activate the environment:"
        echo "  source venv/bin/activate"
        echo ""
        echo "To run the CLI:"
        echo "  python cli.py mode=autopilot"
    else
        echo "❌ Installation failed. Please check the error messages above."
        exit 1
    fi
fi
