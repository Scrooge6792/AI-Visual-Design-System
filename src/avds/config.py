from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def default_config_path() -> Path:
    return Path.home() / ".avds" / "config.json"


@dataclass
class Config:
    vault: str = str(Path.home() / "Pictures" / "VisualAssetVault")
    host: str = "127.0.0.1"
    port: int = 8765
    open_browser: bool = False
    visual_provider: str = "auto"

    @property
    def root(self):
        return Path(self.vault).expanduser().resolve()

    @property
    def state_path(self):
        return self.root / "data" / "service.json"


def load_config(args=None) -> Config:
    args = vars(args) if args is not None else {}
    config_path = Path(args.get("config") or os.environ.get("AVDS_CONFIG") or default_config_path()).expanduser()
    values = {}
    if config_path.exists():
        values = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(values, dict) or set(values) - set(Config.__dataclass_fields__):
            raise ValueError("配置文件包含未知字段")
    for key in Config.__dataclass_fields__:
        env = os.environ.get("AVDS_" + key.upper())
        if env is not None:
            values[key] = env
        if args.get(key) is not None:
            values[key] = args[key]
    config = Config(**values)
    config.port = int(config.port)
    if not 0 <= config.port <= 65535:
        raise ValueError("端口应为 0～65535，0 表示由系统分配")
    if config.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("仅允许 127.0.0.1 或 localhost 本机监听")
    if isinstance(config.open_browser, str):
        if config.open_browser.lower() not in {"true", "false", "1", "0"}:
            raise ValueError("open_browser 应为 true 或 false")
        config.open_browser = config.open_browser.lower() in {"true", "1"}
    if not isinstance(config.open_browser, bool) or config.visual_provider not in {"auto", "none", "apple-vision"}:
        raise ValueError("配置中的浏览器或视觉能力选项不合法")
    if not isinstance(config.vault, str) or not config.vault.strip():
        raise ValueError("Vault 路径不能为空")
    return config


def add_options(parser):
    parser.add_argument("--config", metavar="PATH", help="使用指定 JSON 配置文件")
    parser.add_argument("--vault", metavar="PATH", help="覆盖当前 Vault 路径")
    parser.add_argument("--host", metavar="HOST", help="本机监听地址：127.0.0.1 或 localhost")
    parser.add_argument("--port", type=int, metavar="PORT", help="覆盖本机服务端口，0 表示自动分配")
    parser.add_argument("--visual-provider", choices=["auto", "none", "apple-vision"], help="选择本机视觉提供者")
    parser.add_argument("--open-browser", "--open", dest="open_browser", action="store_true", default=None,
        help="服务启动后打开 WebUI")
    parser.add_argument("--no-open-browser", dest="open_browser", action="store_false", help="服务启动后不打开浏览器")


class VaultLock:
    """An OS-held lock, automatically released after a crash; never unlink it."""
    def __init__(self, root: Path):
        self.path = root / "data" / "service.lock"
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0)
                self.file.write(b"\0"); self.file.flush(); self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.file.close(); self.file = None
            raise ValueError("同一 Vault 已有服务运行，请使用 avds status/open 或选择其他 Vault") from exc

    def close(self):
        if self.file:
            self.file.close(); self.file = None
