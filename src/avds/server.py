from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import signal
import socket
import socketserver
from pathlib import Path

from .errors import AVDSError
from .store import Store

SOL_LOCAL = 0
LOCAL_PEERPID = 2


def peer_path(sock: socket.socket) -> str:
    raw = sock.getsockopt(SOL_LOCAL, LOCAL_PEERPID, 4)
    pid = int.from_bytes(raw, byteorder=os.sys.byteorder, signed=True)
    libproc = ctypes.CDLL("/usr/lib/libproc.dylib")
    buffer = ctypes.create_string_buffer(4096)
    if libproc.proc_pidpath(pid, buffer, len(buffer)) <= 0:
        return "unknown"
    return buffer.value.decode()


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        executable = peer_path(self.request)
        for raw in self.rfile:
            request = None
            try:
                request = json.loads(raw)
                response = self.server.dispatch(request, executable)
                value = {"ok": True, "result": response}
            except AVDSError as exc:
                value = exc.as_dict(request.get("operation_id") if isinstance(request, dict) else None)
            except Exception as exc:
                value = AVDSError("INTERNAL_ERROR", str(exc)).as_dict()
            self.wfile.write(json.dumps(value, ensure_ascii=False).encode() + b"\n")


class Server(socketserver.UnixStreamServer):
    allow_reuse_address = True

    def __init__(self, socket_path: Path, store: Store, reviewer_path: str, reviewer_hash: str):
        self.socket_path = socket_path
        self.store = store
        self.reviewer_path = str(Path(reviewer_path).resolve()) if reviewer_path else ""
        self.reviewer_hash = reviewer_hash
        socket_path.parent.mkdir(parents=True, exist_ok=True)
        socket_path.unlink(missing_ok=True)
        super().__init__(str(socket_path), RequestHandler)
        os.chmod(socket_path, 0o600)

    def server_close(self):
        super().server_close(); self.socket_path.unlink(missing_ok=True); self.store.close()

    def trusted_reviewer(self, executable: str) -> bool:
        try:
            return (str(Path(executable).resolve()) == self.reviewer_path and
                    sha256_file(executable) == self.reviewer_hash)
        except OSError:
            return False

    def dispatch(self, req: dict, executable: str):
        command = req.get("command")
        reviewer_commands = {"review.list", "review.get", "review.action"}
        if command in reviewer_commands and not self.trusted_reviewer(executable):
            raise AVDSError("UNAUTHORIZED_REVIEW", "仅安装后的受信 Reviewer 可执行审核动作")
        routes = {
            "status": lambda: self.store.status(),
            "import.stage": lambda: self.store.stage(req),
            "queue.get": lambda: self.store.queue_get(req.get("queue_item_id", "")),
            "queue.preview": lambda: self.store.queue_preview(req.get("queue_item_id", "")),
            "search.pending": lambda: self.store.pending(req),
            "analysis.record": lambda: self.store.record_analysis(req),
            "proposal.create": lambda: self.store.create_proposal(req),
            "proposal.revise": lambda: self.store.create_proposal(req),
            "proposal.get": lambda: self.store.proposal_get(req.get("proposal_id", ""), req.get("revision")),
            "candidate.get": lambda: self.store.candidate_get(req.get("candidate_id", "")),
            "asset.get": lambda: self.store.asset_get(req.get("asset_id", "")),
            "asset.preview": lambda: self.store.asset_preview(req.get("asset_id", "")),
            "search.concepts": lambda: self.store.search_concepts(req),
            "search.assets": lambda: self.store.search_assets(req),
            "search.explain": lambda: self.store.search_explain(req),
            "search.related": lambda: self.store.search_related(req),
            "knowledge.get": lambda: self.store.knowledge_get(req.get("knowledge_id", "")),
            "knowledge.search": lambda: self.store.knowledge_search(req),
            "prompt.get": lambda: self.store.prompt_get(req.get("prompt_id", "")),
            "prompt.list": lambda: self.store.prompt_list(req),
            "prompt.render": lambda: self.store.prompt_render(req),
            "visual.index": lambda: self.store.visual_index(req),
            "visual.search": lambda: self.store.visual_search(req),
            "search.rebuild": lambda: self.store.rebuild_index(),
            "operations.recover": lambda: self.store.recover(),
            "review.list": lambda: self.store.review_list(),
            "review.get": lambda: self.store.proposal_get(req.get("proposal_id", ""), req.get("revision")),
            "review.action": lambda: self.store.review_action(req, executable),
        }
        if command in {"asset.delete", "concept.update", "concept.merge"}:
            raise AVDSError("OPERATION_NOT_SUPPORTED", "该操作不属于 V1")
        if command not in routes:
            raise AVDSError("VALIDATION_FAILED", "未知命令")
        return routes[command]()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", required=True)
    parser.add_argument("--socket", required=True)
    parser.add_argument("--reviewer-path", required=True)
    parser.add_argument("--reviewer-hash", required=True)
    args = parser.parse_args()
    server = Server(Path(args.socket), Store(Path(args.vault)), args.reviewer_path, args.reviewer_hash)
    def terminate(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminate)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
