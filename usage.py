#!/usr/bin/python3
"""Read subscription allowances; publish safe, hourly-cached Herdr sidebar tokens."""
import argparse
import datetime as dt
import fcntl
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HOME = Path.home()
ROOT = HOME / ".local/state/herdr/subscription-usage"
CACHE = ROOT / "usage.json"
INTERVAL = 3600
MAX_AGE = 7200
SOURCE = "local:subscription-usage"
CLAUDE_URL = "https://api.anthropic.com/api/oauth/usage"
CODEX_URL = "https://chatgpt.com/backend-api/wham/usage"
MAX_JSON_BYTES = 1024 * 1024
SAFE_ERRORS = frozenset(("sign in again", "rate limited", "login unavailable", "usage unavailable"))
TOKEN_NAMES = ("subscription_header", "claude_5h", "claude_week",
               "codex_primary", "codex_secondary", "usage_updated")
# Keep usage_updated in the patch list to clear the separate row on older installs.


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        # urllib otherwise copies Authorization even to a different host or HTTP.
        raise urllib.error.HTTPError(request.full_url, code, "Redirect blocked", headers, response)


def get_json(url, headers):
    if url not in (CLAUDE_URL, CODEX_URL):
        raise ValueError("unapproved usage endpoint")
    request = urllib.request.Request(url, headers={
        "User-Agent": "herdr-subscription-usage/1.0", **headers,
    })
    # Direct TLS, default certificate validation; no redirects or ambient proxies.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirects())
    with opener.open(request, timeout=20) as response:
        raw = response.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("usage response too large")
    return json.loads(raw)


