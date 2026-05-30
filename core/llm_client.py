"""
LLM Client — Groq API (free tier)
Uses LLaMA 3.3 70B via Groq's OpenAI-compatible endpoint.
"""

import os
import json
import requests
from colorama import Fore, Style
from core.prompt_engine import SYSTEM_PROMPT, build_analysis_prompt

# Maximum characters we'll send to Groq in one request
# Groq's context window is ~32k tokens — 12000 chars is safe
MAX_INPUT_CHARS = 12000


def analyze_news(news_text: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise EnvironmentError(
            "GROQ_API_KEY not set. Get your free key at https://console.groq.com"
        )

    # Hard cap — truncate if combined articles are too long
    if len(news_text) > MAX_INPUT_CHARS:
        print(f"{Fore.YELLOW}[LLM] Input too long ({len(news_text)} chars), "
              f"truncating to {MAX_INPUT_CHARS}...{Style.RESET_ALL}")
        news_text = news_text[:MAX_INPUT_CHARS]

    prompt = build_analysis_prompt(news_text)

    print(f"{Fore.YELLOW}[LLM] Sending request to Groq API (LLaMA 3.3 70B)...{Style.RESET_ALL}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.2
    }

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
    except requests.Timeout:
        raise RuntimeError("Groq API timed out. Check your internet connection.")
    except requests.RequestException as e:
        raise RuntimeError(f"Network error calling Groq: {e}")

    if response.status_code == 401:
        raise EnvironmentError("Invalid Groq API key. Check your environment variables.")
    elif response.status_code == 429:
        raise RuntimeError("Groq rate limit hit. Wait a moment and try again.")
    elif response.status_code == 413:
        raise RuntimeError("Input too large for Groq. Try fewer or shorter articles.")
    elif response.status_code != 200:
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text[:200]}")

    try:
        response_json = response.json()
        raw_response = response_json["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as e:
        raise ValueError(f"Unexpected response structure from Groq: {e}")

    # Check for empty or garbage response
    if not raw_response or len(raw_response) < 10:
        raise ValueError(
            "Groq returned an empty response. "
            "The input may have been too long or contained unreadable content."
        )

    print(f"{Fore.YELLOW}[LLM] Response received ({len(raw_response)} chars). "
          f"Parsing JSON...{Style.RESET_ALL}")

    # Strip markdown code fences if model adds them
    if raw_response.startswith("```"):
        lines = raw_response.split("\n")
        raw_response = "\n".join(lines[1:-1]).strip()

    # Check if response looks like JSON before trying to parse
    if not raw_response.startswith("{"):
        print(f"{Fore.RED}[LLM] Response doesn't look like JSON. "
              f"First 200 chars: {raw_response[:200]}{Style.RESET_ALL}")
        raise ValueError(
            "Groq returned plain text instead of JSON. "
            "This usually means the article text was too long or garbled. "
            "Try using the 'Paste Text' tab with a shorter article."
        )

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}[LLM] JSON parse failed. "
              f"First 300 chars of response: {raw_response[:300]}{Style.RESET_ALL}")
        raise ValueError(
            f"Failed to parse JSON from Groq: {e}. "
            f"Try with a shorter or simpler article."
        )

    return parsed
