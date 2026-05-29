"""
Output handler — saves results to JSON files and prints a summary to terminal.
"""

import os
import json
from datetime import datetime
from colorama import Fore, Style


def save_output(data: dict, output_dir: str = "outputs") -> str:
    """Save the analysis dict to a timestamped JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sentiment_analysis_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"{Fore.GREEN}[OUTPUT] Saved to: {filepath}{Style.RESET_ALL}")
    return filepath


def print_summary(data: dict):
    """Print a clean terminal summary of the analysis."""
    print("\n" + "="*60)
    print(f"{Fore.CYAN}  FINANCIAL SENTIMENT ANALYSIS — RESULTS{Style.RESET_ALL}")
    print("="*60)
    
    meta = data.get("analysis_metadata", {})
    print(f"  Articles analyzed : {meta.get('total_articles', 'N/A')}")
    print(f"  Model used        : {meta.get('model_used', 'N/A')}")
    print(f"  Timestamp         : {meta.get('processing_timestamp', 'N/A')}")
    print("-"*60)
    
    articles = data.get("articles", [])
    sentiment_colors = {
        "Bullish": Fore.GREEN,
        "Bearish": Fore.RED,
        "Neutral": Fore.YELLOW
    }
    
    for article in articles:
        sentiment = article.get("sentiment", "N/A")
        color = sentiment_colors.get(sentiment, Fore.WHITE)
        score = article.get("sentiment_score", 0)
        
        print(f"\n  [{article.get('article_id', '?')}] {article.get('headline_summary', '')}")
        print(f"      Sentiment : {color}{sentiment} (score: {score:+.2f}){Style.RESET_ALL}")
        print(f"      Sector    : {article.get('sector', 'N/A')}")
        print(f"      Entities  : {', '.join(article.get('entities', []))}")
        print(f"      Drivers   : {' | '.join(article.get('key_drivers', []))}")
        
        flags = article.get("risk_flags", [])
        if flags:
            print(f"      {Fore.RED}Risk Flags: {', '.join(flags)}{Style.RESET_ALL}")
    
    print("\n" + "-"*60)
    summary = data.get("portfolio_summary", {})
    overall = summary.get("overall_sentiment", "N/A")
    color = sentiment_colors.get(overall, Fore.WHITE)
    
    print(f"  OVERALL MARKET SENTIMENT: {color}{overall}{Style.RESET_ALL}")
    print(f"  Avg Score : {summary.get('average_sentiment_score', 0):+.2f}")
    print(f"  Bullish: {summary.get('bullish_count',0)}  "
          f"Bearish: {summary.get('bearish_count',0)}  "
          f"Neutral: {summary.get('neutral_count',0)}")
    print(f"\n  Outlook: {summary.get('market_outlook', '')}")
    print("="*60 + "\n")