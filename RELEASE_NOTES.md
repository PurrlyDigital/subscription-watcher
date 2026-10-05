# v0.1.2

- The plugin runs on Linux, including WSL2 on Windows. Native Windows is not supported.
- `make_systemd_timer.py` generates an hourly systemd user timer. Without systemd, the README shows a cron line.
- On Linux, the plugin reads Claude Code credentials from `~/.claude/.credentials.json`. It reads the Keychain only on macOS.
- Allowance rows put a space after `↻`, as in `↻ 7:30 PM`, so the symbol no longer runs into the reset time in Windows Terminal.
- The README has a new Update section and steps for each operating system.
- The release ZIP extracts into a `subscription-watcher/` folder, so a new release extracts over the old install.
