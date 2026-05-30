"""
FinSentimentEngine — Web Server
Run locally: python run_web.py
Then open:   http://localhost:5000
"""

import os
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from colorama import init

init()
load_dotenv()

from core.fetcher import fetch_from_url, fetch_from_string, fetch_from_newsapi
from core.llm_client import analyze_news
from core.output_handler import save_output

app = Flask(__name__)
CORS(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    input_type = data.get("type")
    content = data.get("content", "")

    collected_articles = []
    errors = []

    try:
        if input_type == "urls":
            urls = [u.strip() for u in content if u.strip()]
            if not urls:
                return jsonify({"error": "No URLs provided."}), 400

            for url in urls:
                try:
                    text = fetch_from_url(url)
                    collected_articles.append(f"SOURCE: {url}\n\n{text}")
                except Exception as e:
                    errors.append(str(e))

            if not collected_articles:
                return jsonify({
                    "error": "Could not fetch any of the provided URLs.",
                    "details": errors,
                    "suggestion": "Try copying the article text and using the Paste Text tab instead."
                }), 400

        elif input_type == "text":
            if not content or not content.strip():
                return jsonify({"error": "No text provided."}), 400
            collected_articles = [content.strip()]

        elif input_type == "search":
            query = content.strip()
            if not query:
                return jsonify({"error": "No search query provided."}), 400

            api_key = os.environ.get("NEWSAPI_KEY")
            if not api_key:
                return jsonify({"error": "NewsAPI key not configured on server."}), 500

            try:
                articles = fetch_from_newsapi(query, api_key, num_articles=5)
                collected_articles = articles
            except EnvironmentError as e:
                return jsonify({"error": str(e)}), 500
            except (ConnectionError, ValueError) as e:
                return jsonify({"error": str(e)}), 400

        else:
            return jsonify({"error": "Invalid input type."}), 400

        combined = "\n\n---\n\n".join(collected_articles)
        results = analyze_news(combined)

        # Inject real server timestamp
        results.setdefault("analysis_metadata", {})
        results["analysis_metadata"]["processing_timestamp"] = (
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )

        if errors:
            results["fetch_warnings"] = errors

        save_output(results)
        return jsonify(results)

    except EnvironmentError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  FinSentimentEngine is running.")
    print(f"  Open your browser: http://localhost:{port}\n")
    app.run(debug=False, host="0.0.0.0", port=port)
