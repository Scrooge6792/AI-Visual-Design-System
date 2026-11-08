"""Optional operating-system capabilities; the HTTP service has no OS-specific imports."""
from __future__ import annotations

import json
import os
import platform
import stat
import subprocess
from pathlib import Path


def readonly(path: Path):
    # Windows' read-only bit also prevents os.replace/unlink during recovery.
    # Integrity is enforced by hashes on every platform, not by this advisory flag.
    if platform.system() != "Windows":
        path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def sync_directory(path: Path):
    # Python cannot portably fsync a directory handle on Windows. File fsync,
    # same-volume replace and the operation recovery log remain in force there.
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def inspect_native(path: Path) -> tuple[str, int, int]:
    system = platform.system()
    if system == "Darwin":
        result = subprocess.run(["/usr/bin/sips", "-g", "format", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
                                capture_output=True, text=True, timeout=20)
        if result.returncode:
            raise ValueError("系统图像解码失败")
        values = dict(line.strip().split(": ", 1) for line in result.stdout.splitlines() if ": " in line)
        return values.get("format", "").lower(), int(values["pixelWidth"]), int(values["pixelHeight"])
    if system == "Windows":
        # Pass the path via an environment variable, never interpolate file names
        # into PowerShell source. System.Drawing ships with Windows PowerShell.
        script = """$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$stream=[System.IO.File]::OpenRead($env:AVDS_INSPECT_PATH)
try {
 $image=[System.Drawing.Image]::FromStream($stream,$false,$true)
 try {
  $format=if($image.RawFormat.Guid -eq [System.Drawing.Imaging.ImageFormat]::Png.Guid){'png'}elseif($image.RawFormat.Guid -eq [System.Drawing.Imaging.ImageFormat]::Jpeg.Guid){'jpeg'}else{'unsupported'}
  if([long]$image.Width*$image.Height -gt 100000000){throw 'Pixel limit exceeded'}
  @{format=$format;width=$image.Width;height=$image.Height}|ConvertTo-Json -Compress
 } finally {$image.Dispose()}
} finally {$stream.Dispose()}
"""
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                                env={**os.environ, "AVDS_INSPECT_PATH": str(path)}, capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise ValueError("Windows 原生解码失败；请使用有效的 PNG/JPEG 图片")
        values = json.loads(result.stdout.lstrip("\ufeff"))
        return values["format"], int(values["width"]), int(values["height"])
    raise ValueError("当前平台没有配置图像解码器；支持 macOS 与 Windows 10/11")


def visual_capability(provider: str, helper: Path) -> dict:
    available = provider != "none" and platform.system() == "Darwin" and helper.is_file()
    reason = "" if available else ("Windows 不提供 Apple Vision" if platform.system() == "Windows" else
                                 "已禁用视觉相似检索" if provider == "none" else "Apple Vision helper 未构建")
    return {"provider": "apple-vision" if available else "none", "available": available, "reason": reason}


def os_build() -> str:
    return platform.mac_ver()[0] + ":" + platform.release()
