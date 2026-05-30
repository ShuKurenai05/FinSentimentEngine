"""
Fetcher — handles URL scraping, raw text, and file input.
Supports direct scraping, archive.ph fallback for JS-heavy sites,
and clear error messages for blocked/paywalled domains.
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

# Hard paywalls — scraping will never work, tell user to paste text
BLOCKED_DOMAINS = [
    "bloomberg.com", "ft.com", "wsj.com", "barrons.com",
    "businessinsider.com"
]

# JavaScript-rendered sites — BeautifulSoup can't read them directly
# We route these through archive.ph automatically
JS_HEAVY_DOMAINS = [
    "moneycontrol.com", "economictimes.indiatimes.com",
    "livemint.com", "ndtvprofit.com", "businesstoday.in",
    "financialexpress.com", "thehindu.com", "hindustantimes.com"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]


def _get_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc.lower().replace("www.", "")
    except:
        return ""


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }


def _extract_text_from_soup(soup) -> str:
    """Extract clean paragraph text from a BeautifulSoup object."""
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

    return re.sub(r'\s+', ' ', text).strip()


def _try_archive(url: str) -> str:
    """
    For JS-heavy sites, fetch via archive.ph which stores
    fully rendered static snapshots. Free, no JS needed.
    Returns empty string if it fails.
    """
    archive_url = f"https://archive.ph/newest/{url}"
    print(f"{Fore.YELLOW}[FETCHER] Routing through archive.ph...{Style.RESET_ALL}")

    try:
        response = requests.get(archive_url, headers=_get_headers(), timeout=20)
        if response.status_code == 200 and BS4_AVAILABLE:
            soup = BeautifulSoup(response.text, "html.parser")
            text = _extract_text_from_soup(soup)
            if len(text) > 200:
                print(f"{Fore.CYAN}[FETCHER] archive.ph succeeded ({len(text)} chars){Style.RESET_ALL}")
                return text[:6000]
        print(f"{Fore.YELLOW}[FETCHER] archive.ph returned too little text{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}[FETCHER] archive.ph failed: {e}{Style.RESET_ALL}")

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
    """
    Fetch and extract readable article text from a news URL.
    - Paywalled sites: clear error message, user told to paste text
    - JS-heavy sites: auto-routed through archive.ph
    - Normal sites: direct BeautifulSoup scrape
    """
    domain = _get_domain(url)

    # Hard block — paywalled sites we know will never work
    for blocked in BLOCKED_DOMAINS:
        if blocked in domain:
            raise ConnectionError(
                f"{domain} has a hard paywall and blocks all scrapers. "
                f"Open the article, select all text, copy it, "
                f"and paste it into the 'Paste Text' tab instead."
            )

    # JS-heavy sites — try archive.ph first
    is_js_heavy = any(js in domain for js in JS_HEAVY_DOMAINS)
    if is_js_heavy:
        archived = _try_archive(url)
        if archived:
            return archived
        # archive.ph failed — fall through to direct scrape attempt
        print(f"{Fore.YELLOW}[FETCHER] Attempting direct scrape as fallback...{Style.RESET_ALL}")

    # Direct scrape
    try:
        response = requests.get(url, headers=_get_headers(), timeout=15)
        response.raise_for_status()
    except requests.Timeout:
        raise ConnectionError(
            f"Timed out fetching {url}. "
            f"Try copying the article text and using the 'Paste Text' tab."
        )
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        if status == 403:
            raise ConnectionError(
                f"{domain} blocked the request (403 Forbidden). "
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
        text = _extract_text_from_soup(soup)
    else:
        text = response.text.strip()

    if len(text) < 100:
        if is_js_heavy:
            raise ConnectionError(
                f"{domain} requires JavaScript and archive.ph didn't have a snapshot. "
                f"Copy the article text manually and use the 'Paste Text' tab."
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
