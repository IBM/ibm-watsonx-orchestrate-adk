"""Minimal stub agent used as the ARM image deliverable for integration testing.

Exposes:
  GET  /health  — liveness check so ARM can confirm the container is running.
  POST /chat    — minimal invoke endpoint returning a fixed greeting, so the
                  image can be pushed and confirmed end-to-end with a single
                  curl call.
"""
from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "agent": "arm-test-agent"})


@app.route("/chat", methods=["POST"])
def chat():
    return jsonify({"reply": "Hello, World!"})


if __name__ == "__main__":
    # Bind to 0.0.0.0 so ARM can reach the container over the pod network.
    # 127.0.0.1 would only be reachable from within the container itself.
    app.run(host="0.0.0.0", port=8080)  # noqa: S104
