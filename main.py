"""
Free Stock Gap Analysis Backend
Uses: Alpaca (free), VectorBT (backtest), Groq (sentiment)
Deploy: Northflank/Fly.io free tier
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import List, Optional
import os

# Import our modules
from gap_analyzer import GapAnalyzer
from sentiment_analyzer import SentimentAnalyzer
from alpaca_client import AlpacaClient

app = FastAPI(title="Gap Analysis API", version="1.0.0")

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
print("[STARTUP] Initializing services...")
alpaca_client = AlpacaClient()
gap_analyzer = GapAnalyzer(alpaca_client)
sentiment_analyzer = SentimentAnalyzer()

# Check API keys on startup
alpaca_key = os.getenv('ALPACA_API_KEY', 'not_set')
groq_key = os.getenv('GROQ_API_KEY', 'not_set')
print(f"[STARTUP] Alpaca API Key: {'✓ Set' if alpaca_key != 'not_set' and alpaca_key != 'YOUR_ALPACA_KEY' else '✗ Missing'}")
print(f"[STARTUP] Groq API Key: {'✓ Set' if groq_key != 'not_set' and groq_key != 'YOUR_GROQ_KEY' else '✗ Missing'}")
print("[STARTUP] Services initialized successfully")

@app.get("/")
async def root():
    """Health check"""
    alpaca_configured = os.getenv('ALPACA_API_KEY', 'not_set') not in ['not_set', 'YOUR_ALPACA_KEY']
    groq_configured = os.getenv('GROQ_API_KEY', 'not_set') not in ['not_set', 'YOUR_GROQ_KEY']
    
    return {
        "status": "running",
        "service": "Gap Analysis API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "config": {
            "alpaca": "configured" if alpaca_configured else "missing",
            "groq": "configured" if groq_configured else "missing"
        }
    }

@app.get("/api/gaps")
async def get_gaps(
    min_gap: float = Query(1.0, description="Minimum gap percentage"),
    max_gap: float = Query(10.0, description="Maximum gap percentage"),
    limit: int = Query(50, description="Number of results")
):
    """
    Get current market gaps with probability analysis
    Returns stocks gapping up/down with fill probability
    """
    try:
        print(f"[API] Fetching gaps: min={min_gap}, max={max_gap}, limit={limit}")
        
        # Get market movers from Alpaca
        gaps = await gap_analyzer.scan_gaps(min_gap, max_gap, limit)
        
        print(f"[API] Found {len(gaps)} gaps from scanner")
        
        # If no gaps found, return empty array (not an error)
        if not gaps:
            print("[API] No gaps detected, returning empty array")
            return {
                "success": True,
                "data": [],
                "timestamp": datetime.utcnow().isoformat(),
                "count": 0,
                "message": "No gaps detected in current market conditions"
            }
        
        # Calculate fill probability for each
        enriched_gaps = []
        for gap in gaps:
            try:
                # Get historical data and calculate probability
                prob_data = await gap_analyzer.calculate_fill_probability(
                    gap['symbol'], 
                    lookback_days=100
                )
                
                # Get sentiment score
                sentiment = await sentiment_analyzer.analyze_symbol(gap['symbol'])
                
                enriched_gaps.append({
                    **gap,
                    "fillProbability": prob_data['fill_rate'],
                    "avgFillTime": prob_data['avg_fill_time'],
                    "historicalGaps": prob_data['total_gaps'],
                    "conviction": calculate_conviction(gap, prob_data, sentiment),
                    "sentiment": sentiment['score'],
                    "sentimentLabel": sentiment['label'],
                    "reasons": generate_reasons(gap, prob_data, sentiment)
                })
            except Exception as e:
                print(f"[API] Error enriching gap for {gap['symbol']}: {e}")
                # Add gap without enrichment
                enriched_gaps.append({
                    **gap,
                    "fillProbability": 0.5,
                    "avgFillTime": 0,
                    "historicalGaps": 0,
                    "conviction": "LOW",
                    "sentiment": 0,
                    "sentimentLabel": "neutral",
                    "reasons": ["Gap detected"]
                })
        
        print(f"[API] Returning {len(enriched_gaps)} enriched gaps")
        
        return {
            "success": True,
            "data": enriched_gaps,
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(enriched_gaps)
        }
        
    except Exception as e:
        print(f"[API] Error in get_gaps: {e}")
        # Return empty array instead of error
        return {
            "success": True,
            "data": [],
            "timestamp": datetime.utcnow().isoformat(),
            "count": 0,
            "error": str(e)
        }

@app.get("/api/gaps/{symbol}")
async def get_gap_details(symbol: str):
    """Get detailed gap analysis for a specific symbol"""
    try:
        # Get current gap data
        current_data = await alpaca_client.get_latest_quote(symbol)
        
        # Calculate fill probability with more detail
        prob_data = await gap_analyzer.calculate_fill_probability(
            symbol, 
            lookback_days=252  # 1 year
        )
        
        # Get sentiment
        sentiment = await sentiment_analyzer.analyze_symbol(symbol)
        
        # Run backtest
        backtest = await gap_analyzer.run_backtest(symbol, days=365)
        
        return {
            "success": True,
            "data": {
                "symbol": symbol,
                "current": current_data,
                "probability": prob_data,
                "sentiment": sentiment,
                "backtest": backtest,
                "recommendation": generate_recommendation(prob_data, sentiment, backtest)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

@app.get("/api/news")
async def get_news_all(limit: int = 10):
    """Get general market news"""
    try:
        # Return mock news for now
        news_items = [
            {
                "id": "1",
                "headline": "Markets Show Volatility in Pre-Market Trading",
                "summary": "Several stocks showing significant gaps before market open",
                "url": "#",
                "source": "Market News",
                "created_at": datetime.utcnow().isoformat(),
                "sentiment": 0.2,
                "sentiment_label": "Neutral"
            }
        ]
        
        return {
            "success": True,
            "data": news_items,
            "count": len(news_items)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/news/{symbol}")
async def get_news(symbol: str, limit: int = 10):
    """Get news for a symbol with sentiment analysis"""
    try:
        news_items = await alpaca_client.get_news(symbol, limit)
        
        # If no news from API, return empty array
        if not news_items:
            news_items = []
        
        # Analyze sentiment for each news item
        for item in news_items:
            sentiment = await sentiment_analyzer.analyze_text(
                item.get('headline', '') + ' ' + item.get('summary', '')
            )
            item['sentiment'] = sentiment['score']
            item['sentiment_label'] = sentiment['label']
        
        return {
            "success": True,
            "data": news_items,
            "count": len(news_items)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trades")
async def get_trades():
    """Get saved trades from journal"""
    try:
        # Return empty array - frontend will handle
        return {
            "success": True,
            "data": [],
            "count": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backtest/{symbol}")
async def run_backtest(
    symbol: str,
    days: int = Query(365, description="Days to backtest")
):
    """Run VectorBT backtest for gap fill strategy"""
    try:
        result = await gap_analyzer.run_backtest(symbol, days)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Helper functions
def calculate_conviction(gap_data: dict, prob_data: dict, sentiment: dict) -> str:
    """Calculate conviction level: HIGH, MEDIUM, LOW"""
    score = 0
    
    # Gap size (2-8% is ideal)
    gap_pct = abs(gap_data.get('gapPercent', 0))
    if 2 <= gap_pct <= 8:
        score += 3
    elif gap_pct < 2 or gap_pct > 15:
        score -= 1
    
    # Fill probability
    fill_rate = prob_data.get('fill_rate', 0)
    if fill_rate >= 0.75:
        score += 3
    elif fill_rate >= 0.60:
        score += 2
    elif fill_rate < 0.50:
        score -= 2
    
    # Volume
    volume_ratio = gap_data.get('volumeRatio', 1)
    if volume_ratio >= 2:
        score += 2
    
    # Sentiment
    sentiment_score = sentiment.get('score', 0)
    if abs(sentiment_score) > 0.5:
        score += 1
    
    if score >= 6:
        return "HIGH"
    elif score >= 3:
        return "MEDIUM"
    else:
        return "LOW"

def generate_reasons(gap_data: dict, prob_data: dict, sentiment: dict) -> List[str]:
    """Generate human-readable reasons for the gap"""
    reasons = []
    
    gap_pct = gap_data.get('gapPercent', 0)
    if abs(gap_pct) > 5:
        reasons.append(f"Large {abs(gap_pct):.1f}% gap")
    
    if prob_data.get('fill_rate', 0) >= 0.70:
        reasons.append(f"High fill rate ({prob_data['fill_rate']*100:.0f}%)")
    
    if gap_data.get('volumeRatio', 1) >= 2:
        reasons.append(f"Volume spike ({gap_data['volumeRatio']:.1f}x)")
    
    if sentiment.get('score', 0) > 0.3:
        reasons.append("Positive sentiment")
    elif sentiment.get('score', 0) < -0.3:
        reasons.append("Negative sentiment")
    
    return reasons

def generate_recommendation(prob_data: dict, sentiment: dict, backtest: dict) -> dict:
    """Generate trading recommendation"""
    fill_rate = prob_data.get('fill_rate', 0)
    win_rate = backtest.get('win_rate', 0)
    
    if fill_rate >= 0.75 and win_rate >= 0.70:
        action = "STRONG BUY"
        confidence = "HIGH"
    elif fill_rate >= 0.60 and win_rate >= 0.60:
        action = "BUY"
        confidence = "MEDIUM"
    else:
        action = "WAIT"
        confidence = "LOW"
    
    return {
        "action": action,
        "confidence": confidence,
        "expected_win_rate": win_rate,
        "fill_probability": fill_rate
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
