#!/bin/bash
# fix_imports.sh - Quick fix for import errors

echo "════════════════════════════════════════════════════════════════"
echo "🔧 Fixing Import Errors"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if we're in the right directory
if [ ! -f "requirements-test.txt" ]; then
    echo "❌ Error: requirements-test.txt not found"
    echo "   Run this script from the project root directory"
    exit 1
fi

# Install dependencies
echo "📦 Installing missing dependencies..."
echo ""

pip3 install sqlmodel bleach hydra-core --quiet

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Installation failed. Trying with full requirements..."
    pip3 install -r requirements-test.txt
    exit_code=$?
else
    echo "✅ Core dependencies installed"
    echo ""
    echo "📦 Installing test dependencies..."
    pip3 install pytest pytest-asyncio pytest-cov pytest-mock --quiet
    exit_code=$?
fi

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ All dependencies installed successfully!"
    echo ""
    echo "🧪 Verifying installation..."
    python3 check_deps.py

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Everything is ready!"
        echo ""
        echo "🚀 Next steps:"
        echo "   pytest --collect-only    # Verify test collection"
        echo "   pytest -v                # Run all tests"
        echo ""
    fi
else
    echo "❌ Installation failed"
    echo ""
    echo "Try manually:"
    echo "  pip3 install sqlmodel bleach hydra-core"
    echo "  pip3 install pytest pytest-asyncio pytest-cov"
    exit 1
fi

echo "════════════════════════════════════════════════════════════════"
