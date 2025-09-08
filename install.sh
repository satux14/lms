#!/bin/bash

# Lending Management System - Installation Script

echo "🏦 Lending Management System - Installation"
echo "=============================================="
echo

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.7 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed. Please install pip3."
    exit 1
fi

echo "✅ pip3 found: $(pip3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Create demo data
echo "🎭 Creating demo data..."
python3 demo.py

if [ $? -eq 0 ]; then
    echo "✅ Demo data created successfully"
else
    echo "❌ Failed to create demo data"
    exit 1
fi

echo
echo "🎉 Installation completed successfully!"
echo
echo "🚀 To start the application:"
echo "   1. Activate virtual environment: source venv/bin/activate"
echo "   2. Run the application: python3 run.py"
echo "   3. Open browser: http://localhost:8080"
echo
echo "🔑 Default login credentials:"
echo "   Admin: admin / admin123"
echo "   Customer: john_doe / password123"
echo
echo "📚 For more information, see README.md"
