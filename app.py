import os
import requests
from flask import Flask, request, jsonify, render_template
import trafilatura

app = Flask(__name__)

FETCH_TIMEOUT = 30

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/extract", methods=["POST"])
def extract_text():
    try:
        data = request.get_json() if request.is_json else request.form.to_dict()
        url = data.get("url", "").strip()
        if not url:
            return jsonify({"error": "URL is required"}), 400

        response = requests.get(url, timeout=FETCH_TIMEOUT, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        response.raise_for_status()

        text = trafilatura.extract(response.text, include_comments=False, include_tables=False)
        if not text:
            return jsonify({"error": "Could not extract text from URL. The page may be paywalled or use JavaScript."}), 400

        return jsonify({"text": text, "length": len(text)})

    except requests.Timeout:
        return jsonify({"error": "URL took too long to fetch."}), 400
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to fetch URL: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to extract text: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
