#!/usr/bin/python3
"""Generate a local hourly systemd user timer; does not run systemctl."""
import os
from pathlib import Path
import shutil
import sys
import tempfile

NAME = "subscription-usage"
# systemd expands %specifiers and $VARs and interprets quotes and backslashes,
# even inside double quotes; only plain absolute paths are interpolated.
UNSAFE = frozenset("%$\"'\\")


def safe(value):
    value = str(value)
    # isprintable() rejects control, line-break, and non-ASCII-space characters.
    if not os.path.isabs(value) or not value.isprintable() or UNSAFE.intersection(value):
        raise ValueError("unsafe value for systemd unit")
    return value


def service_text(python, script, binary, socket):
    # Double-quote each value so paths with spaces stay one word (systemd.syntax(7)).
    return (
        "[Unit]\n"
        "Description=Refresh Herdr subscription usage\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        'ExecStart="{}" "{}" --refresh\n'
        'Environment="HERDR_BIN_PATH={}"\n'
        'Environment="HERDR_SOCKET_PATH={}"\n'
    ).format(safe(python), safe(script), safe(binary), safe(socket))


def timer_text():
    return (
        "[Unit]\n"
        "Description=Refresh Herdr subscription usage hourly\n"
        "\n"
        "[Timer]\n"
        "OnStartupSec=2min\n"
        "OnUnitActiveSec=1h\n"
        "Unit={0}.service\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    ).format(NAME)


def write(target, text):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=".subscription-", delete=False) as file:
            temp = Path(file.name)
            os.fchmod(file.fileno(), 0o600)
            file.write(text)
        temp.replace(target)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def main():
    os.umask(0o077)
    home = Path.home()
    script = Path(__file__).resolve().with_name("usage.py")
    binary = shutil.which("herdr") or str(home / ".local/bin/herdr")
    # Validate everything before touching the filesystem.
    units = {
        NAME + ".service": service_text(sys.executable, script, binary,
                                        home / ".config/herdr/herdr.sock"),
        NAME + ".timer": timer_text(),
    }
    directory = home / ".config/systemd/user"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink() or not directory.is_dir():
        raise OSError("unsafe units directory")
    targets = {directory / name: text for name, text in units.items()}
    for target in targets:
        if target.is_symlink():
            raise OSError("unsafe unit file")
    for target, text in targets.items():
        write(target, text)
    print("Local systemd user timer generated; see README to enable it.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Could not generate systemd timer; check local setup.", file=sys.stderr)
        sys.exit(1)
