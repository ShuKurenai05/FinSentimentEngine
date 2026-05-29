"""
Fetcher — handles URL scraping, raw text, and file input.
"""

import os
import requests
from colorama import Fore, Style

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


def fetch_from_file(filepath: str) -> str:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        raise ValueError(f"File is empty: {filepath}")
    print(f"{Fore.CYAN}[FETCHER] Loaded from file: {filepath}{Style.RESET_ALL}")
    return content


def fetch_from_url(url: str) -> str:
    """Fetch and extract readable article text from a news URL."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 6.1; WOW64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/109.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        if BS4_AVAILABLE:
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove nav, ads, scripts, footers
            for tag in soup(["script", "style", "nav", "footer",
                              "header", "aside", "form", "noscript"]):
                tag.decompose()

            # Try to find the article body
            article = (
                soup.find("article") or
                soup.find("main") or
                soup.find(class_=lambda c: c and any(
                    x in c.lower() for x in ["article", "content", "story", "post-body"]
                ))
            )

            target = article if article else soup.find("body")
            if target:
                paragraphs = target.find_all("p")
                text = " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
            else:
                text = soup.get_text(separator=" ", strip=True)

            # Clean up whitespace
            import re
            text = re.sub(r'\s+', ' ', text).strip()
        else:
            text = response.text.strip()

        if len(text) < 100:
            raise ValueError(f"Could not extract meaningful text from: {url}")

        print(f"{Fore.CYAN}[FETCHER] Scraped URL: {url} ({len(text)} chars){Style.RESET_ALL}")
        return text[:6000]  # Cap to avoid token overflow

    except requests.Timeout:
        raise ConnectionError(f"Timed out fetching: {url}")
    except requests.RequestException as e:
        raise ConnectionError(f"Failed to fetch {url}: {e}")


def fetch_from_string(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("Input text is empty.")
    print(f"{Fore.CYAN}[FETCHER] Using direct text input ({len(text)} chars){Style.RESET_ALL}")
    return text.strip()


def split_into_articles(raw_text: str) -> list:
    articles = [a.strip() for a in raw_text.split("\n\n") if a.strip()]
    print(f"{Fore.CYAN}[FETCHER] Detected {len(articles)} article(s){Style.RESET_ALL}")
    return articles