"""Lightweight streaming proxy that strips duplicate reasoning fields from vLLM.

vLLM emits both 'reasoning' and 'reasoning_content' in streaming chunks for
reasoning models. Goose's Rust JSON parser treats these as duplicates and crashes.
This proxy removes the 'reasoning' field, keeping only 'reasoning_content'.

Usage:
  python3 llm_proxy.py &
  export OPENAI_HOST=http://localhost:8787
  goose run --no-session --text "hello"
"""

import json
import os
import re
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import ssl

UPSTREAM = os.environ.get(
    "LLM_UPSTREAM",
    os.environ.get("LLAMASTACK_URL", "https://llamastack-llamastack.apps.ocp.v7hjl.sandbox2288.opentlc.com"),
).rstrip("/")
PORT = int(os.environ.get("LLM_PROXY_PORT", "8787"))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

REASONING_RE = re.compile(r',\s*"reasoning"\s*:\s*(?:"(?:[^"\\]|\\.)*"|null)\s*')


def strip_reasoning(line: str) -> str:
    if '"reasoning"' not in line:
        return line
    return REASONING_RE.sub("", line)


class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        url = f"{UPSTREAM}{self.path}"

        req = Request(url, data=body, method="POST")
        for k, v in self.headers.items():
            if k.lower() not in ("host", "content-length", "transfer-encoding"):
                req.add_header(k, v)
        req.add_header("Content-Length", str(len(body)))

        try:
            resp = urlopen(req, context=ctx)
        except HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() not in ("transfer-encoding",):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(e.read())
            return

        self.send_response(resp.status)
        is_stream = False
        for k, v in resp.headers.items():
            if k.lower() == "transfer-encoding":
                continue
            self.send_header(k, v)
            if k.lower() == "content-type" and "text/event-stream" in v:
                is_stream = True
        self.end_headers()

        if is_stream:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace")
                cleaned = strip_reasoning(line)
                self.wfile.write(cleaned.encode("utf-8"))
                self.wfile.flush()
        else:
            data = resp.read().decode("utf-8", errors="replace")
            cleaned = strip_reasoning(data)
            self.wfile.write(cleaned.encode("utf-8"))

    def do_GET(self):
        url = f"{UPSTREAM}{self.path}"
        req = Request(url, method="GET")
        for k, v in self.headers.items():
            if k.lower() not in ("host",):
                req.add_header(k, v)
        try:
            resp = urlopen(req, context=ctx)
        except HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
            return
        self.send_response(resp.status)
        for k, v in resp.headers.items():
            if k.lower() != "transfer-encoding":
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(resp.read())

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    print(f"LLM proxy listening on http://localhost:{PORT}", file=sys.stderr)
    print(f"Upstream: {UPSTREAM}", file=sys.stderr)
    HTTPServer(("0.0.0.0", PORT), ProxyHandler).serve_forever()
