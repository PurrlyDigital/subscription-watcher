# Changelog

## [0.1.4](https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher/-/releases/v0.1.4)

- Updated the README screenshot for the three-row sidebar.
- Added README steps to install the plugin from the GitHub mirror with `herdr plugin install PurrlyDigital/subscription-watcher`.
- Changed `usage.py --if-stale` to compare the rows with the live Herdr sidebar instead of the text it last published. When the workspace that showed the rows closes, the next event moves them to the new first workspace. Removed the `published` state file.
- Added a `pane.exited` hook. Herdr closes a workspace without a `workspace.closed` event when its last pane exits. `herdr-plugin.toml` changed, so link the plugin again after you update.
- Added the `open Claude Code` status. When the saved Claude Code token has expired, the Claude row shows this status and the plugin sends no request. Before, the request failed and the row said `sign in again`. Only Claude Code renews the token.
- Changed the Claude row to refresh on the next Herdr event after Claude Code saves a new token. Before, `sign in again` stayed for up to an hour after you logged in.

## [0.1.3](https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher/-/releases/v0.1.3)

- Consolidated the sidebar into three rows: `$claude`, `$fable`, and `$codex`. To upgrade, replace the `$claude_5h`, `$claude_week`, `$codex_primary`, and `$codex_secondary` rows in your sidebar config with the rows in `sidebar.example.toml`. The plugin clears the old tokens.
- Added the weekly Fable allowance as its own row, and the number of available Codex rate limit resets to the Codex row.
- Changed reset times to a one-unit countdown, such as `4h` or `4d`. Removed the parentheses around the refresh time in the header.
- Added `usage.py --if-stale`, which runs on focus and agent-status events. It refreshes a stale cache the first time you use Herdr after a detached session or sleep. It also republishes the rows when the countdown text changes.
- Made the hourly LaunchAgent and systemd timer optional.
- Changed the plugin to refresh when a shown allowance passes its reset time, and five minutes after a `usage unavailable` failure, instead of waiting an hour.
- Changed the README to reload the config from inside Herdr with the prefix key and `shift+R`. `herdr server reload-config` does not update the sidebar layout of an open window.
- Added an Update step to merge `sidebar.example.toml` again when it changes.

## [0.1.2](https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher/-/releases/v0.1.2)

- Added Linux support, including WSL2 on Windows. The manifest declares the `linux` and `macos` platforms.
- Added `make_systemd_timer.py`, which writes an hourly systemd user service and timer. It does not run `systemctl`.
- Added a space after `↻` in allowance rows, as in `↻ 7:30 PM`. The symbol no longer runs into the reset time in Windows Terminal.
- Limited the Claude Code Keychain fallback to macOS. On Linux, the plugin reads `~/.claude/.credentials.json`, or `.credentials.json` in `$CLAUDE_CONFIG_DIR`.
- Added Linux, WSL2, cron, update, and removal steps to the README, and removed its explanatory notes.
- Added an install step that runs the refresh action after linking.
- Added Linux and systemd notes to the security review.
- Added this changelog, linked it from the README, and included it in the distribution ZIP.
- Included the systemd generator and its tests in the distribution ZIP.
- Changed the distribution ZIP to extract into a `subscription-watcher/` folder without a version. A new release extracts over the old install. The ZIP file name keeps the version.

## [0.1.1](https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher/-/releases/v0.1.1)

- Changed refresh and reset times to a 12-hour clock with AM and PM.
- Moved the last refresh time into the Subscriptions header, replacing the separate Updated row.
- Updated the sidebar configuration example for longer reset times.
- Shortened the README and updated its screenshot.
- Included release notes in the distribution ZIP.

## [0.1.0](https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher/-/releases/v0.1.0)

Initial release.

- Added Claude Code and Codex allowance rows to the Herdr sidebar.
- Added hourly refreshes through a macOS LaunchAgent and a manual refresh action.
- Displayed remaining percentages and local reset times.
- Stored normalized usage data in a private cache. Blocked HTTP redirects and kept credentials out of logs and cached data.
- Added setup documentation, a sidebar configuration example, tests, and a screenshot.
- Added the MIT license and versioned ZIP packaging with SHA-256 checksums.
