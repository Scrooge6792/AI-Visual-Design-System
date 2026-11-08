from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .cli import main as full_main
from .config import Config, default_config_path, load_config, validate_config


CONFIG_KEYS = tuple(Config.__dataclass_fields__)


class ChineseArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "位置参数"
        self._optionals.title = "选项"
        self.add_argument("-h", "--help", action="help", help="显示本级命令和参数后退出")


def _parser():
    parser = ChineseArgumentParser(
        prog="avds",
        description="启动 Visual Design System，并查看或修改当前用户配置。",
        epilog=(
            "查看某个命令的参数：\n"
            "  avds serve -h\n"
            "  avds status -h\n"
            "  avds config -h"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}", help="显示版本号后退出")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)

    serve = commands.add_parser("serve", help="启动唯一的本机服务。", description="启动唯一的本机服务。")
    browser = serve.add_mutually_exclusive_group()
    browser.add_argument("--open", "--open-browser", dest="open_browser", action="store_true",
        help="启动后打开 WebUI")
    browser.add_argument("--no-open", "--no-open-browser", dest="open_browser", action="store_false",
        help="启动后不打开浏览器")
    serve.set_defaults(open_browser=None)

    commands.add_parser("status", help="查看当前服务状态、端口和 Vault。",
        description="查看当前服务状态、端口和 Vault。")

    config = commands.add_parser(
        "config",
        help="打印或修改当前用户的应用配置。",
        description="打印或修改当前用户的应用配置。",
        epilog=(
            "查看某个配置动作的参数：\n"
            "  avds config show -h\n"
            "  avds config get -h\n"
            "  avds config set -h"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    actions = config.add_subparsers(dest="config_action", metavar="ACTION", required=True)
    actions.add_parser("show", help="打印配置文件位置和全部生效配置。")
    get = actions.add_parser("get", help="打印指定配置项的当前值。")
    get.add_argument("key", choices=CONFIG_KEYS, help="配置项名称")
    set_value = actions.add_parser("set", help="设置一个用户配置项。")
    set_value.add_argument("key", choices=CONFIG_KEYS, help="配置项名称")
    set_value.add_argument("value", help="要保存的配置值")
    return parser


def _config_path():
    return Path(os.environ.get("AVDS_CONFIG") or default_config_path()).expanduser()


def _stored_values(path: Path):
    if not path.exists():
        return {}
    values = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, dict) or set(values) - set(CONFIG_KEYS):
        raise ValueError("配置文件包含未知字段")
    return values


def _parse_value(key: str, value: str):
    if key == "port":
        return int(value)
    if key == "open_browser":
        normalized = value.strip().lower()
        if normalized not in {"true", "false", "1", "0"}:
            raise ValueError("open_browser 只接受 true/false/1/0")
        return normalized in {"true", "1"}
    return value


def _show_config():
    config = load_config()
    return {"config_file": str(_config_path()), "values": asdict(config)}


def _set_config(key: str, raw_value: str):
    path = _config_path()
    stored = _stored_values(path)
    stored[key] = _parse_value(key, raw_value)
    merged = asdict(Config())
    merged.update(stored)
    validated = validate_config(Config(**merged))
    stored[key] = getattr(validated, key)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(stored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return {"config_file": str(path), "key": key, "value": stored[key]}


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "serve":
        forwarded = ["serve"]
        if args.open_browser is True:
            forwarded.append("--open")
        elif args.open_browser is False:
            forwarded.append("--no-open-browser")
        return full_main(forwarded)
    if args.command == "status":
        return full_main(["status"])
    try:
        if args.config_action == "show":
            result = _show_config()
        elif args.config_action == "get":
            shown = _show_config()
            result = {"config_file": shown["config_file"], "key": args.key, "value": shown["values"][args.key]}
        else:
            result = _set_config(args.key, args.value)
        print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, json.JSONDecodeError, sqlite3.DatabaseError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "CLIENT_ERROR", "message": str(exc)}}, ensure_ascii=False, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
