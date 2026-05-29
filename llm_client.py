"""
LLM Client — Groq API (free tier)
Uses LLaMA 3.3 70B via Groq's OpenAI-compatible endpoint.
"""

import os
import json
import requests
from colorama import Fore, Style
from core.prompt_engine import SYSTEM_PROMPT, build_analysis_prompt


def analyze_news(news_text: str) -> dict:
    """
    Send news text to Groq and get structured JSON analysis back.
    Returns parsed Python dict.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise EnvironmentError(
            "GROQ_API_KEY not set in .env file. "
            "Get your free key at https://console.groq.com"
        )

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
            timeout=30
        )
    except requests.Timeout:
        raise RuntimeError("Groq API timed out. Check your internet connection.")
    except requests.RequestException as e:
        raise RuntimeError(f"Network error calling Groq: {e}")

    if response.status_code == 401:
        raise EnvironmentError("Invalid Groq API key. Check your .env file.")
    elif response.status_code == 429:
        raise RuntimeError("Groq rate limit hit. Wait a moment and try again.")
    elif response.status_code != 200:
        raise RuntimeError(f"Groq API error {response.status_code}: {response.text}")

    raw_response = response.json()["choices"][0]["message"]["content"].strip()

    print(f"{Fore.YELLOW}[LLM] Response received. Parsing JSON...{Style.RESET_ALL}")

    # Strip markdown code fences if model adds them
    if raw_response.startswith("```"):
        lines = raw_response.split("\n")
        raw_response = "\n".join(lines[1:-1])

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}[LLM] Raw response that failed to parse:{Style.RESET_ALL}")
        print(raw_response[:500])
        raise ValueError(f"Failed to parse JSON from Groq: {e}")

    return parsed