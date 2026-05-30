"""
LLM Client — Groq API (free tier)
Uses LLaMA 3.1 8B via Groq's OpenAI-compatible endpoint.
Includes retry logic for rate limit handling.
"""

import os
import json
import time
import requests
from colorama import Fore, Style
from core.prompt_engine import SYSTEM_PROMPT, build_analysis_prompt

MAX_INPUT_CHARS = 12000
MAX_RETRIES = 3
RETRY_DELAY = 15  # seconds to wait after rate limit hit


def analyze_news(news_text: str) -> dict:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise EnvironmentError(
            "GROQ_API_KEY not set. Get your free key at https://console.groq.com"
        )

    if len(news_text) > MAX_INPUT_CHARS:
        print(f"{Fore.YELLOW}[LLM] Input too long ({len(news_text)} chars), "
              f"truncating to {MAX_INPUT_CHARS}...{Style.RESET_ALL}")
        news_text = news_text[:MAX_INPUT_CHARS]

    prompt = build_analysis_prompt(news_text)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.2,
    }

    # Retry loop
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"{Fore.YELLOW}[LLM] Sending request to Groq "
              f"(attempt {attempt}/{MAX_RETRIES})...{Style.RESET_ALL}")

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
        except requests.Timeout:
            if attempt < MAX_RETRIES:
                print(f"{Fore.YELLOW}[LLM] Timeout, retrying in {RETRY_DELAY}s...{Style.RESET_ALL}")
                time.sleep(RETRY_DELAY)
                continue
            raise RuntimeError("Groq API timed out after multiple attempts.")
        except requests.RequestException as e:
            raise RuntimeError(f"Network error calling Groq: {e}")

        if response.status_code == 429:
            # Read retry-after header if available
            retry_after = int(response.headers.get("retry-after", RETRY_DELAY))
            if attempt < MAX_RETRIES:
                print(f"{Fore.YELLOW}[LLM] Rate limit hit. "
                      f"Waiting {retry_after}s before retry...{Style.RESET_ALL}")
                time.sleep(retry_after)
                continue
            raise RuntimeError(
                "Groq rate limit hit. You're sending too many requests too quickly. "
                "Wait 30 seconds and try again."
            )

        if response.status_code == 401:
            raise EnvironmentError("Invalid Groq API key.")
        elif response.status_code == 413:
            raise RuntimeError("Input too large for Groq. Try fewer or shorter articles.")
        elif response.status_code != 200:
            raise RuntimeError(f"Groq API error {response.status_code}: {response.text[:200]}")

        # Success — parse response
        try:
            response_json = response.json()
            raw_response = response_json["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"Unexpected response structure from Groq: {e}")

        if not raw_response or len(raw_response) < 10:
            raise ValueError("Groq returned an empty response.")

        print(f"{Fore.YELLOW}[LLM] Response received ({len(raw_response)} chars). "
              f"Parsing JSON...{Style.RESET_ALL}")

        if raw_response.startswith("```"):
            lines = raw_response.split("\n")
            raw_response = "\n".join(lines[1:-1]).strip()

        if not raw_response.startswith("{"):
            print(f"{Fore.RED}[LLM] Response doesn't look like JSON: "
                  f"{raw_response[:200]}{Style.RESET_ALL}")
            raise ValueError(
                "Groq returned plain text instead of JSON. "
                "Try with a shorter article or use the 'Paste Text' tab."
            )

        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON from Groq: {e}")

        return parsed

    raise RuntimeError("Groq failed after all retry attempts. Please wait a minute and try again.")
