#!/usr/bin/python3
"""Generate a local hourly LaunchAgent; do not commit the generated plist."""
import os
from pathlib import Path
import plistlib
import shutil
import sys
import tempfile

LABEL = "io.herdr.subscription-usage"


def main():
    os.umask(0o077)
    home = Path.home()
    script = Path(__file__).resolve().with_name("usage.py")
    binary = shutil.which("herdr") or str(home / ".local/bin/herdr")
    state = home / ".local/state/herdr/subscription-usage"
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    if state.is_symlink():
        raise OSError("unsafe state directory")
    state.chmod(0o700)
    log = state / "launchd.log"
    fd = os.open(log, os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    config = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(script), "--refresh"],
        "StartInterval": 3600,
        "RunAtLoad": True,
        "ProcessType": "Background",
        "EnvironmentVariables": {
            "HERDR_BIN_PATH": binary,
            "HERDR_SOCKET_PATH": str(home / ".config/herdr/herdr.sock"),
        },
        "StandardOutPath": str(log),
        "StandardErrorPath": str(log),
    }
    agents = home / "Library/LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=agents, prefix=".subscription-", delete=False) as file:
            temp = Path(file.name)
            plistlib.dump(config, file)
        temp.replace(agents / (LABEL + ".plist"))
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    print("Local LaunchAgent generated; see README to load it.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Could not generate LaunchAgent; check local setup.", file=sys.stderr)
        sys.exit(1)
