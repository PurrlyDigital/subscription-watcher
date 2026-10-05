# Changelog

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
