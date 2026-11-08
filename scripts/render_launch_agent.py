import plistlib
import sys
from pathlib import Path

runtime, vault, reviewer, reviewer_hash, socket_path, output = sys.argv[1:]
value = {
    "Label": "local.avds.core",
    "ProgramArguments": [
        "/usr/bin/python3", "-m", "avds.server", "--vault", vault, "--socket", socket_path,
        "--reviewer-path", reviewer, "--reviewer-hash", reviewer_hash,
    ],
    "EnvironmentVariables": {"PYTHONPATH": str(Path(runtime) / "src")},
    "RunAtLoad": True,
    "KeepAlive": True,
    "ProcessType": "Interactive",
    "StandardOutPath": str(Path(runtime) / "logs" / "core.stdout.log"),
    "StandardErrorPath": str(Path(runtime) / "logs" / "core.stderr.log"),
}
with open(output, "wb") as stream:
    plistlib.dump(value, stream, sort_keys=True)
