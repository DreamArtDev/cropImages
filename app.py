from flask import Flask, request, send_file, jsonify
from pathlib import Path
import tempfile
import uuid
import os

from smart_crop import smart_crop

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY", "")


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "service": "image-api"})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/crop", methods=["POST"])
def crop_image():
    auth_header = request.headers.get("X-Api-Key")

    if not API_KEY or auth_header != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    if "image" not in request.files:
        return jsonify({"error": "Brak pliku image"}), 400

    uploaded_file = request.files["image"]

    target_size = int(request.form.get("size", 1000))
    padding = float(request.form.get("padding", 0.08))
    max_upscale = float(request.form.get("max_upscale", 2.0))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        input_path = tmpdir / f"input_{uuid.uuid4().hex}.png"
        output_path = tmpdir / f"output_{uuid.uuid4().hex}.png"

        uploaded_file.save(input_path)

        try:
            smart_crop(
                str(input_path),
                str(output_path),
                target_size=target_size,
                padding=padding,
                max_upscale=max_upscale,
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 400

        return send_file(
            output_path,
            mimetype="image/png",
            as_attachment=False,
            download_name="cropped.png"
        )