#!/usr/bin/env python3
"""Simple health check script for Docker/Northflank"""
import sys
try:
    import httpx
    response = httpx.get("http://localhost:8000/health", timeout=5.0)
    if response.status_code == 200:
        sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
