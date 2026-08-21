"""A narrow public door to a private model.

The apps are static pages on GitHub Pages. The model lives on a machine
inside a tailnet. Neither can reach the other, and asking a visitor for an
API key means nobody ever tries the thing. This closes that gap: a small
proxy running on a machine that can see both, published over HTTPS by
Tailscale Funnel.

It is deliberately narrow. One endpoint. The request is rebuilt rather than
forwarded, so a caller cannot smuggle fields through to the model. There is
no credential here to steal, because the model behind it needs none. What
protects the GPU is the rate limit and the size cap, not a secret.

  MODEL_URL   where to forward       default the Qwen 3.8 box on :8082
  MODEL_NAME  model id to stamp on   default unset (llama.cpp ignores it)
  PORT        local port             default 8791
  ALLOW       allowed origins        default the two GitHub Pages apps
"""

import json
import os
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import httpx

MODEL_URL = os.environ.get(
    "MODEL_URL", "http://100.73.250.50:8082/v1/chat/completions")
MODEL_NAME = os.environ.get("MODEL_NAME", "")
PORT = int(os.environ.get("PORT", "8791"))
ALLOW = [o.strip() for o in os.environ.get(
    "ALLOW", "https://pbchrist.github.io").split(",") if o.strip()]

# A public door needs limits or it becomes somebody else's free GPU.
MAX_CHARS = 24000
MAX_TOKENS = 8000
RATE_N, RATE_WINDOW = 12, 300
TIMEOUT = 600

_hits: dict = {}
_lock = threading.Lock()


def allowed(origin):
    if not origin:
        return ALLOW[0] if ALLOW else None
    return origin if origin in ALLOW else None


def rate_ok(addr):
    now = time.time()
    with _lock:
        q = _hits.setdefault(addr, deque())
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_N:
            return False
        q.append(now)
        return True


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)

    def _cors(self, origin):
        who = allowed(origin)
        if who:
            self.send_header("Access-Control-Allow-Origin", who)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        # Chrome Private Network Access. Anyone on the same tailnet resolves
        # this host to a 100.x address, and Chrome refuses to let a public
        # page reach a private one unless the server opts in by name. Without
        # this the app works for strangers and fails for the person who owns
        # it, which is the worst possible split.
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, code, payload, origin="", close=False):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if close:
            self.send_header("Connection", "close")
            self.close_connection = True
        self._cors(origin)
        self.end_headers()
        self.wfile.write(body)

    def _drain(self):
        """Read the request body even when we are about to refuse it.

        On a keep-alive connection an unread body is not discarded - it stays
        in the socket and the next request line is parsed out of the middle of
        it, which surfaces as a bogus 501. Every refusal path must drain first.
        """
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return b""
        return self.rfile.read(n) if n > 0 else b""

    def do_OPTIONS(self):
        self._drain()
        self.send_response(204)
        self._cors(self.headers.get("Origin", ""))
        # Echo back whatever headers the preflight asked about, so a browser
        # that requests something beyond Content-Type is not refused.
        want = self.headers.get("Access-Control-Request-Headers")
        if want:
            self.send_header("Access-Control-Allow-Headers", want)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        origin = self.headers.get("Origin", "")
        if urlparse(self.path).path in ("/health", "/"):
            self._json(200, {"ok": True, "model": MODEL_NAME or "default"}, origin)
        else:
            self._json(404, {"error": "not found"}, origin)

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        raw = self._drain()          # always, before any refusal

        if urlparse(self.path).path not in ("/v1/chat/completions", "/chat"):
            self._json(404, {"error": "this bridge forwards one endpoint only"}, origin)
            return
        if origin and not allowed(origin):
            self._json(403, {"error": "origin not allowed"}, origin)
            return
        if not rate_ok(self.address_string()):
            self._json(429, {"error": "Slow down - this is one small GPU. "
                                      "Try again in a few minutes."}, origin)
            return

        try:
            req = json.loads(raw or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "bad JSON"}, origin)
            return

        msgs = req.get("messages")
        if not isinstance(msgs, list) or not msgs:
            self._json(400, {"error": "messages required"}, origin)
            return
        if sum(len(str(m.get("content", ""))) for m in msgs) > MAX_CHARS:
            self._json(413, {"error": f"too long; keep it under {MAX_CHARS} characters"},
                       origin)
            return

        payload = {
            "messages": [{"role": str(m.get("role", "user"))[:20],
                          "content": str(m.get("content", ""))} for m in msgs],
            "temperature": min(float(req.get("temperature", 0.2) or 0.2), 1.0),
            "max_tokens": min(int(req.get("max_tokens", 4000) or 4000), MAX_TOKENS),
            "stream": False,
        }
        if MODEL_NAME:
            payload["model"] = MODEL_NAME

        try:
            with httpx.Client(timeout=TIMEOUT) as c:
                r = c.post(MODEL_URL, json=payload)
        except httpx.HTTPError as exc:
            self._json(502, {"error": f"model unreachable: {exc}"}, origin)
            return
        if r.status_code >= 400:
            self._json(502, {"error": f"model returned {r.status_code}"}, origin)
            return
        try:
            self._json(200, r.json(), origin)
        except ValueError:
            self._json(502, {"error": "model returned unreadable JSON"}, origin)


if __name__ == "__main__":
    print(f"bridge -> {MODEL_URL}")
    print(f"listening on 127.0.0.1:{PORT}, allowing {ALLOW}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
