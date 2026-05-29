"""
FinSentimentEngine — Web Server
"""

import os
import sys
import importlib
import types

# =====================================================================
# FORCE PYTHON TO MAP 'core.X' TO YOUR FLAT ROOT FILES
# =====================================================================
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Map the core submodules explicitly so other files don't crash
for mod_name in ['fetcher', 'llm_client', 'output_handler', 'prompt_engine']:
    try:
        sys.modules[f'core.{mod_name}'] = importlib.import_module(mod_name)
    except Exception:
        pass

sys.modules['core'] = types.ModuleType('core')
# =====================================================================

import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from colorama import init

init()
load_dotenv()

# Safe to import now
from fetcher import fetch_from_url, fetch_from_string
from llm_client import analyze_news
from output_handler import save_output

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid or empty payload."}), 400

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
                    errors.append(f"Could not fetch {url}: {str(e)}")

            if not collected_articles:
                return jsonify({"error": "All URLs failed to load.", "details": errors}), 400

        elif input_type == "text":
            if not content or not content.strip():
                return jsonify({"error": "No text provided."}), 400
            collected_articles = [content.strip()]

        else:
            return jsonify({"error": "Invalid input type."}), 400

        combined = "\n\n---\n\n".join(collected_articles)
        results = analyze_news(combined)

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
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
