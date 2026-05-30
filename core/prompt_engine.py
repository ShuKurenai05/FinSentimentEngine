"""
Prompt templates for the Financial Sentiment Engine.
"""

SYSTEM_PROMPT = """You are an expert financial analyst and NLP engine.
Your ONLY job is to analyze financial news text and return a JSON object.

CRITICAL RULES — you must follow all of these without exception:
1. Return ONLY a valid JSON object. Nothing else.
2. Do NOT write any explanation, introduction, or commentary.
3. Do NOT use markdown. Do NOT use code blocks. Do NOT use backticks.
4. Your entire response must start with { and end with }
5. If the input text is messy or hard to read, do your best with what is available.
6. Never say you cannot process the input — always return the JSON structure.
7. For any field you cannot determine, use a sensible default:
   - sentiment: "Neutral"
   - sentiment_score: 0.0
   - confidence: 0.5
   - entities: []
   - key_drivers: ["Insufficient data"]
   - risk_flags: []"""


def build_analysis_prompt(news_text: str) -> str:
    return f"""Analyze the financial news text below and return ONLY a JSON object.
Start your response with {{ and end with }}. No other text.

Extract for each article:
- headline_summary: One sentence summary (max 20 words)
- entities: Companies, people, or assets mentioned
- sentiment: Exactly one of "Bullish", "Bearish", or "Neutral"
- sentiment_score: Float from -1.0 (bearish) to +1.0 (bullish)
- confidence: Float from 0.0 to 1.0
- key_drivers: 2-3 specific reasons for the sentiment
- sector: Financial sector (Tech, Energy, Macro, Crypto, Finance, etc.)
- risk_flags: Red flags or warnings (empty list if none)

Return exactly this JSON structure and nothing else:
{{
  "analysis_metadata": {{
    "total_articles": <int>,
    "processing_timestamp": "",
    "model_used": "llama-3.3-70b-versatile"
  }},
  "articles": [
    {{
      "article_id": 1,
      "headline_summary": "<string>",
      "entities": ["<string>"],
      "sentiment": "<Bullish|Bearish|Neutral>",
      "sentiment_score": <float>,
      "confidence": <float>,
      "key_drivers": ["<string>"],
      "sector": "<string>",
      "risk_flags": ["<string>"]
    }}
  ],
  "portfolio_summary": {{
    "overall_sentiment": "<Bullish|Bearish|Neutral>",
    "average_sentiment_score": <float>,
    "bullish_count": <int>,
    "bearish_count": <int>,
    "neutral_count": <int>,
    "top_entities": ["<string>"],
    "market_outlook": "<2-3 sentence overall market outlook>"
  }}
}}

NEWS TEXT:
---
{news_text}
---

Remember: respond with ONLY the JSON object. Start with {{ and end with }}."""
