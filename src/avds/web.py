from __future__ import annotations

import hashlib
import json
import mimetypes
import secrets
import tempfile
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from pathlib import Path

from .errors import AVDSError
from .util import new_id


class Handler(BaseHTTPRequestHandler):
    server_version = "AVDS/1"

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def _security_headers(self, content_type="application/json; charset=utf-8"):
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")

    def _host_valid(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def _authorized(self):
        if not self._host_valid():
            return False
        authorization = self.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            return secrets.compare_digest(authorization[7:], self.server.token)
        cookies = {}
        for part in self.headers.get("Cookie", "").split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1); cookies[key] = value
        return secrets.compare_digest(cookies.get("avds_session", ""), self.server.token)

    def _json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status); self._security_headers(); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def _error(self, status, code, message):
        self._json(status, AVDSError(code, message).as_dict())

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path); query = urllib.parse.parse_qs(parsed.query)
        if self._host_valid() and parsed.path == "/session" and query.get("token") and secrets.compare_digest(query["token"][0], self.server.token):
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Set-Cookie", f"avds_session={self.server.token}; HttpOnly; SameSite=Strict; Path=/")
            self.send_header("Location", "/"); self._security_headers("text/plain; charset=utf-8"); self.end_headers(); return
        if not self._authorized():
            self._error(HTTPStatus.UNAUTHORIZED, "ACCESS_DENIED", "请启动时使用 avds serve --open，或由 Agent 在项目目录运行 ./bin/avds open"); return
        try:
            if parsed.path == "/favicon.ico":
                self.send_response(HTTPStatus.NO_CONTENT); self._security_headers("image/x-icon"); self.end_headers(); return
            if parsed.path == "/media":
                self._media(query); return
            name = "index.html" if parsed.path == "/" else parsed.path.lstrip("/")
            if name not in {"index.html", "app.css", "app.js"}:
                self.send_error(HTTPStatus.NOT_FOUND); return
            path = Path(__file__).with_name("web_assets") / name
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK); self._security_headers(mimetypes.guess_type(name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        except AVDSError as exc:
            self._json(HTTPStatus.CONFLICT, exc.as_dict())
        except OSError:
            self._error(HTTPStatus.NOT_FOUND, "FILE_MISSING", "文件不可用")

    def _media(self, query):
        kind = (query.get("kind") or [""])[0]; identifier = (query.get("id") or [""])[0]
        if kind not in {"asset", "queue"} or not identifier:
            raise AVDSError("VALIDATION_FAILED", "媒体参数不合法")
        command, key = ("asset.preview", "asset_id") if kind == "asset" else ("queue.preview", "queue_item_id")
        result = self.server.dispatch({"command": command, key: identifier}, "web")
        body = Path(result["content_path"]).read_bytes()
        if "sha256:" + hashlib.sha256(body).hexdigest() != result["file_hash"]:
            raise AVDSError("HASH_MISMATCH", "媒体指纹异常")
        self.send_response(HTTPStatus.OK); self._security_headers(result["mime_type"])
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        if not self._authorized():
            self._error(HTTPStatus.UNAUTHORIZED, "ACCESS_DENIED", "会话无效"); return
        origins = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
        # CLI uses a bearer credential, browsers must send an exact same-origin Origin.
        origin = self.headers.get("Origin")
        bearer = self.headers.get("Authorization", "").startswith("Bearer ")
        if origin not in origins and (origin is not None or not bearer):
            self._error(HTTPStatus.FORBIDDEN, "ACCESS_DENIED", "来源不可信"); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.headers.get("Transfer-Encoding"):
                raise AVDSError("VALIDATION_FAILED", "不支持分块请求")
            if self.path == "/api/import":
                if not 0 < length <= 512 * 1024 * 1024:
                    raise AVDSError("RESOURCE_LIMIT", "单张图片上限为 512 MiB")
                self._upload(length); return
            if self.path != "/api/command":
                self.send_error(HTTPStatus.NOT_FOUND); return
            if not 0 < length <= 2 * 1024 * 1024:
                raise AVDSError("RESOURCE_LIMIT", "命令请求大小不合法")
            payload = json.loads(self.rfile.read(length))
            self._json(HTTPStatus.OK, {"ok": True, "result": self.server.dispatch(payload, "agent" if bearer else "web")})
        except AVDSError as exc:
            self._json(HTTPStatus.CONFLICT, exc.as_dict())
        except (ValueError, TypeError, KeyError):
            self._error(HTTPStatus.BAD_REQUEST, "VALIDATION_FAILED", "请求内容不合法，请检查字段与 JSON 格式")
        except (OSError, TimeoutError):
            self._error(HTTPStatus.SERVICE_UNAVAILABLE, "STORAGE_UNAVAILABLE", "读取或存储失败，原有资料保留")
        except Exception:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "操作失败，请检查服务终端与请求内容")

    def _upload(self, length):
        directory = self.server.store.staging / ".uploads"
        directory.mkdir(exist_ok=True)
        temporary = None
        stable = None
        try:
            with tempfile.NamedTemporaryFile(dir=directory, delete=False) as stream:
                temporary = Path(stream.name)
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise AVDSError("VALIDATION_FAILED", "图片上传中断")
                    stream.write(chunk); remaining -= len(chunk)
            name = urllib.parse.unquote(self.headers.get("X-File-Name", "image"))
            operation_id = self.headers.get("X-Operation-Id") or new_id("upload")
            stable = directory / (hashlib.sha256(operation_id.encode()).hexdigest() + ".upload")
            temporary.replace(stable)
            temporary = None
            result = self.server.dispatch({"command": "import.stage", "operation_id": operation_id,
                "batch_id": self.headers.get("X-Batch-Id") or new_id("batch"), "source_path": str(stable),
                "source": {"original_name": name}}, "web")
            self._json(HTTPStatus.OK, {"ok": True, "result": result})
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
            if stable:
                stable.unlink(missing_ok=True)

    def log_message(self, format, *args):
        # Session tokens and local paths must not enter HTTP access logs.
        pass


def main():
    # Compatibility launcher: opens the existing single service, never a second process.
    from .cli import main as cli_main
    import sys
    cli_main(["open", *sys.argv[1:]])


if __name__ == "__main__":
    main()
