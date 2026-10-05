# Subscription watcher for Herdr

Shows your remaining Claude Code and Codex allowance in the Herdr sidebar.
Refreshes hourly and matches your active theme.

![Claude Code and Codex allowance in the Herdr sidebar](assets/subscription-sidebar.png)

The header shows the last refresh time. `↻` beside an allowance marks its reset
time. Times use AM/PM in your local timezone.

[Changelog](CHANGELOG.md)

## Install

Requires macOS or Linux, Herdr 0.9.2 or later, and Python 3.9 or later at
`/usr/bin/python3`. On Windows, use WSL2. Herdr does not support native Windows.
Log in to Claude Code and Codex before installing.

### macOS

1. Clone the repository, or extract the [v0.2.0 ZIP](https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher/-/archive/v0.2.0/subscription-watcher-v0.2.0.zip).

	```sh
	git clone https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher.git
	cd subscription-watcher
	```

2. From the plugin directory, link it to Herdr. Keep that directory in place.

	```sh
	herdr plugin link "$PWD"
	```

3. Merge [sidebar.example.toml](sidebar.example.toml) into `~/.config/herdr/config.toml`.
	Update an existing `[ui.sidebar.spaces]` section rather than adding a duplicate.
	If rows are clipped, set `sidebar_min_width = 32` under `[ui]`.

	```sh
	herdr server reload-config
	```

4. Start the hourly job. If you are reinstalling, unload the existing job first
	with `launchctl bootout "gui/$(id -u)/io.herdr.subscription-usage"`.

	```sh
	/usr/bin/python3 make_launchagent.py
	launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/io.herdr.subscription-usage.plist"
	```

5. Linking does not run the plugin's startup hook. Refresh once to fill the rows.

	```sh
	herdr plugin action invoke local.subscription-usage.refresh
	```

### Linux and WSL2

On WSL2, complete these steps first.

- If systemd is off, add these lines to `/etc/wsl.conf`. Then run
	`wsl --shutdown` from Windows and reopen your distribution.

	```ini
	[boot]
	systemd=true
	```

- Log in to Claude Code and Codex inside WSL. The plugin does not read Windows
	logins.

1. Clone the repository into the Linux filesystem, for example under `~/src`.
	On WSL2, do not clone into `/mnt/c/...`. Windows drives ignore `chmod` and are slow.

	```sh
	git clone https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher.git
	cd subscription-watcher
	```

2. From the plugin directory, link it to Herdr. Keep that directory in place.

	```sh
	herdr plugin link "$PWD"
	```

3. Merge [sidebar.example.toml](sidebar.example.toml) into `~/.config/herdr/config.toml`,
	as in macOS step 3. Then reload the config.

	```sh
	herdr server reload-config
	```

4. Generate the systemd user units, then start the hourly timer.

	```sh
	/usr/bin/python3 make_systemd_timer.py
	systemctl --user daemon-reload
	systemctl --user enable --now subscription-usage.timer
	```

5. Linking does not run the plugin's startup hook. Refresh once to fill the rows.

	```sh
	herdr plugin action invoke local.subscription-usage.refresh
	```

If a detached Herdr server keeps running after you log out, turn on linger to
keep the timer running too. This step is optional.

```sh
loginctl enable-linger "$USER"
```

#### Without systemd

Use cron instead of step 4. Run `crontab -e` and add this line. Replace
`<plugin-dir>` with the absolute path of your clone.

```crontab
0 * * * * /usr/bin/python3 <plugin-dir>/usage.py --refresh
```

If `herdr` is not at `~/.local/bin/herdr`, add `HERDR_BIN_PATH=<path-to-herdr>`
before `/usr/bin/python3` in that line. Then refresh, as in step 5.

## Usage

Refresh now.

```sh
herdr plugin action invoke local.subscription-usage.refresh
```

Show cached usage from the plugin directory.

```sh
/usr/bin/python3 usage.py --print
```

Check the hourly job on macOS.

```sh
launchctl print "gui/$(id -u)/io.herdr.subscription-usage"
```

Check the hourly job on Linux.

```sh
systemctl --user list-timers subscription-usage.timer
journalctl --user -u subscription-usage.service
```

If a row says `sign in again`, log in to that provider again and refresh.
`refresh due` means the reset time has passed. `refresh pending` means the cache
is missing or at least two hours old.

## Update

Run these steps from the plugin directory. If you installed from the ZIP,
extract the new version over the old directory instead of step 1. If you
extract it to a new directory, follow the steps for a moved clone.

1. Pull the latest version.

	```sh
	git pull --ff-only
	```

2. If `herdr-plugin.toml` changed, link the plugin again. Herdr reads the
	manifest only at link time. Your config and cached usage stay in place.

	```sh
	herdr plugin link "$PWD"
	```

	If you moved the clone to a new path, unlink the old path first, then link
	from the new path.

	```sh
	herdr plugin unlink local.subscription-usage
	herdr plugin link "$PWD"
	```

3. If you moved the clone, generate the hourly job again.
	On macOS, repeat install step 4, including the unload command.
	On Linux, run these commands.

	```sh
	/usr/bin/python3 make_systemd_timer.py
	systemctl --user daemon-reload
	```

4. Refresh.

	```sh
	herdr plugin action invoke local.subscription-usage.refresh
	```

If only `usage.py` changed, you can skip steps 2 to 4. The next run uses the new code.

## Privacy

The plugin does not store or log credentials. Other Herdr session viewers can
see your usage and reset times. See the [security review](SECURITY.md) for details.

## Remove

On macOS, run these commands.

```sh
launchctl bootout "gui/$(id -u)/io.herdr.subscription-usage"
rm "$HOME/Library/LaunchAgents/io.herdr.subscription-usage.plist"
herdr plugin unlink local.subscription-usage
```

On Linux, run these commands. If you used cron, remove the crontab line instead
of the `systemctl` and `rm` commands.

```sh
systemctl --user disable --now subscription-usage.timer
rm "$HOME/.config/systemd/user/subscription-usage.service" "$HOME/.config/systemd/user/subscription-usage.timer"
systemctl --user daemon-reload
herdr plugin unlink local.subscription-usage
```

If you turned on linger only for this plugin, turn it off.

```sh
loginctl disable-linger "$USER"
```

Remove the subscription rows from `~/.config/herdr/config.toml` and run
`herdr server reload-config`. To delete cached usage, remove
`~/.local/state/herdr/subscription-usage/`.

## Test and package

Run these commands from the plugin directory.

```sh
/usr/bin/python3 -m unittest -v
/usr/bin/python3 build_release.py
```

The build reads the version from `herdr-plugin.toml` and writes a ZIP and
SHA-256 checksum to `dist/`. For version `0.2.0`, verify the checksum.

```sh
# macOS
(cd dist && shasum -a 256 -c subscription-watcher-0.2.0.zip.sha256)
# Linux
(cd dist && sha256sum -c subscription-watcher-0.2.0.zip.sha256)
```

Attach the ZIP and checksum to a GitLab Release. The checksum applies to this
package, not GitLab's source archive.

## License

[MIT](LICENSE)
