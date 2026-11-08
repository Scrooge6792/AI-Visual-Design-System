from __future__ import annotations

import json
import os
import secrets
import socketserver
import threading
import webbrowser
from http.server import HTTPServer

from . import __version__
from .commands import REMOTE_COMMAND_DESCRIPTIONS
from .config import Config, VaultLock
from .errors import AVDSError
from .platform import visual_capability
from .store import Store
from .web import Handler

COMMANDS = tuple(REMOTE_COMMAND_DESCRIPTIONS)


class Server(HTTPServer):
    """Serial requests: a single Store owns writes and SQLite transactions."""
    allow_reuse_address = False

    def server_bind(self):
        # HTTPServer normally performs reverse DNS here. A local-only service
        # should start without any DNS/network dependency or lookup timeout.
        socketserver.TCPServer.server_bind(self)
        self.server_name = self.config.host
        self.server_port = self.socket.getsockname()[1]

    def __init__(self, config: Config):
        self.config = config
        self.lock = VaultLock(config.root)
        self.lock.acquire()
        self.store = None
        self.token = secrets.token_urlsafe(32)
        self.closed = False
        try:
            self.store = Store(config.root, config.visual_provider)
            super().__init__((config.host, config.port), Handler)
            self.url = f"http://{config.host}:{self.server_port}"
            self.session_url = f"{self.url}/session?token={self.token}"
            self.state = {"url": self.url, "token": self.token, "pid": os.getpid(), "vault": str(config.root)}
            temporary = config.state_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.state), encoding="utf-8")
            temporary.replace(config.state_path)
        except Exception:
            if self.store:
                self.store.close()
            self.lock.close()
            raise

    def server_close(self):
        if self.closed:
            return
        self.closed = True
        super().server_close()
        try:
            self.config.state_path.unlink(missing_ok=True)
            if self.store:
                self.store.close()
        finally:
            self.lock.close()

    def dispatch(self, req: dict, source="agent"):
        if not isinstance(req, dict) or not isinstance(req.get("command"), str):
            raise AVDSError("VALIDATION_FAILED", "命令必须是 JSON 对象且包含 command")
        command = req["command"]
        if command == "service.stop":
            threading.Thread(target=self.shutdown, daemon=True).start()
            return {"stopping": True}
        if command == "service.open":
            return {"url": self.session_url}
        if command == "commands":
            return {"commands": list(COMMANDS)}
        if command == "review.action":
            if req.get("confirmed") is not True:
                raise AVDSError("CONFIRMATION_REQUIRED", "请先展示最终提案并明确确认，再传入 confirmed=true；此字段不是身份认证")
            if not isinstance(req.get("operation_id"), str) or not req["operation_id"]:
                raise AVDSError("VALIDATION_FAILED", "审核动作缺少 operation_id")
            if req.get("action") not in {"defer_current", "defer_remaining_batch"}:
                if not isinstance(req.get("revision"), int) or isinstance(req.get("revision"), bool):
                    raise AVDSError("VALIDATION_FAILED", "审核动作必须绑定具体 revision")
                proposal = self.store.proposal_get(req.get("proposal_id", ""), req["revision"])
                for key in ("proposal_hash", "target_revision"):
                    if key not in req or req[key] != proposal[key]:
                        raise AVDSError("STALE_PROPOSAL", f"审核绑定不一致：{key}")
                if proposal["file_hash"] and req.get("file_hash") != proposal["file_hash"]:
                    raise AVDSError("HASH_MISMATCH", "审核文件指纹不一致")
        routes = {
            "status": lambda: {**self.store.status(), "service": {"version": __version__, "url": self.url, "vault": str(self.config.root),
                "review_identity_isolated": False, "visual": visual_capability(self.config.visual_provider, self.store.vision_helper)}},
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
            "review.action": lambda: self.store.review_action(req, source),
        }
        if command in {"asset.delete", "concept.update", "concept.merge", "approval.record", "commit.execute"}:
            raise AVDSError("OPERATION_NOT_SUPPORTED", "不提供该公开操作")
        if command not in routes:
            raise AVDSError("VALIDATION_FAILED", "未知命令")
        return routes[command]()


def serve(config: Config):
    server = Server(config)
    print(json.dumps({"ok": True, "url": server.url, "vault": str(config.root)}, ensure_ascii=False), flush=True)
    if config.open_browser:
        webbrowser.open(server.session_url)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main():
    from .cli import main as cli_main
    cli_main(["serve", *os.sys.argv[1:]])


if __name__ == "__main__":
    main()
