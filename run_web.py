"""
FinSentimentEngine — Web Server
Run: python run_web.py
Then open: http://localhost:5000
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from colorama import init

init()
load_dotenv()

from core.fetcher import fetch_from_url, fetch_from_string
from core.llm_client import analyze_news
from core.output_handler import save_output

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    # silent=True prevents Flask from automatically throwing a 400 error if headers/JSON are malformed
    data = request.get_json(silent=True)
    
    if data is None:
        print("\n[BACKEND ALERT] Received a POST request to /analyze, but the payload is empty or "
              "missing the 'Content-Type: application/json' header.")
        return jsonify({"error": "Invalid payload. Make sure data is valid JSON and Content-Type header is set."}), 400

    input_type = data.get("type")        # "urls" or "text"
    content = data.get("content", "")    # list of URLs or raw text string

    collected_articles = []
    errors = []

    try:
        if input_type == "urls":
            # Ensure content is a list before processing
            if not isinstance(content, list):
                return jsonify({"error": "For 'urls' input type, 'content' must be an array of links."}), 400
                
            urls = [u.strip() for u in content if u.strip()]
            if not urls:
                return jsonify({"error": "No URLs provided."}), 400

            for url in urls:
                try:
                    text = fetch_from_url(url)
                    collected_articles.append(f"SOURCE: {url}\n\n{text}")
                except Exception as e:
                    errors.append(f"Could not fetch {url}: {str(e)}")

            if not collected_articles:
                return jsonify({"error": "All URLs failed to load.", "details": errors}), 400

        elif input_type == "text":
            if not isinstance(content, str) or not content.strip():
                return jsonify({"error": "No text provided."}), 400
            collected_articles = [content.strip()]

        else:
            return jsonify({"error": "Invalid input type. Must be 'urls' or 'text'."}), 400

        combined = "\n\n---\n\n".join(collected_articles)
        results = analyze_news(combined)

        # Add fetch errors to metadata if any
        if errors:
            results["fetch_warnings"] = errors

        save_output(results)
        return jsonify(results)

    except EnvironmentError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


if __name__ == "__main__":
    print("\n  FinSentimentEngine is running.")
    print("  Open your browser and go to: http://localhost:5000\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
