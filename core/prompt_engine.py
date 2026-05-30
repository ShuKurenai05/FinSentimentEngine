"""
Prompt templates for the Financial Sentiment Engine.
"""

SYSTEM_PROMPT = """You are an expert financial analyst and NLP engine.
Your job is to analyze financial news text and extract structured intelligence.
You always respond with valid JSON only — no markdown, no explanation, no extra text.
Never wrap your response in code blocks. Output raw JSON only."""


def build_analysis_prompt(news_text: str) -> str:
    return f"""Analyze the following financial news text. For the ENTIRE batch, provide:

1. A list of individual article analyses
2. An overall portfolio-level sentiment summary

For each article, extract:
- headline_summary: One sentence summary (max 20 words)
- entities: List of companies, people, or assets mentioned
- sentiment: Must be exactly one of: "Bullish", "Bearish", or "Neutral"
- sentiment_score: Float from -1.0 (most bearish) to +1.0 (most bullish)
- confidence: Float from 0.0 to 1.0 indicating your confidence
- key_drivers: List of 2-3 specific reasons for the sentiment
- sector: The financial sector (e.g. Tech, Energy, Macro, Crypto, Finance)
- risk_flags: Any red flags or warnings (empty list if none)

Return this exact JSON structure:
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

NEWS TEXT TO ANALYZE:
---
{news_text}
---"""
