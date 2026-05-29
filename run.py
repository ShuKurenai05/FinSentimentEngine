"""
FinSentimentEngine — Entry Point
Usage:
    python run.py                    <- uses inputs/sample_news.txt
    python run.py --url <URL>        <- fetches from a URL
    python run.py --text "..."       <- pass inline text
"""

import sys
import os
from dotenv import load_dotenv
from colorama import init, Fore, Style

init()
load_dotenv()

# FIXED IMPORTS: Removed "core." prefix
from fetcher import fetch_from_file, fetch_from_url, fetch_from_string
from llm_client import analyze_news
from output_handler import save_output, print_summary


def main():
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  FinSentimentEngine — Multi-Source Financial News Analyzer{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    args = sys.argv[1:]
    
    try:
        if len(args) >= 2 and args[0] == "--url":
            raw_text = fetch_from_url(args[1])
        
        elif len(args) >= 2 and args[0] == "--text":
            raw_text = fetch_from_string(args[1])
        
        else:
            default_path = os.path.join("inputs", "sample_news.txt")
            raw_text = fetch_from_file(default_path)
    
    except (FileNotFoundError, ValueError, ConnectionError) as e:
        print(f"{Fore.RED}[ERROR] Input error: {e}{Style.RESET_ALL}")
        sys.exit(1)
    
    try:
        results = analyze_news(raw_text)
        save_output(results)
        print_summary(results)
    except Exception as e:
        print(f"{Fore.RED}[ERROR] Execution failed: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
