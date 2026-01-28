import os
import asyncio
import tempfile
from flask import Flask, request, send_file, jsonify
import trafilatura
import edge_tts

app = Flask(__name__)

# Configuration
DEFAULT_VOICE = "en-US-AriaNeural"
MAX_TEXT_LENGTH = 500000  # ~500K characters max

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "Text-to-Speech API",
        "endpoints": {
            "POST /tts": {
                "description": "Convert text or URL to audio",
                "parameters": {
                    "url": "URL to extract text from (optional)",
                    "text": "Raw text to convert (optional, use either url or text)",
                    "voice": f"Voice to use (default: {DEFAULT_VOICE})"
                }
            },
            "GET /voices": "List available voices"
        }
    })

@app.route("/voices", methods=["GET"])
def list_voices():
    """Return popular voice options"""
    return jsonify({
        "popular": {
            "female": [
                {"id": "en-US-AriaNeural", "description": "News/Novel, positive and confident"},
                {"id": "en-US-AvaNeural", "description": "Conversational, friendly"},
                {"id": "en-US-JennyNeural", "description": "General purpose"},
                {"id": "en-GB-SoniaNeural", "description": "British accent"}
            ],
            "male": [
                {"id": "en-US-AndrewNeural", "description": "Warm and confident"},
                {"id": "en-US-ChristopherNeural", "description": "News/Novel, authoritative"},
                {"id": "en-US-GuyNeural", "description": "General purpose"},
                {"id": "en-GB-RyanNeural", "description": "British accent"}
            ]
        },
        "default": DEFAULT_VOICE
    })

async def generate_audio(text: str, voice: str, output_path: str):
    """Generate audio using edge-tts"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

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
    voice = data.get("voice", DEFAULT_VOICE).strip()

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

    # Generate audio
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            output_path = tmp.name

        # Run async edge-tts
        asyncio.run(generate_audio(text, voice, output_path))

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