def child_environment():
    # Do not pass API keys, plugin context/selected text, or unrelated shell secrets
    # to the Keychain/Herdr subprocesses. Socket and binary overrides are trusted.
    env = {key: os.environ[key] for key in
           ("HOME", "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR",
            "HERDR_SOCKET_PATH", "HERDR_SESSION") if key in os.environ}
    env.setdefault("HOME", str(HOME))
    env.setdefault("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    return env


def window(label, used, reset):
    used = float(used)
    if not math.isfinite(used) or not 0 <= used <= 100:
        raise ValueError("invalid utilization")
    if isinstance(reset, str):
        reset = dt.datetime.fromisoformat(reset.replace("Z", "+00:00")).timestamp()
    if reset is not None:
        reset = float(reset)
        if not math.isfinite(reset) or not 0 <= reset <= 4102444800:
            raise ValueError("invalid reset time")
    return {"label": label, "remaining": round(100 - used), "reset": reset}


def claude_usage():
    credentials_file = Path(os.environ.get("CLAUDE_CONFIG_DIR", HOME / ".claude")) / ".credentials.json"
    if credentials_file.exists():
        credentials = json.loads(credentials_file.read_text())
    else:
        result = subprocess.run(
            ["/usr/bin/security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=10, env=child_environment(),
        )
        if result.returncode:
            raise FileNotFoundError("Claude Code login unavailable")
        credentials = json.loads(result.stdout)
    token = credentials["claudeAiOauth"]["accessToken"]
    usage = get_json(CLAUDE_URL, {
        "Authorization": "Bearer " + token,
        "anthropic-beta": "oauth-2025-04-20",
    })
    return {name: window(label, usage[key]["utilization"], usage[key].get("resets_at"))
            for name, key, label in (("claude_5h", "five_hour", "Claude 5h"),
                                     ("claude_week", "seven_day", "Claude wk"))
            if usage.get(key)}


def codex_usage():
    auth_file = Path(os.environ.get("CODEX_HOME", HOME / ".codex")) / "auth.json"
    tokens = json.loads(auth_file.read_text())["tokens"]
    headers = {"Authorization": "Bearer " + tokens["access_token"]}
    if tokens.get("account_id"):
        headers["ChatGPT-Account-Id"] = tokens["account_id"]
    usage = get_json(CODEX_URL, headers)
    result = {}
    limits = usage.get("rate_limit") or {}
    for key, name in (("primary_window", "codex_primary"),
                      ("secondary_window", "codex_secondary")):
        value = limits.get(key)
        if not value:
            continue
        seconds = value.get("limit_window_seconds")
        if seconds is not None and (type(seconds) is not int or not 1 <= seconds <= 31536000):
            raise ValueError("invalid limit duration")
        period = "wk" if seconds == 604800 else (
            f"{seconds // 3600}h" if seconds and seconds % 3600 == 0 else "limit")
        result[name] = window("Codex " + period, value["used_percent"], value.get("reset_at"))
    return result


def safe_fetch(fetch):
    try:
        values = fetch()
        return {"windows": values} if values else {"error": "usage unavailable"}
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            message = "sign in again"
        elif error.code == 429:
            message = "rate limited"
        else:
            message = "usage unavailable"
    except FileNotFoundError:
        message = "login unavailable"
    except Exception:
        # Even unexpected parser/network exceptions must not echo response data.
        message = "usage unavailable"
    # Never log exceptions, credentials, headers, or raw responses.
    return {"error": message}


def sanitize_cache(cache):
    """Allow only the normalized schema; never render arbitrary cached strings."""
    if not isinstance(cache, dict):
        return {}
    fetched = cache.get("fetched_at")
    if type(fetched) not in (int, float) or not math.isfinite(fetched) or not 0 < fetched <= 4102444800:
        return {}
    clean = {"fetched_at": fetched}
    for provider in ("claude", "codex"):
        data = cache.get(provider)
        if not isinstance(data, dict):
            clean[provider] = {"error": "usage unavailable"}
            continue
        if "error" in data:
            error = data["error"]
            clean[provider] = {"error": error if isinstance(error, str) and error in SAFE_ERRORS
                              else "usage unavailable"}
            continue
        windows = {}
        names = ("claude_5h", "claude_week") if provider == "claude" else ("codex_primary", "codex_secondary")
        cached_windows = data.get("windows")
        if not isinstance(cached_windows, dict):
            cached_windows = {}
        for name in names:
            value = cached_windows.get(name)
            if not isinstance(value, dict):
                continue
            remaining = value.get("remaining")
            if type(remaining) is not int or not 0 <= remaining <= 100:
                continue
            label = value.get("label")
            if provider == "claude":
                label = "Claude 5h" if name == "claude_5h" else "Claude wk"
            elif not isinstance(label, str) or (label not in ("Codex wk", "Codex limit") and
                  not (label.startswith("Codex ") and label.endswith("h") and
                       label[6:-1].isascii() and label[6:-1].isdigit() and
                       1 <= len(label[6:-1]) <= 4)):
                continue
            try:
                windows[name] = window(label, 100 - remaining, value.get("reset"))
            except (ValueError, TypeError, OverflowError):
                continue
        clean[provider] = {"windows": windows} if windows else {"error": "usage unavailable"}
    return clean


def load_cache():
    try:
        fd = os.open(CACHE, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as file:
            if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
                return {}
            raw = file.read(MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES:
            return {}
        return sanitize_cache(json.loads(raw))
    except (OSError, ValueError, TypeError, AttributeError, OverflowError):
        return {}


def refresh():
    result = {"fetched_at": time.time(), "claude": safe_fetch(claude_usage),
              "codex": safe_fetch(codex_usage)}
    # Only normalized percentages, reset times, and safe status strings are stored.
    temp = None
    try:
        # mkstemp creates a new, private file: no deterministic-name symlink or
        # briefly world-readable existing temporary file before chmod.
        with tempfile.NamedTemporaryFile(mode="w", dir=ROOT, prefix=".usage-", delete=False) as file:
            temp = Path(file.name)
            os.fchmod(file.fileno(), 0o600)
            json.dump(result, file, allow_nan=False)
            file.write("\n")
        temp.replace(CACHE)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    return result


def format_time(value):
    hour = value.hour % 12 or 12
    period = "AM" if value.hour < 12 else "PM"
    return f"{hour}:{value.minute:02d} {period}"


def format_window(value, now):
    label = value["label"]
    reset = value.get("reset")
    if reset is not None and reset <= now:
        return f"{label}: refresh due"
    text = f"{label}: {value['remaining']}%"
    if reset is not None:
        local = dt.datetime.fromtimestamp(reset).astimezone()
        today = dt.datetime.fromtimestamp(now).astimezone().date()
        suffix = format_time(local)
        if local.date() != today:
            suffix = local.strftime("%a ") + suffix
        text += " ↻" + suffix
    return text


def sidebar_tokens(cache, now=None):
    now = time.time() if now is None else now
    tokens = dict.fromkeys(TOKEN_NAMES)
    tokens["subscription_header"] = "Subscriptions"
    fetched = cache.get("fetched_at", 0)
    if fetched:
        refreshed = format_time(dt.datetime.fromtimestamp(fetched))
        tokens["subscription_header"] = f"Subscriptions (↻ {refreshed})"
    if not fetched or now - fetched >= MAX_AGE:
        tokens["claude_5h"] = "Claude: refresh pending"
        tokens["codex_primary"] = "Codex: refresh pending"
        return tokens
    for provider, first_token in (("claude", "claude_5h"), ("codex", "codex_primary")):
        data = cache.get(provider, {})
        if data.get("error") or not data.get("windows"):
            tokens[first_token] = f"{provider.capitalize()}: {data.get('error', 'usage unavailable')}"
        else:
            for name, value in data["windows"].items():
                if name in tokens:
                    tokens[name] = format_window(value, now)
    return tokens


def herdr(*args):
    env = child_environment()
    env.setdefault("HERDR_SOCKET_PATH", str(HOME / ".config/herdr/herdr.sock"))
    result = subprocess.run(
        [os.environ.get("HERDR_BIN_PATH", str(HOME / ".local/bin/herdr")), *args],
        capture_output=True, text=True, timeout=15, env=env,
    )
    if result.returncode:
        raise RuntimeError("Herdr server unavailable")
    # Successful metadata no-ops can return no output on Herdr 0.9.2.
    return json.loads(result.stdout) if result.stdout.strip() else {}


def publish(cache):
    spaces = herdr("workspace", "list")["result"]["workspaces"]
    tokens = sidebar_tokens(cache)
    # One section under the first local workspace, not duplicated on every row.
    for index, space in enumerate(spaces):
        if index and not any(key in space.get("tokens", {}) for key in TOKEN_NAMES):
            continue
        args = ["workspace", "report-metadata", space["workspace_id"],
                "--source", SOURCE, "--ttl-ms", str(MAX_AGE * 1000)]
        for name, value in tokens.items():
            if index == 0 and value is not None:
                args.extend(["--token", name + "=" + value])
            else:
                args.extend(["--clear-token", name])
        herdr(*args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--refresh", action="store_true", help="fetch fresh usage (hourly scheduler)")
    mode.add_argument("--cached", action="store_true", help="publish cached usage without API requests")
    mode.add_argument("--print", action="store_true", dest="print_only", help="display cached sidebar text")
    args = parser.parse_args()
    os.umask(0o077)
    ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    info = ROOT.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise OSError("unsafe state directory")
    ROOT.chmod(0o700)
    fd = os.open(ROOT / "refresh.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a") as lock:
        os.fchmod(lock.fileno(), 0o600)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        cache = load_cache()
        if args.print_only:
            for value in sidebar_tokens(cache).values():
                if value:
                    print(value)
            return
        if args.refresh or (not args.cached and time.time() - cache.get("fetched_at", 0) >= INTERVAL):
            cache = refresh()
        try:
            publish(cache)
        except (RuntimeError, OSError, subprocess.SubprocessError, ValueError, KeyError):
            # Keep the cache even when Herdr is not running; startup republishes it.
            print("Subscription usage cached; Herdr sidebar unavailable.")


def entrypoint():
    try:
        main()
        return 0
    except Exception:
        # Tracebacks/exception messages may contain private paths or input data.
        print("Subscription usage unavailable; check local setup.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(entrypoint())
