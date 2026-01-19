#!/bin/bash
set -e

echo "Starting Gap Scanner API..."

# Check required environment variables
if [ -z "$ALPACA_API_KEY" ]; then
    echo "ERROR: ALPACA_API_KEY environment variable is required"
    exit 1
fi

if [ -z "$ALPACA_SECRET_KEY" ]; then
    echo "ERROR: ALPACA_SECRET_KEY environment variable is required"
    exit 1
fi

# Initialize database
echo "Initializing database..."
python -c "import asyncio; from database import init_db; asyncio.run(init_db())"

# Start server
echo "Starting API server on port ${PORT:-8000}..."
exec uvicorn main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-1}" \
    --log-level "${LOG_LEVEL:-info}"
