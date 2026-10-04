"""Small offline checks; all fixtures are synthetic, never account data."""
import contextlib
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
        self.assertEqual(usage.format_window(value, 201), "Claude 5h: refresh due")
        with self.assertRaises(ValueError):
            usage.window("Claude 5h", float("nan"), None)

    def test_stale_cache_does_not_display_old_balance(self):
        cache = {"fetched_at": 100, "claude": {"windows": {
            "claude_5h": usage.window("Claude 5h", 25, 100000)}}}
        tokens = usage.sidebar_tokens(cache, now=100 + usage.MAX_AGE)
        self.assertEqual(tokens["claude_5h"], "Claude: refresh pending")
        self.assertNotIn("75%", str(tokens))

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

    def test_metadata_noop_and_single_sidebar_section(self):
        from subprocess import CompletedProcess
        with patch.object(usage.subprocess, "run", return_value=CompletedProcess([], 0, "", "")):
            self.assertEqual(usage.herdr("workspace", "report-metadata", "w1"), {})
        spaces = [{"workspace_id": "w1"}, {"workspace_id": "w2", "tokens": {"subscription_header": "old"}}]
        with patch.object(usage, "herdr", return_value={"result": {"workspaces": spaces}}) as cli:
            usage.publish({})
        self.assertIn("w1", cli.call_args_list[1].args)
        self.assertIn("w2", cli.call_args_list[2].args)
        self.assertNotIn("--token", cli.call_args_list[2].args)


if __name__ == "__main__":
    unittest.main()
