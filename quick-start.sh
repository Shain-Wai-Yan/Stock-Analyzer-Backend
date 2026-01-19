#!/bin/bash
set -e

echo "==============================================="
echo "  Gap Scanner Backend - Quick Start"
echo "==============================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "🔧 Please edit .env and add your API keys:"
    echo "   - ALPACA_API_KEY"
    echo "   - ALPACA_SECRET_KEY"
    echo "   - GROQ_API_KEY (optional)"
    echo ""
    read -p "Press Enter after you've configured your .env file..."
fi

# Check Python version
echo "🐍 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2 | cut -d '.' -f 1,2)
echo "✅ Python $PYTHON_VERSION found"
echo ""

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""

# Initialize database
echo "🗄️  Initializing database..."
python -c "import asyncio; from database import init_db; asyncio.run(init_db())"
echo "✅ Database initialized"
echo ""

echo "==============================================="
echo "  🚀 Ready to launch!"
echo "==============================================="
echo ""
echo "To start the backend:"
echo "  ./start.sh"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  uvicorn main:app --reload"
echo ""
echo "API will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
