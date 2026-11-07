#!/usr/bin/env python3
"""Serve the local prototype. No training occurs at startup or on Analyze."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import argparse
import json
import sys
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.prototype import ComparisonApp, WEB_DIR


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, app, **kwargs):
        self.app = app
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        url = urlparse(self.path)
        if not url.path.startswith("/api/"):
            return super().do_GET()
        try:
            if url.path == "/api/summary":
                data = self.app.summary()
            elif url.path == "/api/analyze":
                query = parse_qs(url.query)
                data = self.app.analyze(query.get("location", [""])[0],
                                        float(query.get("radius", ["2"])[0]))
            else:
                return self.send_error(404)
            self.send_json(data)
        except ValueError as error:
            self.send_json({"error": str(error)}, status=400)
        except Exception:
            import traceback
            traceback.print_exc()
            self.send_json({"error": "Analysis failed. Check the server terminal for details."}, status=500)

    def send_json(self, data, status=200):
        body = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        app = ComparisonApp()
    except (FileNotFoundError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, app=app))
    print(f"PIGEON-AI comparison: http://127.0.0.1:{args.port} (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
