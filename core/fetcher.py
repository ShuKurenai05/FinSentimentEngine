"""
Fetcher — handles URL scraping, raw text, and file input.
"""

import os
import re
import random
import requests
from colorama import Fore, Style

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

BLOCKED_DOMAINS = [
    "bloomberg.com", "ft.com", "wsj.com", "barrons.com",
    "reuters.com", "businessinsider.com"
]

JS_HEAVY_DOMAINS = [
    "moneycontrol.com", "economictimes.indiatimes.com",
    "livemint.com", "ndtvprofit.com", "businesstoday.in",
    "financialexpress.com"
]


def _get_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower().replace("www.", "")
    except:
        return ""


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
    domain = _get_domain(url)

    for blocked in BLOCKED_DOMAINS:
        if blocked in domain:
            raise ConnectionError(
                f"{domain} blocks automated access (paywall/bot protection). "
                f"Copy the article text manually and use the 'Paste Text' tab instead."
            )

    is_js_heavy = any(js in domain for js in JS_HEAVY_DOMAINS)
    if is_js_heavy:
        print(f"{Fore.YELLOW}[FETCHER] Warning: {domain} is JS-heavy, extraction may be partial{Style.RESET_ALL}")

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
    ]

    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.Timeout:
        raise ConnectionError(
            f"Timed out fetching {url}. "
            f"The site may be slow or blocking requests. Try the 'Paste Text' tab."
        )
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        if status == 403:
            raise ConnectionError(
                f"{domain} returned 403 Forbidden — it's actively blocking scrapers. "
                f"Copy the article text manually and use the 'Paste Text' tab."
            )
        elif status == 404:
            raise ConnectionError(f"Article not found (404) at {url} — check the link.")
        else:
            raise ConnectionError(f"HTTP {status} error fetching {url}.")
    except requests.RequestException as e:
        raise ConnectionError(f"Network error fetching {url}: {str(e)}")

    if BS4_AVAILABLE:
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer",
                          "header", "aside", "form", "noscript",
                          "iframe", "figure", "figcaption"]):
            tag.decompose()

        selectors = [
            "article",
            "main",
            "[class*='article-body']",
            "[class*='article-content']",
            "[class*='story-content']",
            "[class*='post-content']",
            "[class*='entry-content']",
            "[class*='content-body']",
            "[id*='article-body']",
            "[id*='story-body']",
        ]

        target = None
        for selector in selectors:
            found = soup.select_one(selector)
            if found:
                target = found
                break

        if not target:
            target = soup.find("body")

        if target:
            paragraphs = target.find_all("p")
            text = " ".join(
                p.get_text(separator=" ", strip=True)
                for p in paragraphs
                if len(p.get_text(strip=True)) > 30
            )
        else:
            text = soup.get_text(separator=" ", strip=True)

        text = re.sub(r'\s+', ' ', text).strip()
    else:
        text = response.text.strip()

    if len(text) < 100:
        if is_js_heavy:
            raise ConnectionError(
                f"{domain} requires JavaScript to load content. "
                f"Copy the article text manually and use the 'Paste Text' tab instead."
            )
        raise ConnectionError(
            f"Could not extract meaningful text from {url}. "
            f"The page may be empty, paywalled, or require login."
        )

    print(f"{Fore.CYAN}[FETCHER] Scraped: {url} ({len(text)} chars){Style.RESET_ALL}")
    return text[:6000]


def fetch_from_string(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("Input text is empty.")
    print(f"{Fore.CYAN}[FETCHER] Using direct text input ({len(text)} chars){Style.RESET_ALL}")
    return text.strip()


def split_into_articles(raw_text: str) -> list:
    articles = [a.strip() for a in raw_text.split("\n\n") if a.strip()]
    print(f"{Fore.CYAN}[FETCHER] Detected {len(articles)} article(s){Style.RESET_ALL}")
    return articles
