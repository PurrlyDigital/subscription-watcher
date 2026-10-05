"""Offline checks for the systemd unit generator; every write goes to a temp HOME."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import make_systemd_timer as timer

REPO = Path(__file__).resolve().parent
SCRIPT = REPO / "usage.py"
PYTHON = "/opt/example/bin/python3"
HERDR = "/opt/example/bin/herdr"


class SystemdTimerTests(unittest.TestCase):
    def setUp(self):
        # main() sets umask 077 in-process; restore the caller's umask afterwards.
        old = os.umask(0o077)
        self.addCleanup(os.umask, old)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.units = self.home / ".config/systemd/user"

    def run_main(self, home=None, python=PYTHON, herdr=HERDR):
        home = home or self.home
        with patch.object(Path, "home", return_value=home), \
                patch.dict(os.environ, {"HOME": str(home)}), \
                patch.object(timer.shutil, "which", return_value=herdr), \
                patch.object(timer.sys, "executable", python), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            timer.main()
        return out.getvalue()

    def test_exact_units(self):
        before = sorted(os.listdir(REPO))
        out = self.run_main()
        self.assertEqual(out, "Local systemd user timer generated; see README to enable it.\n")
        self.assertEqual((self.units / "subscription-usage.service").read_text(encoding="utf-8"), (
            "[Unit]\n"
            "Description=Refresh Herdr subscription usage\n"
            "\n"
            "[Service]\n"
            "Type=oneshot\n"
            'ExecStart="' + PYTHON + '" "' + str(SCRIPT) + '" --refresh\n'
            'Environment="HERDR_BIN_PATH=' + HERDR + '"\n'
            'Environment="HERDR_SOCKET_PATH=' + str(self.home / ".config/herdr/herdr.sock") + '"\n'
        ))
        self.assertEqual((self.units / "subscription-usage.timer").read_text(encoding="utf-8"), (
            "[Unit]\n"
            "Description=Refresh Herdr subscription usage hourly\n"
            "\n"
            "[Timer]\n"
            "OnStartupSec=2min\n"
            "OnUnitActiveSec=1h\n"
            "Unit=subscription-usage.service\n"
            "\n"
            "[Install]\n"
            "WantedBy=timers.target\n"
        ))
        # Only the two units exist (no stray temp files), and nothing landed in the repo.
        written = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(written, ["home/.config/systemd/user/subscription-usage.service",
                                   "home/.config/systemd/user/subscription-usage.timer"])
        self.assertEqual(sorted(os.listdir(REPO)), before)

    def test_file_modes_and_rerun(self):
        self.run_main()
        self.run_main()
        for name in ("subscription-usage.service", "subscription-usage.timer"):
            self.assertEqual((self.units / name).stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(list(self.units.iterdir())), 2)

    def test_herdr_fallback_path(self):
        self.run_main(herdr=None)
        text = (self.units / "subscription-usage.service").read_text(encoding="utf-8")
        self.assertIn('Environment="HERDR_BIN_PATH=' + str(self.home / ".local/bin/herdr") + '"\n', text)

    def test_paths_with_spaces_are_quoted(self):
        home = self.root / "home dir"
        home.mkdir()
        self.run_main(home=home, python="/opt/my python/bin/python3", herdr="/opt/herdr tools/herdr")
        text = (home / ".config/systemd/user/subscription-usage.service").read_text(encoding="utf-8")
        self.assertIn('ExecStart="/opt/my python/bin/python3" "' + str(SCRIPT) + '" --refresh\n', text)
        self.assertIn('Environment="HERDR_BIN_PATH=/opt/herdr tools/herdr"\n', text)
        self.assertIn('Environment="HERDR_SOCKET_PATH=' + str(home / ".config/herdr/herdr.sock") + '"\n', text)

    def test_rejects_unsafe_values(self):
        bad = ("%", "$", "${HOME}", '"', "'", "\\", "\n", "\r", "\t", "\x00", "\x1b", "\x7f",
               "\x85", " ", " ")
        for char in bad:
            with self.subTest(char=repr(char)):
                with self.assertRaises(ValueError):
                    timer.safe("/opt/ex" + char + "ample")
                for field in ("python", "herdr"):
                    with self.assertRaises(ValueError):
                        self.run_main(**{field: "/opt/ex" + char + "ample/bin"})
                home = self.root / "unsafe"
                with self.assertRaises(ValueError):
                    self.run_main(home=Path(str(home) + char))
        for value in ("", "bin/python3", "./python3", "~/python3"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    timer.safe(value)
                with self.assertRaises(ValueError):
                    self.run_main(python=value)
        # Validation happens before any directory or file is created.
        self.assertEqual(list(self.root.rglob("*")), [self.home])

    def test_refuses_symlinked_unit_file(self):
        self.units.mkdir(parents=True)
        outside = self.root / "outside.txt"
        outside.write_text("keep\n", encoding="utf-8")
        for name in ("subscription-usage.service", "subscription-usage.timer"):
            with self.subTest(name=name):
                link = self.units / name
                link.symlink_to(outside)
                with self.assertRaises(OSError):
                    self.run_main()
                self.assertTrue(link.is_symlink())
                self.assertEqual(outside.read_text(encoding="utf-8"), "keep\n")
                self.assertEqual(list(self.units.iterdir()), [link])
                link.unlink()

    def test_refuses_symlinked_units_directory(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        self.units.parent.mkdir(parents=True)
        self.units.symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaises(OSError):
            self.run_main()
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_cli_error_is_generic(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        self.units.parent.mkdir(parents=True)
        self.units.symlink_to(elsewhere, target_is_directory=True)
        env = {"HOME": str(self.home), "PATH": "/usr/bin:/bin"}
        result = subprocess.run([sys.executable, str(REPO / "make_systemd_timer.py")], env=env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "Could not generate systemd timer; check local setup.\n")
        self.assertEqual(list(elsewhere.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
