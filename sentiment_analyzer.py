"""
Sentiment Analysis using Groq (FREE)
Uses Llama 3 for financial sentiment
"""
import os
from groq import Groq
from typing import Dict

class SentimentAnalyzer:
    def __init__(self):
        # Get Groq API key (FREE tier)
        api_key = os.getenv('GROQ_API_KEY', 'YOUR_GROQ_API_KEY')
        self.client = Groq(api_key=api_key) if api_key != 'YOUR_GROQ_API_KEY' else None
    
    async def analyze_symbol(self, symbol: str) -> Dict:
        """
        Analyze overall sentiment for a symbol
        Returns score from -1 (very negative) to 1 (very positive)
        """
        if not self.client:
            # Return neutral if Groq not configured
            return {"score": 0.0, "label": "neutral"}
        
        try:
            # Use Groq's Llama model for sentiment
            prompt = f"""Analyze the sentiment for stock {symbol} based on recent market conditions and news.
            Return ONLY a JSON object with: {{"score": <number between -1 and 1>, "label": "<positive/negative/neutral>"}}
            
            Consider:
            - Recent price action
            - Market sentiment
            - Sector trends
            
            Response (JSON only):"""
            
            completion = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Free tier model
                messages=[
                    {"role": "system", "content": "You are a financial sentiment analyzer. Respond with only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            response = completion.choices[0].message.content
            
            # Parse response
            import json
            result = json.loads(response)
            
            return {
                "score": float(result.get('score', 0)),
                "label": result.get('label', 'neutral')
            }
            
        except Exception as e:
            print(f"Sentiment analysis error: {e}")
            return {"score": 0.0, "label": "neutral"}
    
    async def analyze_text(self, text: str) -> Dict:
        """
        Analyze sentiment of news headline/text
        """
        if not self.client or not text:
            return {"score": 0.0, "label": "neutral"}
        
        try:
            prompt = f"""Analyze the sentiment of this financial news:
            "{text}"
            
            Return ONLY a JSON object: {{"score": <number between -1 and 1>, "label": "<positive/negative/neutral>"}}"""
            
            completion = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a financial sentiment analyzer. Respond with only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            response = completion.choices[0].message.content
            
            import json
            result = json.loads(response)
            
            return {
                "score": float(result.get('score', 0)),
                "label": result.get('label', 'neutral')
            }
            
        except Exception as e:
            print(f"Text sentiment error: {e}")
            return {"score": 0.0, "label": "neutral"}
