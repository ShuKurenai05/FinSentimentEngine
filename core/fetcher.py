import requests
from bs4 import BeautifulSoup

def fetch_from_file(file_path):
    """Reads raw text from a local file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def fetch_from_string(raw_text):
    """Validates and returns inline text string."""
    if not raw_text.strip():
        raise ValueError("Input text cannot be empty.")
    return raw_text.strip()


def fetch_from_url(url):
    """
    Fetches the HTML content from a URL and extracts readable text paragraphs.
    Includes browser simulation headers to prevent anti-bot blocking (HTTP 403/400).
    """
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"Invalid URL protocol: {url}")

    # Spoof a real browser to pass basic anti-bot firewalls
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    try:
        # 15 second timeout to keep slow websites from freezing your Render instance
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise ConnectionError(f"Request timed out while trying to reach {url}")
    except requests.exceptions.HTTPError as e:
        raise ConnectionError(f"HTTP Server Error ({response.status_code}) encountered for {url}")
    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"Network error trying to connect to URL: {str(e)}")

    # Parse webpage elements cleanly using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Strip unnecessary scripts, styles, and navigational elements
    for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        element.decompose()

    # Target regular article content blocks
    paragraphs = soup.find_all("p")
    text_content = [p.get_text().strip() for p in paragraphs if p.get_text().strip()]

    if not text_content:
        # Fallback to general inner text pull if no standard paragraph components are found
        fallback_text = soup.get_text(separator="\n").strip()
        lines = [line.strip() for line in fallback_text.splitlines() if line.strip()]
        if not lines:
            raise ValueError("The target URL resolved successfully, but no readable body text could be extracted.")
        return "\n".join(lines[:150]) # Cap fallback output length

    return "\n\n".join(text_content)
