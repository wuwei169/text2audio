import os
import tempfile
from flask import Flask, request, send_file, jsonify, render_template
import trafilatura
from gtts import gTTS

app = Flask(__name__)

# Configuration
MAX_TEXT_LENGTH = 100000  # gTTS works better with shorter texts

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/voices", methods=["GET"])
def list_voices():
    """Return available accent options"""
    return jsonify({
        "accents": [
            {"id": "com", "description": "US English"},
            {"id": "co.uk", "description": "UK English"},
            {"id": "com.au", "description": "Australian English"},
            {"id": "co.in", "description": "Indian English"}
        ],
        "default": "com"
    })

@app.route("/tts", methods=["POST"])
def text_to_speech():
    """Convert text or URL to audio"""

    # Get parameters from JSON body or form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()

    url = data.get("url", "").strip()
    text = data.get("text", "").strip()
    accent = data.get("voice", "com").strip()  # Keep 'voice' param name for compatibility

    # Validate input
    if not url and not text:
        return jsonify({"error": "Either 'url' or 'text' parameter is required"}), 400

    # Extract text from URL if provided
    if url:
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return jsonify({"error": f"Could not fetch URL: {url}"}), 400

            text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            if not text:
                return jsonify({"error": "Could not extract text from URL"}), 400
        except Exception as e:
            return jsonify({"error": f"Failed to extract text: {str(e)}"}), 500

    # Validate text length
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({
            "error": f"Text too long ({len(text)} chars). Maximum is {MAX_TEXT_LENGTH} characters."
        }), 400

    # Generate audio using gTTS
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            output_path = tmp.name

        # Use gTTS to generate audio
        tts = gTTS(text=text, lang='en', tld=accent)
        tts.save(output_path)

        # Send file and clean up after
        response = send_file(
            output_path,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name="audio.mp3"
        )

        # Clean up temp file after sending
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(output_path)
            except:
                pass

        return response

    except Exception as e:
        return jsonify({"error": f"Failed to generate audio: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
