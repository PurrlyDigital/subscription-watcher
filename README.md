# Subscription watcher for Herdr

Shows your remaining Claude Code and Codex allowance in the Herdr sidebar.
Refreshes hourly while you use Herdr and matches your active theme.

![Claude, Fable, and Codex allowance rows in the Herdr sidebar](assets/subscription-sidebar.png)

The header shows the last refresh time in AM/PM. Each row shows the remaining
percentage and the time until it resets, in one unit: days from 48 hours, hours
from 1 hour, and minutes below that.

The Claude row shows the 5-hour allowance first, then the weekly one. The Fable
row is the weekly Fable allowance. The Codex row ends with the number of rate
limit resets available on your account.

When you focus a workspace, tab, or pane, or an agent changes status, the plugin
refreshes if the last refresh is an hour old or a shown allowance has reset. After
sleep or a detached session, the rows update the first time you use Herdr again.
The optional hourly job also refreshes while you are away.

[Changelog](CHANGELOG.md)

## Install

Requires macOS or Linux, Herdr 0.9.2 or later, and Python 3.9 or later at
`/usr/bin/python3`. On Windows, use WSL2. Herdr does not support native Windows.
Log in to Claude Code and Codex before installing.

### Install from GitHub

Herdr can install the plugin from the [GitHub mirror](https://github.com/PurrlyDigital/subscription-watcher)
on macOS, Linux, and WSL2. On WSL2, first complete the setup at the start of
[Linux and WSL2](#linux-and-wsl2).

1. Install the plugin, then go to the directory where Herdr installed it.

	```sh
	herdr plugin install PurrlyDigital/subscription-watcher
	cd "$(herdr plugin list --json | /usr/bin/python3 -c 'import json, sys; print(next(p["plugin_root"] for p in json.load(sys.stdin)["result"]["plugins"] if p["plugin_id"] == "local.subscription-usage"))')"
	```

2. Continue from step 3 of the macOS or Linux steps.

### macOS

1. Clone the repository, or extract the [v0.1.3 ZIP](https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher/-/archive/v0.1.3/subscription-watcher-v0.1.3.zip).

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
	Then reload the config in each open Herdr window. Press the prefix key
	(`ctrl+b` by default), then `shift+R`. `herdr server reload-config` does not
	update the sidebar layout of a window that is already open.

4. Optional: start the hourly job. If you are reinstalling, unload the existing job first
	with `launchctl bootout "gui/$(id -u)/io.herdr.subscription-usage"`.

	```sh
	/usr/bin/python3 make_launchagent.py
	launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/io.herdr.subscription-usage.plist"
	```

5. Refresh once to fill the rows.

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

- Log in to Claude Code and Codex inside WSL.

1. Clone the repository into the Linux filesystem, for example under `~/src`.
	On WSL2, do not clone into `/mnt/c/...`.

	```sh
	git clone https://gitlab.com/purrly-digital-llc/herdr-stuff/subscription-watcher.git
	cd subscription-watcher
	```

2. From the plugin directory, link it to Herdr. Keep that directory in place.

	```sh
	herdr plugin link "$PWD"
	```

3. Merge [sidebar.example.toml](sidebar.example.toml) into `~/.config/herdr/config.toml`,
	and reload the config in each open Herdr window, as in macOS step 3.

4. Optional: generate the systemd user units, then start the hourly timer.

	```sh
	/usr/bin/python3 make_systemd_timer.py
	systemctl --user daemon-reload
	systemctl --user enable --now subscription-usage.timer
	```

5. Refresh once to fill the rows.

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
`reset` in place of a percentage means that allowance has reset since the last
refresh. `refresh pending` means the cache is missing or at least two hours old.

## Update

If you installed from GitHub, run `herdr plugin install PurrlyDigital/subscription-watcher`
again, then refresh as in step 4. Herdr replaces the checkout at the same path,
so the hourly job keeps working.

For a clone, run these steps from the plugin directory. If you installed from
the ZIP, extract the new version over the old directory instead of step 1. If
you extract it to a new directory, follow the steps for a moved clone.

1. Pull the latest version.

	```sh
	git pull --ff-only
	```

2. If `herdr-plugin.toml` changed, link the plugin again.

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

If `sidebar.example.toml` changed, merge its rows into
`~/.config/herdr/config.toml` again. Then reload the config in each open Herdr
window with the prefix key and `shift+R`.

If only `usage.py` changed, you can skip steps 2 to 4.

## Privacy

The plugin does not store or log credentials. Other Herdr session viewers can
see your usage and reset times. See the [security review](SECURITY.md) for details.

## Remove

If you installed from GitHub, run `herdr plugin uninstall local.subscription-usage`
in place of `herdr plugin unlink local.subscription-usage`. It also deletes the
checkout.

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

Remove the subscription rows from `~/.config/herdr/config.toml`, then reload
the config in each open Herdr window with the prefix key and `shift+R`. To delete
cached usage, remove
`~/.local/state/herdr/subscription-usage/`.

## Test and package

Run these commands from the plugin directory.

```sh
/usr/bin/python3 -m unittest -v
/usr/bin/python3 build_release.py
```

The build reads the version from `herdr-plugin.toml` and writes a ZIP and
SHA-256 checksum to `dist/`. For version `0.1.3`, verify the checksum.

```sh
# macOS
(cd dist && shasum -a 256 -c subscription-watcher-0.1.3.zip.sha256)
# Linux
(cd dist && sha256sum -c subscription-watcher-0.1.3.zip.sha256)
```

Attach the ZIP and checksum to a GitLab Release. The checksum applies to this
package, not GitLab's source archive.

## License

[MIT](LICENSE)
