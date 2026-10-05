# Subscription watcher for Herdr

Show your remaining Claude Code and Codex allowance in the expanded Herdr sidebar.
The plugin adds one section beneath the first workspace in each Herdr session.
The hourly job updates the default local session, not saved SSH machines.

Each row shows the percentage remaining. `↻` marks the reset time in your local
timezone. The sidebar matches your active Herdr theme. This screenshot uses a
custom theme.

![Claude Code and Codex allowance in the Herdr sidebar](assets/subscription-sidebar.png)

## Install the plugin

Use macOS with Herdr 0.9.2 or later and Python 3.9 or later. Log in to Claude Code
and Codex on the same Mac before you start.

1. Clone the repository into a permanent directory. Enter the checkout.

	```sh
	git clone https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher.git
	cd subscription-watcher
	```

	For the tagged version, [download the v0.1.0 ZIP](https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher/-/archive/v0.1.0/subscription-watcher-v0.1.0.zip)
	instead. Extract the ZIP and enter the extracted directory.

2. Link the plugin to Herdr.

	```sh
	herdr plugin link "$PWD"
	```

	Keep this directory in place. Herdr loads the linked files, and the hourly job
	uses their absolute paths. Herdr's `plugin install` command accepts GitHub
	sources, so use `plugin link` for this GitLab repository.

3. Merge [sidebar.example.toml](sidebar.example.toml) into
	`~/.config/herdr/config.toml`. Keep your existing configuration.

	If you already have a `[ui.sidebar.spaces]` section, update its `rows` instead
	of adding a second section. To give the rows more room, set
	`sidebar_min_width = 28` in your existing `[ui]` section.

	Reload the configuration.

	```sh
	herdr server reload-config
	```

4. Generate and load the hourly macOS job.

	If you already have an hourly job for this plugin, unload that job first.
	This prevents duplicate requests. For a job created by this generator, use
	`launchctl bootout "gui/$(id -u)/io.herdr.subscription-usage"`.

	```sh
	/usr/bin/python3 make_launchagent.py
	launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/io.herdr.subscription-usage.plist"
	```

	The generator writes the plist outside the repository. Do not commit the
	plist because it contains paths specific to your Mac.

Look for `Subscriptions (hourly)` beneath the first workspace. The job fetches
usage when loaded, at login, and every hour. macOS can defer a run while asleep.
Herdr startup restores the cached rows and fetches again if the cache is overdue.
Workspace changes reposition the cached rows without querying either provider.

## Refresh or check the usage

To fetch fresh usage and update the sidebar, run this command from a Herdr pane.

```sh
herdr plugin action invoke local.subscription-usage.refresh
```

To print the cached rows, run this command from the plugin directory. The output
contains your allowance and reset times, so check it before sharing it.

```sh
/usr/bin/python3 usage.py --print
```

To check the hourly job, inspect its launchd status.

```sh
launchctl print "gui/$(id -u)/io.herdr.subscription-usage"
```

A state of `not running` is normal between hourly runs. Check the last exit code
and the run interval.

## Recover from missing or stale usage

- If a row says `sign in again`, reauthenticate in the native Claude Code or
  Codex client. Then run the refresh command. The plugin does not refresh OAuth tokens.
- If a row says `refresh due`, the reported reset time has passed. Refresh now
  or wait for the next hourly run. The plugin does not assume a full allowance.
- If a row says `refresh pending`, the cache is missing or at least two hours old.
  Check the hourly job and run the refresh command.
- If the rows disappear, check that the sidebar is expanded and the hourly job
  still runs. Herdr expires these rows after two hours without a metadata update.

The provider-specific usage endpoints can change. A failed request produces a
status message instead of a cached credential or raw API error.

## Protect your account data

Anyone who can view the Herdr session can see your allowance and reset times.
Check screenshots, exports, and shared session access before exposing that data.

The plugin reads your local Claude Code and Codex login credentials. It sends
those credentials only to the corresponding provider's HTTPS usage endpoint.
It blocks redirects and ignores environment proxy settings.

The cache stores percentages, reset times, fetch times, and fixed status messages
under `~/.local/state/herdr/subscription-usage/`. The plugin does not log or cache
credentials, account IDs, email addresses, subscription plans, or raw API responses.
Read [Security and disclosure review](SECURITY.md) for the data flow and trust limits.

Keep credential files, generated plists, runtime state, and your full Herdr
configuration out of Git and public bug reports.

## Remove the plugin

1. Unload the hourly job and remove its plist.

	```sh
	launchctl bootout "gui/$(id -u)/io.herdr.subscription-usage"
	rm "$HOME/Library/LaunchAgents/io.herdr.subscription-usage.plist"
	```

2. Unlink the plugin.

	```sh
	herdr plugin unlink local.subscription-usage
	```

3. Remove the subscription rows from your Herdr configuration. Reload the
	configuration with `herdr server reload-config`.

Existing metadata expires within two hours. To discard the cached usage, also
delete `~/.local/state/herdr/subscription-usage/`.

## Test and package a release

Run these commands from the plugin directory.

```sh
/usr/bin/python3 -m unittest -v
/usr/bin/python3 build_release.py
```

The tests use synthetic data. They do not read your account credentials or make
network requests. The packaging script also runs without credentials or network access.

The script reads the version from `herdr-plugin.toml`. For `0.1.0`, it creates
`dist/subscription-watcher-0.1.0.zip` and
`dist/subscription-watcher-0.1.0.zip.sha256`. Verify that archive's checksum.

```sh
(cd dist && shasum -a 256 -c subscription-watcher-0.1.0.zip.sha256)
```

The archive includes only the files named in `FILES` in `build_release.py`.
It uses fixed timestamps and omits workstation file paths and ownership metadata.
Git ignores `dist/`. Review staged files before publishing. The packaging
allowlist does not prevent you from committing an unrelated file.

To publish a new version, follow these steps.

1. Choose an unused version. Update `version` in `herdr-plugin.toml` and the
	README download link.
2. Run the tests and packaging commands. Review and commit the release changes.
3. Tag that commit and push the tag. Replace `0.1.1` below with your new version.

	```sh
	git tag v0.1.1
	git push origin v0.1.1
	```

GitLab provides a source ZIP for each tag. To offer the custom package, attach
its ZIP and checksum to a GitLab Release. The script does not upload files or
create a Release page. Its checksum applies to the custom ZIP, not GitLab's
source ZIP.

## License

This project uses the [MIT license](LICENSE).
