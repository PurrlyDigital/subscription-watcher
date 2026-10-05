#!/usr/bin/python3
"""Build a versioned ZIP of public files only; no dependencies or network access."""
import hashlib
from pathlib import Path
import re
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
FILES = (
    ".gitignore", "LICENSE", "README.md", "RELEASE_NOTES.md", "SECURITY.md", "herdr-plugin.toml",
    "usage.py", "make_launchagent.py", "build_release.py", "test_usage.py",
    "sidebar.example.toml", "assets/subscription-sidebar.png",
)


def main():
    manifest = (ROOT / "herdr-plugin.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"(\d+\.\d+\.\d+)"\s*$', manifest, re.MULTILINE)
    if not match:
        raise ValueError("expected a three-part manifest version")
    prefix = "subscription-watcher-" + match.group(1)
    # Validate the entire allowlist before writing; never follow a file symlink.
    for name in FILES:
        file = ROOT / name
        if file.is_symlink() or not file.is_file():
            raise ValueError("missing or unsafe release file")
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    if dist.is_symlink():
        raise ValueError("unsafe output directory")
    output = dist / (prefix + ".zip")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=dist, suffix=".zip", delete=False) as file:
            temporary = Path(file.name)
        with zipfile.ZipFile(temporary, "w") as archive:
            for name in FILES:
                # Fixed timestamps and permissions: no workstation path, file
                # ownership, or original modification-time metadata in the ZIP.
                info = zipfile.ZipInfo(prefix + "/" + name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, (ROOT / name).read_bytes(), compress_type=zipfile.ZIP_DEFLATED)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    checksum = output.with_suffix(".zip.sha256")
    checksum.write_text(digest + "  " + output.name + "\n", encoding="ascii")
    print("dist/" + output.name)
    print("dist/" + checksum.name)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Release build failed; check the manifest and public file list.", file=sys.stderr)
        sys.exit(1)
