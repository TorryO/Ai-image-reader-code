"""Vercel serverless function: POST {image: <base64>, media_type, prompt} -> {answer}"""

import json
import os
from http.server import BaseHTTPRequestHandler

import anthropic

MODEL = "claude-sonnet-5-5"
ALLOWED = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length) or b"{}")

            image = data.get("image")
            media_type = data.get("media_type", "image/jpeg")
            prompt = data.get("prompt") or "Describe this image in detail."

            if not image:
                return self._send(400, {"error": "No image provided."})
            if media_type not in ALLOWED:
                return self._send(400, {"error": f"Unsupported type: {media_type}"})
            if not os.environ.get("ANTHROPIC_API_KEY"):
                return self._send(500, {"error": "ANTHROPIC_API_KEY is not set."})

            client = anthropic.Anthropic()
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            )
            self._send(200, {"answer": response.content[0].text})
        except Exception as e:  # keep the demo simple: surface the error
            self._send(500, {"error": str(e)})

