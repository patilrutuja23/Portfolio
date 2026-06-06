import base64
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/proxy":
            self.handle_proxy(parsed)
            return

        file_path = ROOT / parsed.path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            self.serve_file(file_path)
            return

        index_file = ROOT / "index.html"
        if index_file.exists():
            self.serve_file(index_file)
            return

        self.send_error(404, "Not found")

    def handle_proxy(self, parsed):
        query = urllib.parse.parse_qs(parsed.query)
        url = query.get("url", [None])[0]
        if not url:
            self.send_error(400, "Missing url query parameter")
            return

        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=60) as response:
                content = response.read()
                content_type = response.headers.get_content_type()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "public, max-age=3600")
                self.end_headers()
                self.wfile.write(content)
        except (BrokenPipeError, ConnectionAbortedError):
            pass
        except Exception as exc:
            try:
                self.send_error(502, f"Proxy fetch failed: {exc}")
            except (BrokenPipeError, ConnectionAbortedError):
                pass

    def serve_file(self, file_path: Path):
        content = file_path.read_bytes()
        content_type = "text/html; charset=utf-8" if file_path.suffix.lower() in {".html", ".htm"} else None
        if not content_type:
            import mimetypes
            content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        try:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionAbortedError):
            pass

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 3000), Handler)
    print("Serving on http://localhost:3000")
    server.serve_forever()
