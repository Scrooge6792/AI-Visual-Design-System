from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path


def request(socket_path: str, value: dict):
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(socket_path)
    with client:
        client.sendall(json.dumps(value, ensure_ascii=False).encode() + b"\n")
        data = b""
        while not data.endswith(b"\n"):
            chunk = client.recv(65536)
            if not chunk: break
            data += chunk
    return json.loads(data)


def main():
    parser = argparse.ArgumentParser(prog="avds", description="AI Visual Design System V1 Agent CLI")
    parser.add_argument("--socket", default=str(Path.home() / "Library/Application Support/AIVisualDesign/core.sock"))
    parser.add_argument("command")
    parser.add_argument("--json", default="{}", help="JSON object payload")
    args = parser.parse_args()
    try:
        payload = json.loads(args.json)
        if not isinstance(payload, dict): raise ValueError("payload must be object")
        payload["command"] = args.command
        result = request(args.socket, payload)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result.get("ok") else 2)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": {"code": "CLIENT_ERROR", "message": str(exc)}}, ensure_ascii=False, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
