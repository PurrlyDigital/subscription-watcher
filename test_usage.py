"""Small offline checks; all fixtures are synthetic, never account data."""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

import usage


class UsageTests(unittest.TestCase):
    def test_remaining_and_expired_reset(self):
        value = usage.window("Claude 5h", 25, 200)
        self.assertEqual(value["remaining"], 75)
        self.assertEqual(usage.format_window(value, 201), "reset")
        self.assertEqual(usage.format_window(value, 201, first=False), "5h reset")
        with self.assertRaises(ValueError):
            usage.window("Claude 5h", float("nan"), None)

    def test_twelve_hour_time(self):
        for hour, expected in ((0, "12:05 AM"), (12, "12:05 PM"), (19, "7:05 PM")):
            self.assertEqual(usage.format_time(dt.datetime(2030, 1, 2, hour, 5)), expected)

    def test_one_unit_countdown(self):
        for seconds, expected in ((172800, "2d"), (172799, "47h"), (3600, "1h"),
                                  (3599, "59m"), (20, "1m")):
            self.assertEqual(usage.format_countdown(seconds), expected)

    def test_three_rows_with_fable_and_resets(self):
        now = dt.datetime(2030, 1, 2, 11, 16).timestamp()
        cache = {"fetched_at": now - 60,
                 "claude": {"windows": {
                     "claude_5h": usage.window("Claude 5h", 0, now + 4 * 3600 + 44 * 60),
                     "claude_week": usage.window("Claude wk", 84, now + 7 * 3600 + 44 * 60),
                     "fable_week": usage.window("Fable wk", 49, now + 7 * 3600 + 44 * 60)}},
                 "codex": {"windows": {
                     "codex_primary": usage.window("Codex wk", 45, now + 4 * 86400 + 5 * 3600)},
                     "resets": 2}}
        tokens = usage.sidebar_tokens(cache, now=now)
        self.assertEqual(tokens["subscription_header"], "Subscriptions ↻ 11:15 AM")
        self.assertEqual(tokens["claude"], "Claude 100% 4h · wk 16% 7h")
        self.assertEqual(tokens["fable"], "Fable 51% 7h")
        self.assertEqual(tokens["codex"], "Codex 55% 4d · 2 resets")
        for old in ("claude_5h", "claude_week", "codex_primary", "codex_secondary", "usage_updated"):
            self.assertIsNone(tokens[old])
        cache["codex"]["resets"] = 1
        self.assertEqual(usage.sidebar_tokens(cache, now=now)["codex"], "Codex 55% 4d · 1 reset")

    def test_fable_and_reset_count_parsing(self):
        claude = {"five_hour": {"utilization": 0, "resets_at": None},
                  "limits": [{"kind": "weekly_scoped", "percent": 49, "resets_at": None,
                              "scope": {"model": {"display_name": "Fable"}}},
                             {"kind": "weekly_scoped", "percent": 10, "resets_at": None,
                              "scope": {"model": {"display_name": "Other"}}}]}
        codex = {"rate_limit": {"primary_window": {"used_percent": 45, "limit_window_seconds": 604800,
                                                   "reset_at": None}},
                 "rate_limit_reset_credits": {"available_count": 2}}
        with patch.object(usage, "get_json", side_effect=[claude, codex]), \
                patch.object(usage.sys, "platform", "linux"), tempfile.TemporaryDirectory() as home:
            Path(home, ".credentials.json").write_text('{"claudeAiOauth": {"accessToken": "TEST_ONLY"}}')
            Path(home, "auth.json").write_text('{"tokens": {"access_token": "TEST_ONLY"}}')
            with patch.dict(usage.os.environ, {"CLAUDE_CONFIG_DIR": home, "CODEX_HOME": home}):
                claude_data, codex_data = usage.claude_usage(), usage.codex_usage()
        self.assertEqual(sorted(claude_data["windows"]), ["claude_5h", "fable_week"])
        self.assertEqual(claude_data["windows"]["fable_week"]["remaining"], 51)
        self.assertEqual(codex_data["resets"], 2)
        cached = usage.sanitize_cache({"fetched_at": 100, "claude": claude_data,
                                       "codex": {**codex_data, "resets": "2"}})
        self.assertIn("fable_week", cached["claude"]["windows"])
        self.assertNotIn("resets", cached["codex"])

    def test_stale_cache_does_not_display_old_balance(self):
        cache = {"fetched_at": 100, "claude": {"windows": {
            "claude_5h": usage.window("Claude 5h", 25, 100000)}}}
        tokens = usage.sidebar_tokens(cache, now=100 + usage.MAX_AGE)
        self.assertEqual(tokens["claude"], "Claude: refresh pending")
        self.assertNotIn("75%", str(tokens))

    def test_needs_refresh_after_sleep_reset_or_network_failure(self):
        fetched = dt.datetime(2030, 1, 2, 9, 0).timestamp()
        fresh = {"fetched_at": fetched, "claude": {"windows": {
            "claude_5h": usage.window("Claude 5h", 25, fetched + 1800)}}}
        self.assertFalse(usage.needs_refresh(fresh, fetched + 60))
        self.assertTrue(usage.needs_refresh(fresh, fetched + usage.INTERVAL))
        self.assertTrue(usage.needs_refresh(fresh, fetched + 1800))
        # A reset that had already passed at fetch time does not trigger a loop.
        old_reset = {"fetched_at": fetched, "claude": {"windows": {
            "claude_5h": usage.window("Claude 5h", 25, fetched - 10)}}}
        self.assertFalse(usage.needs_refresh(old_reset, fetched + 60))
        offline = {"fetched_at": fetched, "claude": {"error": "usage unavailable"}}
        self.assertFalse(usage.needs_refresh(offline, fetched + 60))
        self.assertTrue(usage.needs_refresh(offline, fetched + usage.RETRY))
        signed_out = {"fetched_at": fetched, "claude": {"error": "sign in again"}}
        self.assertFalse(usage.needs_refresh(signed_out, fetched + usage.RETRY))
        self.assertTrue(usage.needs_refresh({}, fetched))

    def test_if_stale_publishes_only_when_text_changes(self):
        now = dt.datetime(2030, 1, 2, 11, 0).timestamp()
        cache = {"fetched_at": now, "claude": {"windows": {
            "claude_5h": usage.window("Claude 5h", 0, now + 2 * 3600 + 30)}}}
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "usage.json").write_text(json.dumps(cache))
            with patch.multiple(usage, ROOT=root, CACHE=root / "usage.json",
                                PUBLISHED=root / "published"), \
                    patch.object(usage, "publish") as publish, \
                    patch.object(usage, "refresh") as refresh, \
                    patch.object(usage.sys, "argv", ["usage.py", "--if-stale"]):
                for offset in (0, 10, 60):
                    with patch.object(usage.time, "time", return_value=now + offset):
                        usage.main()
            refresh.assert_not_called()
        # 2h at first, unchanged ten seconds later, then 1h once a minute has passed.
        self.assertEqual([call.args[0]["claude"] for call in publish.call_args_list],
                         ["Claude 100% 2h", "Claude 100% 1h"])

    def test_redirects_never_forward_credentials(self):
        request = urllib.request.Request(usage.CLAUDE_URL, headers={"Authorization": "Bearer TEST_ONLY"})
        for code in (301, 302, 303, 307, 308):
            for target in (usage.CLAUDE_URL, "https://example.invalid/", "http://example.invalid/"):
                with self.assertRaises(urllib.error.HTTPError):
                    usage.NoRedirects().redirect_request(request, None, code, "moved", {}, target)

    def test_only_fixed_provider_urls_are_accepted(self):
        with patch.object(usage.urllib.request, "build_opener") as opener:
            for url in ("http://api.anthropic.com/api/oauth/usage", "https://example.invalid/"):
                with self.assertRaises(ValueError):
                    usage.get_json(url, {"Authorization": "Bearer TEST_ONLY"})
            opener.assert_not_called()
            opener.return_value.open.return_value.__enter__.return_value.read.return_value = b'{}'
            self.assertEqual(usage.get_json(usage.CLAUDE_URL, {"Authorization": "Bearer TEST_ONLY"}), {})
            proxy, redirects = opener.call_args.args
            self.assertEqual(proxy.proxies, {})
            self.assertIsInstance(redirects, usage.NoRedirects)

    def test_errors_do_not_echo_private_details(self):
        with patch.object(usage, "claude_usage", side_effect=RuntimeError("TEST_PRIVATE_DETAIL")):
            self.assertEqual(usage.safe_fetch(usage.claude_usage), {"error": "usage unavailable"})
        stderr = io.StringIO()
        with patch.object(usage, "main", side_effect=RuntimeError("TEST_PRIVATE_DETAIL")):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(usage.entrypoint(), 1)
        self.assertNotIn("TEST_PRIVATE_DETAIL", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_cache_drops_account_fields_and_arbitrary_strings(self):
        cache = {"fetched_at": 100, "access_token": "TEST_ONLY", "email": "user@example.invalid",
                 "claude": {"error": "TEST_PRIVATE_DETAIL"},
                 "codex": {"windows": {"codex_primary": {
                     "label": "TEST_PRIVATE_DETAIL", "remaining": 75, "reset": 200}}}}
        clean = usage.sanitize_cache(cache)
        self.assertNotIn("TEST_", json.dumps(clean))
        self.assertNotIn("email", clean)
        self.assertNotIn("access_token", clean)

    def test_cache_write_is_private_and_symlink_reads_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(usage, "ROOT", root), patch.object(usage, "CACHE", root / "usage.json"):
                with patch.object(usage, "claude_usage", return_value={}), patch.object(usage, "codex_usage", return_value={}):
                    usage.refresh()
                self.assertEqual(usage.CACHE.stat().st_mode & 0o777, 0o600)
                self.assertEqual(usage.load_cache()["claude"], {"error": "usage unavailable"})
                usage.CACHE.unlink()
                target = root / "other.json"
                target.write_text('{"private": "TEST_ONLY"}')
                usage.CACHE.symlink_to(target)
                self.assertEqual(usage.load_cache(), {})

    def test_claude_keychain_fallback_only_on_macos(self):
        from subprocess import CompletedProcess
        keychain = CompletedProcess([], 0, '{"claudeAiOauth": {"accessToken": "TEST_ONLY"}}', "")
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(usage.os.environ, {"CLAUDE_CONFIG_DIR": directory}), \
                patch.object(usage, "get_json", return_value={}) as get_json, \
                patch.object(usage.subprocess, "run", return_value=keychain) as run:
            with patch.object(usage.sys, "platform", "linux"):
                self.assertEqual(usage.safe_fetch(usage.claude_usage), {"error": "login unavailable"})
            run.assert_not_called()
            get_json.assert_not_called()
            with patch.object(usage.sys, "platform", "darwin"):
                self.assertEqual(usage.claude_usage(), {})
            self.assertEqual(run.call_args.args[0][0], "/usr/bin/security")
            self.assertEqual(get_json.call_args.args[1]["Authorization"], "Bearer TEST_ONLY")

    def test_metadata_noop_and_single_sidebar_section(self):
        from subprocess import CompletedProcess
        with patch.object(usage.subprocess, "run", return_value=CompletedProcess([], 0, "", "")):
            self.assertEqual(usage.herdr("workspace", "report-metadata", "w1"), {})
        spaces = [{"workspace_id": "w1"}, {"workspace_id": "w2", "tokens": {"subscription_header": "old"}}]
        with patch.object(usage, "herdr", return_value={"result": {"workspaces": spaces}}) as cli:
            usage.publish(usage.sidebar_tokens({}))
        self.assertIn("w1", cli.call_args_list[1].args)
        self.assertIn("w2", cli.call_args_list[2].args)
        self.assertNotIn("--token", cli.call_args_list[2].args)


if __name__ == "__main__":
    unittest.main()
