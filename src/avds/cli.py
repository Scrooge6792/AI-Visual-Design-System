from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import sys
import urllib.error
import urllib.request
import webbrowser
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .commands import LOCAL_COMMAND_DESCRIPTIONS, REMOTE_COMMAND_DESCRIPTIONS
from .config import Config, VaultLock, add_options, default_config_path, load_config


def _help_epilog():
    def section(title, commands):
        width = max(len(command) for command in commands)
        lines = [title]
        lines.extend(f"  {command:<{width}}  {description}" for command, description in commands.items())
        return "\n".join(lines)

    return "\n\n".join((
        section("生命周期与发现命令：", LOCAL_COMMAND_DESCRIPTIONS),
        section("业务命令：", REMOTE_COMMAND_DESCRIPTIONS),
        "业务命令通过 --json JSON 或 --json-file PATH 接收参数；具体字段见 docs/CONTRACTS.md。",
    ))


def request(config: Config, value: dict):
    state = json.loads(config.state_path.read_text(encoding="utf-8"))
    from urllib.parse import urlparse
    parsed = urlparse(state["url"])
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.path:
        raise ValueError("服务地址必须是本机 HTTP 地址")
    req = urllib.request.Request(state["url"] + "/api/command", data=json.dumps(value, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + state["token"]}, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=180) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        with exc:
            return json.load(exc)


def doctor(config):
    from .platform import visual_capability
    import os
    root = Path(__file__).resolve().parents[2]
    helper = Path(os.environ.get("AVDS_VISION_HELPER", root / ".build" / "avds-vision"))
    db = sqlite3.connect(":memory:")
    try:
        db.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
        fts = True
    except sqlite3.DatabaseError:
        fts = False
    finally:
        db.close()
    return {"version": __version__, "platform": platform.system(), "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
        "fts5": fts, "config": asdict(config), "visual": visual_capability(config.visual_provider, helper),
        "image_formats": ["png", "jpeg", "heic", "webp"] if platform.system() == "Darwin" else ["png", "jpeg"],
        "review_identity_isolated": False}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="avds",
        description="启动和操作本机 Visual Design System；Agent 与 WebUI 共用同一服务。",
        epilog=_help_epilog(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser._positionals.title = "位置参数"
    parser._optionals.title = "公共参数"
    parser.add_argument("-h", "--help", action="help", help="显示全部命令、参数和用途后退出")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}", help="显示版本号后退出")
    parser.add_argument("command", help="要执行的命令；完整列表见下方")
    add_options(parser)
    parser.add_argument("--json", default="{}", metavar="JSON", help="业务命令的 JSON 对象，默认为 {}")
    parser.add_argument("--json-file", metavar="PATH", help="从 UTF-8 文件读取业务参数，适合多行内容和 PowerShell")
    args = parser.parse_args(argv)
    try:
        config = load_config(args)
        if args.command == "serve":
            from .server import serve
            serve(config); return
        if args.command == "init":
            import os
            config_path = Path(args.config or os.environ.get("AVDS_CONFIG") or default_config_path()).expanduser()
            if config_path.exists():
                raise ValueError("配置已存在；请编辑文件或使用启动参数覆盖，不会覆盖原配置")
            lock = VaultLock(config.root); lock.acquire()
            try:
                from .store import Store
                store = Store(config.root, config.visual_provider); store.close()
                config_path.parent.mkdir(parents=True, exist_ok=True)
                config_path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
            finally:
                lock.close()
            result = {"ok": True, "result": {"config": str(config_path), "vault": str(config.root)}}
        elif args.command == "doctor":
            result = {"ok": True, "result": doctor(config)}
            if not result["result"]["fts5"]:
                result["ok"] = False
        else:
            payload = json.loads(Path(args.json_file).read_text(encoding="utf-8-sig") if args.json_file else args.json)
            if not isinstance(payload, dict):
                raise ValueError("载荷必须是 JSON 对象")
            payload["command"] = {"open": "service.open", "stop": "service.stop"}.get(args.command, args.command)
            result = request(config, payload)
            if args.command == "open" and result.get("ok"):
                webbrowser.open(result["result"]["url"])
                result["result"] = {"opened": True}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok"):
            raise SystemExit(2)
    except (OSError, ValueError, TypeError, sqlite3.DatabaseError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "CLIENT_ERROR", "message": str(exc)}}, ensure_ascii=False, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
