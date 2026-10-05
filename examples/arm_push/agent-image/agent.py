"""Minimal stub agent used as the ARM image deliverable for integration testing.

Exposes a single /health endpoint so ARM can confirm the image is runnable.
"""
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "agent": "arm-test-agent"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080)
