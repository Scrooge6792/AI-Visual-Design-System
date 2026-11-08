from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import secrets
import threading
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .cli import request as core_request

READ_COMMANDS = {
    "status", "asset.get", "asset.preview", "queue.get", "queue.preview",
    "proposal.get", "candidate.get", "search.pending", "search.concepts",
    "search.assets", "search.related", "search.explain", "knowledge.get",
    "knowledge.search", "prompt.get", "prompt.list", "prompt.render", "visual.search",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "AVDSWeb/1"

    def _security_headers(self, content_type="application/json; charset=utf-8"):
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")

    def _authorized(self):
        cookies = {}
        for part in self.headers.get("Cookie", "").split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1); cookies[key] = value
        return secrets.compare_digest(cookies.get("avds_session", ""), self.server.token)

    def _json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status); self._security_headers(); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path); query = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/session" and query.get("token") and secrets.compare_digest(query["token"][0], self.server.token):
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Set-Cookie", f"avds_session={self.server.token}; HttpOnly; SameSite=Strict; Path=/")
            self.send_header("Location", "/"); self._security_headers("text/plain; charset=utf-8"); self.end_headers(); return
        if not self._authorized():
            self._json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": {"code": "ACCESS_DENIED", "message": "请从 avds-web 生成的本机入口打开。"}}); return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT); self._security_headers("image/x-icon"); self.end_headers(); return
        if parsed.path == "/media": self._media(query); return
        name = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
        if name not in {"index.html", "app.css", "app.js"}: self.send_error(HTTPStatus.NOT_FOUND); return
        path = Path(__file__).with_name("web_assets") / name; body = path.read_bytes(); content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK); self._security_headers(content_type); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def _media(self, query):
        kind = (query.get("kind") or [""])[0]; identifier = (query.get("id") or [""])[0]
        if kind not in {"asset", "queue"} or not identifier:
            self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": {"code": "VALIDATION_FAILED", "message": "媒体参数不合法"}}); return
        command, key = ("asset.preview", "asset_id") if kind == "asset" else ("queue.preview", "queue_item_id")
        response = core_request(self.server.socket_path, {"command": command, key: identifier})
        if not response.get("ok"): self._json(HTTPStatus.NOT_FOUND, response); return
        result = response["result"]; body = Path(result["content_path"]).read_bytes()
        if "sha256:" + hashlib.sha256(body).hexdigest() != result["file_hash"]:
            self._json(HTTPStatus.CONFLICT, {"ok": False, "error": {"code": "HASH_MISMATCH", "message": "媒体指纹异常"}}); return
        self.send_response(HTTPStatus.OK); self._security_headers(result["mime_type"]); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        if not self._authorized(): self._json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": {"code": "ACCESS_DENIED", "message": "会话无效"}}); return
        if self.headers.get("Origin") not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
            self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": {"code": "ACCESS_DENIED", "message": "来源不可信"}}); return
        if self.path != "/api/command": self.send_error(HTTPStatus.NOT_FOUND); return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 64 * 1024: self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": {"code": "RESOURCE_LIMIT", "message": "请求体积不合法"}}); return
        try: payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError: self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": {"code": "VALIDATION_FAILED", "message": "JSON 不合法"}}); return
        if payload.get("command") not in READ_COMMANDS:
            self._json(HTTPStatus.FORBIDDEN, {"ok": False, "error": {"code": "ACCESS_DENIED", "message": "WebUI 仅开放只读命令"}}); return
        self._json(HTTPStatus.OK, core_request(self.server.socket_path, payload))

    def log_message(self, format, *args): return


def main():
    parser = argparse.ArgumentParser(description="AI Visual Design local WebUI")
    parser.add_argument("--socket", default=str(Path.home() / "Library/Application Support/AIVisualDesign/core.sock")); parser.add_argument("--port", type=int, default=0); parser.add_argument("--open", action="store_true")
    args = parser.parse_args(); server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.token = secrets.token_urlsafe(32); server.socket_path = args.socket
    url = f"http://127.0.0.1:{server.server_port}/session?token={urllib.parse.quote(server.token)}"; print(url, flush=True)
    if args.open: threading.Timer(0.2, lambda: webbrowser.open(url)).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == "__main__": main()
