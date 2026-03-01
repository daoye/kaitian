#!/bin/bash
# Development environment setup script

set -e

echo "=== KaiTian Project Setup ==="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
	echo "Creating virtual environment..."
	python -m venv venv
	echo "Virtual environment created"
else
	echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -e ".[dev]"

# Create .env file if not exists
if [ ! -f ".env" ]; then
	echo "Creating .env file from .env.example..."
	cp .env.example .env
	echo "Please fill in your credentials in .env file"
else
	echo ".env file already exists"
fi

echo ""
echo "=== Setup Complete ==="
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To run the application, use:"
echo "  python main.py"
echo ""
echo "To run tests, use:"
echo "  pytest"
