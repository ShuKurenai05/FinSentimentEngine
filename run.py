"""
FinSentimentEngine — Entry Point
Run this file to analyze financial news.

Usage:
    python run.py                    <- uses inputs/sample_news.txt
    python run.py --url <URL>        <- fetches from a URL
    python run.py --text "..."       <- pass inline text

D:\FinSentimentEngine> python run.py
"""

import sys
import os
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Init colorama for Windows color support
init()

# Load API key from .env
load_dotenv()

from core.fetcher import fetch_from_file, fetch_from_url, fetch_from_string
from core.llm_client import analyze_news
from core.output_handler import save_output, print_summary


def main():
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  FinSentimentEngine — Multi-Source Financial News Analyzer{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    args = sys.argv[1:]
    
    # --- Input mode selection ---
    try:
        if len(args) >= 2 and args[0] == "--url":
            raw_text = fetch_from_url(args[1])
        
        elif len(args) >= 2 and args[0] == "--text":
            raw_text = fetch_from_string(args[1])
        
        else:
            # Default: read from inputs/sample_news.txt
            default_path = os.path.join("inputs", "sample_news.txt")
            raw_text = fetch_from_file(default_path)
    
    except (FileNotFoundError, ValueError, ConnectionError) as e:
        print(f"{Fore.RED}[ERROR] Input error: {e}{Style.RESET_ALL}")
        sys.exit(1)
    
    # --- LLM Analysis ---
    try:
        results = analyze_news(raw_text)
    except (EnvironmentError, RuntimeError, ValueError) as e:
        print(f"{Fore.RED}[ERROR] Analysis failed: {e}{Style.RESET_ALL}")
        sys.exit(1)
    
    # --- Output ---
    print_summary(results)
    saved_path = save_output(results)
    
    print(f"{Fore.GREEN}Done! Full JSON saved to: {saved_path}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()