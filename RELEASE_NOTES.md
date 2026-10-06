# v0.1.4

- If the workspace that shows the subscription rows closes, the rows move to the new first workspace on the next Herdr event. Before, they stayed hidden until the row text changed.
- If the saved Claude Code login token has expired, the Claude row says `open Claude Code` instead of `sign in again`. Start Claude Code to renew the token. The row updates on the next Herdr event.
- After you sign in to Claude Code again, the Claude row updates on the next Herdr event instead of up to an hour later.
- You can install the plugin from the GitHub mirror with `herdr plugin install PurrlyDigital/subscription-watcher`.
- `herdr-plugin.toml` changed. After you update a clone, link the plugin again. If you installed from GitHub, run `herdr plugin install PurrlyDigital/subscription-watcher` again.
