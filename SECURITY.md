# Security and disclosure review

## Scope

Source, manifest, tests, example sidebar config, documentation, the local
LaunchAgent and systemd timer generators, and release packaging were reviewed.
The example image intentionally shows usage rows; its PNG metadata was removed
before publication.
This is a focused code review, not a guarantee against every vulnerability or a
third-party security certification.

## Intended data flow

- Reads native Claude Code/Codex credentials into process memory. On Linux,
  including WSL2, the plugin reads them only from the login files. Claude Code
  credentials are in `.credentials.json` in `~/.claude` or `$CLAUDE_CONFIG_DIR`.
  Codex credentials are in `auth.json` in `~/.codex` or `$CODEX_HOME`. The
  plugin does not check the permissions of these files. Keep them readable only
  by you (0600). The Keychain fallback runs only on macOS.
- Sends Claude's OAuth bearer token only to
  `https://api.anthropic.com/api/oauth/usage`.
- Sends Codex's OAuth bearer token and, if present, ChatGPT account ID only to
  `https://chatgpt.com/backend-api/wham/usage`.
- Keeps only allowance percentages, fixed window labels, reset times, fetch time,
  and fixed error/status strings in the local cache and Herdr metadata.
- Does not collect email, organization, account ID, subscription plan, conversation
  text, workspace contents, or refresh tokens for storage/display/transmission to
  Herdr. Credential files can contain those fields; the script selects only the
  access token and the Codex account ID needed for the provider request.
- No analytics, telemetry service, GitLab traffic, or third-party network endpoint.

## Findings addressed

1. **Redirect credential forwarding.** Python urllib's default redirect handler
   copies request headers to redirected requests, potentially exposing bearer
   credentials to another origin or an HTTP URL. All redirects are now blocked;
   only the two exact HTTPS URLs above are accepted. TLS verification remains
   enabled. Environment proxy settings are deliberately ignored.
2. **Personal installation details.** The old local launcher contained workstation
   home paths; tests reused real usage observations. Neither is needed in public
   source. Tests now use synthetic data, docs are generic, and the generator writes
   machine-specific launch configuration outside the repository.
3. **Filesystem/cache handling.** State directory permissions are enforced as 0700,
   locks/cache writes are 0600, cache writes use private random temporary files and
   atomic replacement, and symlink cache/lock reads are rejected. The generator
   prepares a private log file. The cache has a bounded size and schema whitelist;
   arbitrary cached labels, errors, or extra account fields are not displayed.
4. **Error disclosure.** HTTP/parser/subprocess failures are reduced to fixed safe
   strings. The command entrypoint does not print tracebacks or exception messages.
   API headers, raw bodies, and Keychain subprocess output are never logged.
5. **Subprocess exposure.** Credentials are not passed in process arguments. Only a
   small environment allowlist is inherited by Keychain/Herdr subprocesses, rather
   than unrelated API keys or the plugin's selected-text/context environment.
6. **Accidental publication.** Runtime data stays outside the source tree; ignore
   rules and an explicit public-file list exclude credentials, usage logs/cache,
   generated plists, and Python artifacts. The systemd generator writes its units
   to `~/.config/systemd/user/`, outside the repository. Distribution ZIPs are
   built from an explicit public-file allowlist, with fixed timestamps and no workstation file
   paths/ownership metadata. Generated bundles are ignored by Git.
7. **systemd unit injection.** systemd expands `%` specifiers and `$` variables
   and interprets quotes and backslashes, even inside double quotes. The generator
   accepts only printable absolute paths without `%`, `$`, quotes, or backslashes,
   and validates every value before it writes a file. It refuses symlinked unit
   files and a symlinked units directory, and writes units as 0600 through atomic
   replacement. `Environment=` holds only the Herdr binary and socket paths, never
   a credential or token. The generator never calls `systemctl`.

## Trust boundaries and remaining considerations

- Usage percentages and reset times are intentionally visible to every connected
  Herdr client and may appear in screenshots, metadata inspection, exports, or
  Herdr-owned diagnostics. This plugin cannot make a shared session private.
- The native login files, macOS Keychain, operating system, Python/TLS trust store,
  Herdr binary, plugin source directory, and configured credential/socket/binary
  overrides must be trusted. This is not a sandbox against another process running
  as the same user, an administrator, a compromised provider, or a compromised
  computer.
- On WSL2, Windows processes that run as the same Windows user can read the Linux
  filesystem through `\\wsl$`, including the login files and the cache. Treat
  the Windows account as part of the trust boundary.
- The LaunchAgent and the systemd service each record the absolute paths of the
  Python interpreter and `usage.py`. The scheduler runs whatever code is at those
  paths every hour. Protect the plugin directory and the interpreter from writes
  by other users, and generate the job again if either moves.
- Credentials necessarily exist in memory during authenticated requests. Python
  does not guarantee secure memory erasure; privileged inspection/crash collection
  is outside this plugin's protection.
- Normal DNS/TLS connections expose provider destinations to network observers,
  not plaintext bearer credentials under ordinary trusted TLS operation.
- The local allowance cache is private to the user, but is still personal usage
  data. Do not commit it or attach it to public bug reports.
- The CLI/session metadata and its access controls belong to Herdr. This review
  does not audit Herdr's socket permissions, snapshots, or diagnostics implementation.
- Do not publish the containing `.config/herdr` directory, the generated local
  launcher, or the generated systemd units. Review staged files before pushing,
  even with `.gitignore` present.

## Verification

A small offline unittest suite checks redirect rejection, the endpoint allowlist,
error redaction, normalized cache filtering/private writes, the macOS-only
Keychain fallback, and basic display behavior. It also checks the exact systemd
unit text, file modes, rejection of unsafe values, and refusal of symlinked unit
paths. It uses no real credentials or live network. Public source is also
checked for personal paths, email addresses other than explicit synthetic test
fixtures, and common credential patterns before publication.
