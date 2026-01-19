#!/bin/bash
# Test script to verify all imports work before deploying

echo "Testing Python environment..."
python --version

echo "Testing imports..."
python -c "
import sys
try:
    print('Testing fastapi...', end=' ')
    import fastapi
    print('✓')
    
    print('Testing uvicorn...', end=' ')
    import uvicorn
    print('✓')
    
    print('Testing lumibot...', end=' ')
    import lumibot
    print('✓')
    
    print('Testing alpaca...', end=' ')
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.trading.client import TradingClient
    print('✓')
    
    print('Testing sqlalchemy...', end=' ')
    import sqlalchemy
    print('✓')
    
    print('Testing pandas...', end=' ')
    import pandas
    print('✓')
    
    print('Testing groq...', end=' ')
    import groq
    print('✓')
    
    print('Testing httpx...', end=' ')
    import httpx
    print('✓')
    
    print('')
    print('All imports successful! ✓')
    sys.exit(0)
except ImportError as e:
    print(f'✗ Failed: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "Build test PASSED. Ready to deploy!"
    exit 0
else
    echo ""
    echo "Build test FAILED. Check dependencies."
    exit 1
fi
