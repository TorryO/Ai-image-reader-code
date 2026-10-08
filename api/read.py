"""Vercel serverless function for image analysis with Anthropic."""

import json
import os
from http.server import BaseHTTPRequestHandler

import anthropic

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024


class handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0") or "0")
            if content_length <= 0:
                return self._send_json(400, {"error": "Request body is required."})
            if content_length > MAX_IMAGE_BYTES:
                return self._send_json(413, {"error": "Request body exceeds the size limit."})

            raw_body = self.rfile.read(content_length)
            data = json.loads(raw_body or b"{}")
            if not isinstance(data, dict):
                return self._send_json(400, {"error": "JSON object required."})

            image = data.get("image")
            media_type = data.get("media_type", "image/jpeg")
            prompt = data.get("prompt") or "Describe this image in detail."

            if not isinstance(image, str) or not image.strip():
                return self._send_json(400, {"error": "No image provided."})
            if media_type not in ALLOWED_MIME_TYPES:
                return self._send_json(400, {"error": f"Unsupported type: {media_type}"})
            if not os.environ.get("ANTHROPIC_API_KEY"):
                return self._send_json(500, {"error": "ANTHROPIC_API_KEY is not set."})

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
            answer = response.content[0].text
            return self._send_json(200, {"answer": answer})
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            return self._send_json(400, {"error": f"Invalid request: {exc}"})
        except Exception as exc:  # Surface the API failure without exposing internals.
            return self._send_json(500, {"error": str(exc)})

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
