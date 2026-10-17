"""Serve a build directory's review page and store image flags next to it.

  review_server.py BUILD_DIR [--port 8765]

Open http://localhost:8765/review.html in a browser (WSL forwards localhost to
Windows). Flags set on the page are saved to BUILD_DIR/review-flags.json on
every change, so they can be read back by tools and by Claude.
"""
import argparse
import json
import os
import tempfile
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Handler(SimpleHTTPRequestHandler):
	flags_path: Path

	def do_GET(self):
		if self.path == "/api/flags":
			data = self.flags_path.read_bytes() if self.flags_path.exists() else b"{}"
			self._send(200, data)
		else:
			super().do_GET()

	def do_PUT(self):
		if self.path != "/api/flags":
			return self._send(404, b'{"error": "not found"}')
		body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
		try:
			flags = json.loads(body)
			assert isinstance(flags, dict)
		except (ValueError, AssertionError):
			return self._send(400, b'{"error": "expected a JSON object"}')
		# Write atomically so a crash never leaves a half-written file.
		fd, tmp = tempfile.mkstemp(dir=self.flags_path.parent, suffix=".tmp")
		with os.fdopen(fd, "w") as f:
			json.dump(flags, f, indent=1, ensure_ascii=False)
		os.replace(tmp, self.flags_path)
		self._send(200, b'{"ok": true}')

	def _send(self, code, data):
		self.send_response(code)
		self.send_header("Content-Type", "application/json")
		self.send_header("Content-Length", str(len(data)))
		self.end_headers()
		self.wfile.write(data)

	def log_message(self, fmt, *args):
		if "/api/" in (args[0] if args else ""):
			super().log_message(fmt, *args)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("build", type=Path)
	ap.add_argument("--port", type=int, default=8765)
	args = ap.parse_args()
	Handler.flags_path = args.build.resolve() / "review-flags.json"
	server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(args.build.resolve())))
	print(f"http://localhost:{args.port}/review.html  (flags -> {Handler.flags_path})", flush=True)
	server.serve_forever()


if __name__ == "__main__":
	main()
