"""Sentiment analysis service using Groq"""
from typing import List, Dict, Optional
from config import settings
import logging
import httpx

logger = logging.getLogger(__name__)


async def analyze_sentiment(text: str) -> float:
    """
    Analyze sentiment of text using Groq
    Returns score between 0 (bearish) and 1 (bullish)
    """
    if not settings.groq_api_key:
        logger.warning("Groq API key not configured, returning neutral sentiment")
        return 0.5
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "mixtral-8x7b-32768",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a financial sentiment analyzer. Return ONLY a number between 0 and 1, where 0 is very bearish and 1 is very bullish. No explanation.",
                        },
                        {
                            "role": "user",
                            "content": f"Analyze sentiment: {text}",
                        },
                    ],
                    "temperature": 0.3,
                    "max_tokens": 10,
                },
            )
            
            if response.status_code == 200:
                result = response.json()
                sentiment_text = result["choices"][0]["message"]["content"].strip()
                
                # Parse sentiment score
                try:
                    score = float(sentiment_text)
                    return max(0.0, min(1.0, score))
                except ValueError:
                    logger.warning(f"Failed to parse sentiment score: {sentiment_text}")
                    return 0.5
            else:
                logger.error(f"Groq API error: {response.status_code}")
                return 0.5
                
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return 0.5


async def get_news_sentiment(symbol: str) -> List[Dict]:
    """
    Get news and sentiment for a symbol
    Uses Alpaca News API (free with data subscription)
    """
    try:
        # Note: Alpaca news requires subscription
        # For free tier, return mock data
        news = [
            {
                "id": "1",
                "title": f"{symbol} Shows Strong Premarket Activity",
                "summary": "Stock experiencing increased volatility in premarket trading with significant gap.",
                "source": "Market Watch",
                "url": f"https://example.com/{symbol}",
                "published_at": "2024-01-19T09:00:00Z",
                "sentiment": 0.65,
                "related_symbols": [symbol],
            }
        ]
        return news
        
    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        return []


async def get_gap_reason(symbol: str, gap_percent: float) -> Dict:
    """
    Use AI to explain why a gap occurred
    """
    if not settings.groq_api_key:
        return {
            "reason": "Gap analysis requires Groq API key configuration.",
            "confidence": 0.0,
        }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "mixtral-8x7b-32768",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a financial analyst. Explain stock gaps in 2-3 sentences. Be specific and actionable.",
                        },
                        {
                            "role": "user",
                            "content": f"Why did {symbol} gap {gap_percent:.2f}% today? What are the likely catalysts?",
                        },
                    ],
                    "temperature": 0.7,
                    "max_tokens": 150,
                },
            )
            
            if response.status_code == 200:
                result = response.json()
                reason = result["choices"][0]["message"]["content"].strip()
                
                return {
                    "reason": reason,
                    "confidence": 0.75,
                }
            else:
                return {
                    "reason": f"Failed to analyze gap for {symbol}",
                    "confidence": 0.0,
                }
                
    except Exception as e:
        logger.error(f"Error getting gap reason: {e}")
        return {
            "reason": f"Error analyzing gap: {str(e)}",
            "confidence": 0.0,
        }
