# Subscription Usage for Herdr

A small macOS plugin showing Claude Code and Codex subscription **percent remaining**
in the expanded Spaces sidebar. A single section appears under the first workspace.
`↻` marks reset times in the local timezone. Requires Herdr 0.9.2+ and Python 3.9+.

## Setup

1. Log in to Claude Code and Codex on this Mac.
2. Clone this repository to a permanent local directory and link it:

   ```sh
   herdr plugin link "$PWD"
   ```

3. Merge `sidebar.example.toml` into `~/.config/herdr/config.toml`. Keep existing
   configuration; optionally set `sidebar_min_width = 28` in your existing `[ui]`
   section. Run `herdr server reload-config`.
4. Generate and load the hourly macOS job:

   ```sh
   /usr/bin/python3 make_launchagent.py
   launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/io.herdr.subscription-usage.plist"
   ```

   This generates a plist **outside the repository**, with paths specific to your
   Mac. Do not commit it. If you already have an older hourly job for this plugin,
   unload/remove that job first to avoid duplicate polling. When regenerating an
   already-loaded job, unload it before bootstrapping again.

The job fetches at login and every **3600 seconds**. Herdr startup republishes the
cache, refreshing only if overdue. Workspace events use the cache without querying
providers. macOS may defer execution while asleep. This setup polls local accounts
and publishes to the default local Herdr session, not saved SSH machines.

## Privacy

See `SECURITY.md` for the data flow, hardening, and limits of this review.
OAuth credentials are sent only to the fixed HTTPS usage endpoints of their
respective provider; redirects and environment-configured proxies are disabled.
The cache contains only normalized percentages, reset times, fetch times, and
fixed status strings. Account IDs, email, plan details, raw API responses, and
credentials are not cached, logged, or sent to Herdr.

The sidebar intentionally discloses allowance and reset times to **anyone who can
view the Herdr session**, including attached clients, screenshots, and exports.
Do not treat the usage rows as private from other session viewers.

Credentials are read from Claude Code's macOS Keychain or its `.credentials.json`
(`CLAUDE_CONFIG_DIR` is supported), and Codex's `auth.json` (`CODEX_HOME` is supported).
Private runtime state lives outside the repository at
`~/.local/state/herdr/subscription-usage/`. No OAuth token refresh is attempted:
if login is rejected, reauthenticate in the native client and refresh manually.
The provider-specific endpoints may change.

Expired reset times show `refresh due`, not an invented full balance. Cache older
than two hours shows `refresh pending`; sidebar metadata also expires after two
hours if the background job stops.

## Refresh / inspect

```sh
herdr plugin action invoke local.subscription-usage.refresh
/usr/bin/python3 usage.py --print
launchctl print "gui/$(id -u)/io.herdr.subscription-usage"
```

`--print` deliberately prints the normalized usage rows, never login credentials.
Use it only where you are comfortable displaying usage information.

## Tests

Small, offline tests with synthetic data and no account access:

```sh
/usr/bin/python3 -m unittest -v
```

## Remove

```sh
launchctl bootout "gui/$(id -u)/io.herdr.subscription-usage"
rm "$HOME/Library/LaunchAgents/io.herdr.subscription-usage.plist"
herdr plugin unlink local.subscription-usage
```

Remove the subscription rows from your Herdr config and reload it. Existing
metadata expires within two hours. Delete the runtime state directory separately
if you want to remove cached usage.

## Publishing

Publish only these files: `.gitignore`, `herdr-plugin.toml`, `usage.py`,
`make_launchagent.py`, `test_usage.py`, `sidebar.example.toml`, `README.md`, and
`SECURITY.md`. Do **not** publish your full Herdr configuration, config backups,
session snapshots, credential files, runtime cache/logs, or generated LaunchAgent.
The ignore rules are defense in depth, not a substitute for checking staged files.

Herdr's built-in `plugin install` currently accepts GitHub sources, not GitLab.
For a GitLab repository, clone it with Git and use `herdr plugin link` as above.
