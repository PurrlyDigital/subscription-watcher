# v0.1.3

- The sidebar shows three rows: Claude, Fable, and Codex. Replace the old subscription rows in your sidebar config with the rows in `sidebar.example.toml`. Then reload the config in Herdr with the prefix key and `shift+R`.
- The Fable row shows the weekly Fable allowance. The Codex row ends with the number of available rate limit resets.
- Each allowance shows the time until it resets as a one-unit countdown, such as `4h` or `4d`.
- The plugin refreshes the first time you use Herdr after a detached session or sleep. The hourly LaunchAgent and systemd timer are optional.
- After a `usage unavailable` failure, the plugin retries after five minutes.
- `herdr-plugin.toml` changed, so link the plugin again after you update.
