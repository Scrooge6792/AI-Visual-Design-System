from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .platform import inspect_native

SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
FACETS = {
    "work_type", "subject", "scene", "style", "technique", "composition",
    "lighting", "color", "material", "pose_action", "mood", "usage",
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def canonical_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest_json(value) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def safe_relative(root: Path, relative: str) -> Path:
    if not relative or os.path.isabs(relative):
        raise ValueError("路径必须是 Vault 内相对路径")
    candidate = root / relative
    resolved_root = root.resolve()
    resolved_parent = candidate.parent.resolve()
    if resolved_parent != resolved_root and resolved_root not in resolved_parent.parents:
        raise ValueError("路径越出 Vault")
    if candidate.is_symlink():
        raise ValueError("不允许符号链接")
    return candidate


def inspect_image(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("来源必须是普通文件且不能是符号链接")
    size = path.stat().st_size
    if size <= 0 or size > 512 * 1024 * 1024:
        raise ValueError("文件体积超限")
    image_format, width, height = inspect_native(path)
    allowed = {"png": "image/png", "jpeg": "image/jpeg", "heic": "image/heic", "webp": "image/webp"}
    if image_format not in allowed:
        raise ValueError(f"不支持的图像格式：{image_format or 'unknown'}")
    if width <= 0 or height <= 0 or width * height > 100_000_000:
        raise ValueError("图像像素数超限")
    size = path.stat().st_size
    if size <= 0 or size > 512 * 1024 * 1024:
        raise ValueError("文件体积超限")
    return {"format": image_format, "mime_type": allowed[image_format], "width": width, "height": height, "size": size}
