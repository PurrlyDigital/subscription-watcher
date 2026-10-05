# Changelog

## 0.2.0

- Added Linux support, including WSL2 on Windows. The manifest declares the `linux` and `macos` platforms.
- Added `make_systemd_timer.py`, which writes an hourly systemd user service and timer. It does not run `systemctl`.
- Added a space after `↻` in allowance rows, as in `↻ 7:30 PM`, so the symbol no longer runs into the reset time in Windows Terminal.
- Limited the Claude Code Keychain fallback to macOS. On Linux, the plugin reads `~/.claude/.credentials.json`, or `.credentials.json` in `$CLAUDE_CONFIG_DIR`.
- Added Linux, WSL2, cron, update, and removal steps to the README.
- Added an install step that runs the refresh action after linking, because linking does not run the startup hook.
- Added Linux and systemd notes to the security review.
- Included the systemd generator and its tests in the distribution ZIP.
- Changed the distribution ZIP to extract into a `subscription-watcher/` folder without a version, so a new release extracts over the old install. The ZIP file name keeps the version.

## 0.1.1

- Changed refresh and reset times to a 12-hour clock with AM and PM.
- Moved the last refresh time into the Subscriptions header, replacing the separate Updated row.
- Updated the sidebar configuration example for longer reset times.
- Shortened the README and updated its screenshot.
- Included release notes in the distribution ZIP.

## 0.1.0

Initial release.

- Added Claude Code and Codex allowance rows to the Herdr sidebar.
- Added hourly refreshes through a macOS LaunchAgent and a manual refresh action.
- Displayed remaining percentages and local reset times.
- Stored normalized usage data in a private cache. Blocked HTTP redirects and kept credentials out of logs and cached data.
- Added setup documentation, a sidebar configuration example, tests, and a screenshot.
- Added the MIT license and versioned ZIP packaging with SHA-256 checksums.
