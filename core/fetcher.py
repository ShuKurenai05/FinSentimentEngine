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
    "financialexpress.com", "thehindu.com", "hindustantimes.com",
    "cnbctv18.com"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

def _clean_text(text: str) -> str:
    """
    Clean scraped text before sending to AI.
    Aggressively removes garbage, unicode noise, and irrelevant content.
    """
    # Keep only printable ASCII characters
    text = text.encode("ascii", errors="ignore").decode("ascii")

    # Remove sequences of repeated characters (aaaaaaa, >>>>>, etc.)
    text = re.sub(r'(.)\1{4,}', '', text)

    # Remove lines that are too short to be meaningful
    # or contain known noise phrases
    noise_phrases = [
        "subscribe", "sign in", "log in", "register",
        "cookie", "accept", "privacy policy", "terms",
        "advertisement", "also read", "read more", "click here",
        "follow us", "download app", "get app", "breaking news",
        "javascript", "enable javascript", "please enable",
        "live updates", "refresh", "notification",
        "whatsapp", "telegram", "facebook", "twitter", "instagram",
        "share this", "bookmark", "save article",
    ]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    cleaned = []
    for sentence in sentences:
        s = sentence.strip()
        if len(s) < 25:
            continue
        s_lower = s.lower()
        if any(noise in s_lower for noise in noise_phrases):
            continue
        # Skip sentences that are mostly non-alphabetic
        alpha_ratio = sum(c.isalpha() for c in s) / max(len(s), 1)
        if alpha_ratio < 0.5:
            continue
        cleaned.append(s)

    result = " ".join(cleaned)
    result = re.sub(r'\s+', ' ', result).strip()
    return result

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


def _extract_text_from_soup(soup, max_paragraphs: int = 20) -> str:
    """
    Extract clean paragraph text from a BeautifulSoup object.
    Limits to first max_paragraphs to avoid massive live blog pages.
    """
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
        # Only take first max_paragraphs — prevents live blogs from exploding
        paragraphs = paragraphs[:max_paragraphs]
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
                text = _clean_text(text)
                if len(text) > 200:
                    print(f"{Fore.CYAN}[FETCHER] archive.ph succeeded ({len(text)} chars){Style.RESET_ALL}")
                    return text[:2000]
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
    text = _clean_text(text)
    if len(text) < 100:
        raise ConnectionError(
            f"After cleaning, not enough readable text could be extracted from {url}. "
            f"Try copying the article text manually and using the 'Paste Text' tab."
        )
    return text[:2000]

def fetch_from_string(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("Input text is empty.")
    print(f"{Fore.CYAN}[FETCHER] Using direct text input ({len(text)} chars){Style.RESET_ALL}")
    return text.strip()


def split_into_articles(raw_text: str) -> list:
    articles = [a.strip() for a in raw_text.split("\n\n") if a.strip()]
    print(f"{Fore.CYAN}[FETCHER] Detected {len(articles)} article(s){Style.RESET_ALL}")
    return articles

def fetch_from_newsapi(query: str, api_key: str, num_articles: int = 5) -> list:
    """
    Fetch latest news articles matching a search query via NewsAPI.
    Returns a list of cleaned article text strings.
    """
    print(f"{Fore.CYAN}[FETCHER] Searching NewsAPI for: '{query}'{Style.RESET_ALL}")

    url = "https://newsapi.org/v2/everything"
    params = {
    "q": f'"{query}" stock OR shares OR market OR earnings OR revenue OR investor',
    "language": "en",
    "sortBy": "publishedAt",
    "pageSize": num_articles,
    "apiKey": api_key,
    "domains": (
        "reuters.com,bloomberg.com,cnbc.com,finance.yahoo.com,"
        "marketwatch.com,investing.com,businessinsider.com,"
        "economictimes.indiatimes.com,livemint.com,moneycontrol.com,"
        "thehindu.com,businesstoday.in,financialexpress.com,"
        "zeebiz.com,ndtvprofit.com"
    )
}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.Timeout:
        raise ConnectionError("NewsAPI timed out. Try again.")
    except requests.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        if status == 401:
            raise EnvironmentError("Invalid NewsAPI key. Check your environment variables.")
        elif status == 426:
            raise EnvironmentError(
                "NewsAPI free tier only works on localhost. "
                "On a live server you need a paid plan. "
                "Use the Paste Text tab instead."
            )
        else:
            raise ConnectionError(f"NewsAPI error {status}.")
    except requests.RequestException as e:
        raise ConnectionError(f"Network error calling NewsAPI: {e}")

    data = response.json()

    if data.get("status") != "ok":
        raise ConnectionError(f"NewsAPI returned error: {data.get('message', 'Unknown error')}")

    articles = data.get("articles", [])
    if not articles:
        raise ValueError(f"No articles found for '{query}'. Try a different search term.")

    results = []
    for a in articles:
        source = a.get("source", {}).get("name", "Unknown")
        title = a.get("title", "")
        description = a.get("description") or ""
        content = a.get("content") or ""

        # NewsAPI free tier truncates content at 200 chars
        # Combine title + description + content for maximum text
        combined = f"SOURCE: {source}\nTITLE: {title}\n\n{description}\n\n{content}"
        combined = _clean_text(combined)

        if len(combined) > 50:
            results.append(combined)

    if not results:
        raise ValueError(f"Articles found but no readable content extracted for '{query}'.")

    print(f"{Fore.CYAN}[FETCHER] NewsAPI returned {len(results)} articles for '{query}'{Style.RESET_ALL}")
    return results
