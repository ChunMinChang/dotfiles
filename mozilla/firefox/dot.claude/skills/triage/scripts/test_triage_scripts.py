#!/usr/bin/env python3
"""Tests for the Firefox bug triage skill helper scripts.

Run from the repo root:

    python3 -m unittest discover -s mozilla/firefox/dot.claude/skills/triage/scripts

Stdlib only; mirrors the style of claude/test_session_sync.py.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

# Import the modules under test.
sys.path.insert(0, os.path.dirname(__file__))
import apply_pending
import bmo_rest
import pending_store
import render_report
import scope_profiles
import triage_paths


# ---------------------------------------------------------------------------
# scope_profiles
# ---------------------------------------------------------------------------


class TestScopeProfiles(unittest.TestCase):

    def test_media_inference(self):
        self.assertEqual(
            scope_profiles.infer_profile("Core", "Audio/Video: Playback"), "media"
        )
        self.assertEqual(scope_profiles.infer_profile("Core", "Web Audio"), "media")

    def test_web_conferencing_inference(self):
        self.assertEqual(
            scope_profiles.infer_profile("Core", "WebRTC: Networking"),
            "web-conferencing",
        )
        self.assertEqual(
            scope_profiles.infer_profile("Core", "DOM: Screen Capture"),
            "web-conferencing",
        )

    def test_graphics_inference(self):
        self.assertEqual(
            scope_profiles.infer_profile("Core", "Graphics: WebRender"),
            "graphics",
        )
        self.assertEqual(
            scope_profiles.infer_profile("Core", "Web Painting"),
            "graphics",
        )

    def test_android_inference(self):
        self.assertEqual(
            scope_profiles.infer_profile("Firefox for Android", "Media"),
            "android",
        )
        self.assertEqual(
            scope_profiles.infer_profile("GeckoView", "Media"),
            "android",
        )
        # Android wins regardless of component.
        self.assertEqual(
            scope_profiles.infer_profile("GeckoView", "General"),
            "android",
        )

    def test_default_with_warning(self):
        buf = io.StringIO()
        with mock.patch("sys.stderr", buf):
            result = scope_profiles.infer_profile("Toolkit", "Storage")
        self.assertEqual(result, "media")
        self.assertIn("no profile match", buf.getvalue())

    def test_resolve_profile_known(self):
        self.assertEqual(scope_profiles.resolve_profile("Graphics"), "graphics")
        self.assertEqual(scope_profiles.resolve_profile(" media "), "media")
        self.assertIsNone(scope_profiles.resolve_profile(None))

    def test_resolve_profile_unknown(self):
        with self.assertRaises(ValueError) as ctx:
            scope_profiles.resolve_profile("not-a-profile")
        msg = str(ctx.exception)
        # Error message must list the valid options.
        for key in scope_profiles.PROFILES:
            self.assertIn(key, msg)

    def test_components_and_product(self):
        comps = scope_profiles.components_for("media")
        self.assertIn("Audio/Video", comps)
        # Returned list is a copy — mutation must not bleed into the table.
        comps.append("FAKE")
        self.assertNotIn("FAKE", scope_profiles.components_for("media"))
        self.assertEqual(scope_profiles.product_for("media"), "Core")
        self.assertEqual(
            scope_profiles.product_for("android"),
            ["Firefox for Android", "GeckoView"],
        )


# ---------------------------------------------------------------------------
# pending_store
# ---------------------------------------------------------------------------


class TestPendingStore(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="triage-test-")
        triage_paths.set_override(self._tmp)

    def tearDown(self):
        triage_paths.clear_override()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    # -- paths

    def test_paths_respect_override(self):
        self.assertEqual(pending_store.state_dir(), self._tmp)
        self.assertEqual(
            pending_store.pending_path(123),
            os.path.join(self._tmp, "triage-bug-123", "pending.json"),
        )
        self.assertEqual(
            pending_store.bug_snapshot_path(123),
            os.path.join(self._tmp, "triage-bug-123", "bug.json"),
        )
        self.assertEqual(
            pending_store.log_path(),
            os.path.join(self._tmp, "triage-log.json"),
        )

    # -- save / load round-trip

    def test_save_and_load_round_trip(self):
        payload = {
            "schema_version": 1,
            "bug_id": 42,
            "created_at": "2026-05-14T10:00:00Z",
            "branch": "1a",
            "comment": "hello",
        }
        path = pending_store.save_pending(payload)
        self.assertTrue(os.path.exists(path))
        loaded = pending_store.load_pending(42)
        self.assertEqual(loaded, payload)

    def test_save_requires_bug_id_and_created_at(self):
        with self.assertRaises(ValueError):
            pending_store.save_pending({"created_at": "x"})
        with self.assertRaises(ValueError):
            pending_store.save_pending({"bug_id": 1})

    def test_load_missing_returns_none(self):
        self.assertIsNone(pending_store.load_pending(9999))

    def test_delete_pending_idempotent(self):
        payload = {"bug_id": 7, "created_at": "2026-05-14T10:00:00Z"}
        pending_store.save_pending(payload)
        self.assertTrue(pending_store.delete_pending(7))
        self.assertFalse(pending_store.delete_pending(7))

    # -- atomicity

    def test_save_is_atomic(self):
        payload = {"bug_id": 1, "created_at": "2026-05-14T10:00:00Z"}
        pending_store.save_pending(payload)
        # No leftover .tmp in the per-bug folder after a successful write.
        bug_dir = os.path.dirname(pending_store.pending_path(1))
        leftovers = [f for f in os.listdir(bug_dir) if f.endswith(".tmp")]
        self.assertEqual(leftovers, [])

    # -- stale detection

    def test_is_stale_true_when_bug_newer(self):
        payload = {"bug_id": 1, "created_at": "2026-05-14T10:00:00Z"}
        self.assertTrue(pending_store.is_stale(payload, "2026-05-14T10:00:01Z"))

    def test_is_stale_false_when_bug_older_or_equal(self):
        payload = {"bug_id": 1, "created_at": "2026-05-14T10:00:00Z"}
        self.assertFalse(pending_store.is_stale(payload, "2026-05-14T10:00:00Z"))
        self.assertFalse(pending_store.is_stale(payload, "2026-05-13T10:00:00Z"))

    def test_is_stale_handles_missing_inputs(self):
        self.assertFalse(pending_store.is_stale(None, "anything"))
        self.assertFalse(pending_store.is_stale({"bug_id": 1}, "x"))
        self.assertFalse(
            pending_store.is_stale(
                {"bug_id": 1, "created_at": "2026-05-14T10:00:00Z"}, ""
            )
        )

    # -- log append

    def test_append_log_creates_array(self):
        pending_store.append_log_entry({"bug_id": 1, "decision": "skipped"})
        pending_store.append_log_entry({"bug_id": 2, "decision": "triaged"})
        with open(pending_store.log_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["bug_id"], 1)
        self.assertEqual(data[1]["decision"], "triaged")

    def test_append_log_survives_corrupt_existing_file(self):
        os.makedirs(pending_store.state_dir(), exist_ok=True)
        with open(pending_store.log_path(), "w", encoding="utf-8") as f:
            f.write("not-json garbage")
        pending_store.append_log_entry({"bug_id": 3, "decision": "ok"})
        with open(pending_store.log_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, [{"bug_id": 3, "decision": "ok"}])

    def test_now_iso_utc_shape(self):
        ts = pending_store.now_iso_utc()
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# ---------------------------------------------------------------------------
# bmo_rest
# ---------------------------------------------------------------------------


class TestBmoRestKeyDiscovery(unittest.TestCase):

    def setUp(self):
        self._tmp_home = tempfile.mkdtemp(prefix="triage-home-")
        self._home_patcher = mock.patch.dict(os.environ, {"HOME": self._tmp_home})
        self._home_patcher.start()
        # Make sure env var doesn't leak from the host.
        os.environ.pop("BMO_API_KEY", None)

    def tearDown(self):
        self._home_patcher.stop()
        import shutil

        shutil.rmtree(self._tmp_home, ignore_errors=True)

    def test_env_var_wins(self):
        with mock.patch.dict(os.environ, {"BMO_API_KEY": "env-key"}):
            self.assertEqual(bmo_rest.get_api_key(), "env-key")

    def test_file_fallback(self):
        cfg_dir = os.path.join(self._tmp_home, ".config", "bmo")
        os.makedirs(cfg_dir, exist_ok=True)
        key_path = os.path.join(cfg_dir, "api_key")
        with open(key_path, "w", encoding="utf-8") as f:
            f.write("file-key\n")
        os.chmod(key_path, 0o600)
        self.assertEqual(bmo_rest.get_api_key(), "file-key")

    def test_no_key_returns_none(self):
        self.assertIsNone(bmo_rest.get_api_key())

    def test_world_readable_warning(self):
        cfg_dir = os.path.join(self._tmp_home, ".config", "bmo")
        os.makedirs(cfg_dir, exist_ok=True)
        key_path = os.path.join(cfg_dir, "api_key")
        with open(key_path, "w", encoding="utf-8") as f:
            f.write("loose-key\n")
        os.chmod(key_path, 0o644)
        buf = io.StringIO()
        with mock.patch("sys.stderr", buf):
            key = bmo_rest.get_api_key()
        self.assertEqual(key, "loose-key")
        self.assertIn("chmod 600", buf.getvalue())


class TestBmoRestRedaction(unittest.TestCase):

    def test_redact_masks_api_key(self):
        out = bmo_rest._redact(
            {
                "X-BUGZILLA-API-KEY": "secret",
                "Accept": "application/json",
            }
        )
        self.assertEqual(out["X-BUGZILLA-API-KEY"], "***redacted***")
        self.assertEqual(out["Accept"], "application/json")

    def test_redact_case_insensitive(self):
        out = bmo_rest._redact({"x-bugzilla-api-key": "secret"})
        self.assertEqual(out["x-bugzilla-api-key"], "***redacted***")

    def test_bmoerror_repr_does_not_leak(self):
        e = bmo_rest.BMOError("boom", status_code=500, body={"x": 1})
        self.assertIn("status=500", repr(e))
        self.assertNotIn("secret", repr(e))


class TestBmoRestUrlBuilding(unittest.TestCase):

    def test_build_url_relative(self):
        url = bmo_rest._build_url("/bug/1")
        self.assertEqual(url, "https://bugzilla.mozilla.org/rest/bug/1")

    def test_build_url_with_params(self):
        url = bmo_rest._build_url("/bug", {"id": 1, "skip": None})
        self.assertIn("id=1", url)
        self.assertNotIn("skip", url)


class TestBmoRestWriteGate(unittest.TestCase):
    """Write helpers must never reach the network without a key."""

    def test_post_comment_without_key_raises_before_request(self):
        with mock.patch.object(bmo_rest, "_request") as m:
            with self.assertRaises(bmo_rest.BMOError):
                bmo_rest.post_comment(1, "hi", api_key=None)
            m.assert_not_called()

    def test_set_fields_without_key_raises_before_request(self):
        with mock.patch.object(bmo_rest, "_request") as m:
            with self.assertRaises(bmo_rest.BMOError):
                bmo_rest.set_fields(1, {"priority": "P2"}, api_key=None)
            m.assert_not_called()

    def test_set_needinfo_without_key_raises_before_request(self):
        with mock.patch.object(bmo_rest, "_request") as m:
            with self.assertRaises(bmo_rest.BMOError):
                bmo_rest.set_needinfo(1, "a@b", api_key=None)
            m.assert_not_called()

    def test_set_fields_rejects_empty(self):
        with self.assertRaises(ValueError):
            bmo_rest.set_fields(1, {}, api_key="k")


class TestBmoRestRequestShape(unittest.TestCase):

    def _mock_response(self, payload, status=200):
        class FakeResp:
            def __init__(self, data, code):
                self._data = data
                self.status = code

            def read(self):
                return self._data

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return FakeResp(json.dumps(payload).encode("utf-8"), status)

    def test_get_bug_returns_first_bug(self):
        fake = self._mock_response({"bugs": [{"id": 1, "summary": "x"}]})
        with mock.patch("urllib.request.urlopen", return_value=fake) as m:
            bug = bmo_rest.get_bug(1)
        self.assertEqual(bug["id"], 1)
        # Verify we issued GET and never set the Content-Type header
        # (no body on GET).
        req = m.call_args[0][0]
        self.assertEqual(req.get_method(), "GET")

    def test_get_bug_missing_raises(self):
        fake = self._mock_response({"bugs": []})
        with mock.patch("urllib.request.urlopen", return_value=fake):
            with self.assertRaises(bmo_rest.BMOError) as ctx:
                bmo_rest.get_bug(99999999)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_post_comment_sends_body_and_key(self):
        fake = self._mock_response({"id": 12345})
        with mock.patch("urllib.request.urlopen", return_value=fake) as m:
            bmo_rest.post_comment(1, "hello", api_key="K")
        req = m.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["comment"], "hello")
        self.assertFalse(body["is_private"])
        # Header lookup is case-insensitive in urllib Request internals
        # but the public dict uses the original casing; check via items.
        headers = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(headers["x-bugzilla-api-key"], "K")

    def test_set_needinfo_sends_flag_shape(self):
        fake = self._mock_response({"bugs": []})
        with mock.patch("urllib.request.urlopen", return_value=fake) as m:
            bmo_rest.set_needinfo(1, "user@example.com", api_key="K")
        req = m.call_args[0][0]
        self.assertEqual(req.get_method(), "PUT")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["flags"][0]["name"], "needinfo")
        self.assertEqual(body["flags"][0]["status"], "?")
        self.assertEqual(body["flags"][0]["requestee"], "user@example.com")

    def test_http_error_parses_retry_after(self):
        import urllib.error

        err = urllib.error.HTTPError(
            url="https://x",
            code=429,
            msg="Too Many",
            hdrs={"Retry-After": "12"},
            fp=io.BytesIO(b'{"error": true, "message": "slow down"}'),
        )
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(bmo_rest.BMOError) as ctx:
                bmo_rest.get_bug(1)
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(ctx.exception.retry_after, 12.0)


# ---------------------------------------------------------------------------
# apply_pending
# ---------------------------------------------------------------------------


def _make_bug(bug_id=1, last_change_time="2026-05-14T10:00:00Z", **extra):
    bug = {
        "id": bug_id,
        "summary": "test bug",
        "status": "NEW",
        "product": "Core",
        "component": "Audio/Video: Playback",
        "creation_time": "2026-05-14T09:00:00Z",
        "last_change_time": last_change_time,
        "severity": "--",
        "priority": "--",
        "keywords": [],
        "flags": [],
        "comments": [],
    }
    bug.update(extra)
    return bug


def _make_pending(bug_id=1, branch="1b", **extra):
    payload = {
        "schema_version": 1,
        "bug_id": bug_id,
        "title": "test",
        "branch": branch,
        "scope": "media",
        "created_at": "2026-05-14T09:30:00Z",
        "comment": "Reproduced. Setting P2/S3.",
        "priority": "P2",
        "severity": "S3",
    }
    payload.update(extra)
    return payload


class _ApplyTestCase(unittest.TestCase):
    """Shared scaffolding for apply_pending tests."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="triage-apply-")
        triage_paths.set_override(self._tmp)
        self._env_patcher = mock.patch.dict(os.environ, {"BMO_API_KEY": "test-key"})
        self._env_patcher.start()

    def tearDown(self):
        self._env_patcher.stop()
        triage_paths.clear_override()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)


class TestApplyPendingExitCodes(_ApplyTestCase):

    def test_missing_pending_file_exits_2(self):
        with mock.patch.object(bmo_rest, "get_bug") as fetch:
            code = apply_pending.run(9999, dry_run=True, assume_yes=True)
        self.assertEqual(code, 2)
        fetch.assert_not_called()

    def test_stale_draft_exits_6(self):
        pending_store.save_pending(_make_pending(bug_id=1))
        bug = _make_bug(bug_id=1, last_change_time="2026-05-14T10:00:00Z")
        with mock.patch.object(bmo_rest, "get_bug", return_value=bug):
            code = apply_pending.run(1, dry_run=True, assume_yes=True)
        self.assertEqual(code, 6)
        # Pending file preserved.
        self.assertIsNotNone(pending_store.load_pending(1))

    def test_missing_api_key_exits_3(self):
        pending_store.save_pending(_make_pending(bug_id=2))
        bug = _make_bug(bug_id=2, last_change_time="2026-05-14T09:00:00Z")
        with mock.patch.dict(os.environ, {"BMO_API_KEY": ""}, clear=False):
            os.environ.pop("BMO_API_KEY", None)
            with mock.patch.object(bmo_rest, "get_api_key", return_value=None):
                with mock.patch.object(bmo_rest, "get_bug", return_value=bug):
                    code = apply_pending.run(2, dry_run=False, assume_yes=True)
        self.assertEqual(code, 3)
        self.assertIsNotNone(pending_store.load_pending(2))

    def test_dry_run_succeeds_without_calls(self):
        pending_store.save_pending(_make_pending(bug_id=3))
        bug = _make_bug(bug_id=3, last_change_time="2026-05-14T09:00:00Z")
        with mock.patch.object(
            bmo_rest, "get_bug", return_value=bug
        ), mock.patch.object(bmo_rest, "set_fields") as sf, mock.patch.object(
            bmo_rest, "post_comment"
        ) as pc, mock.patch.object(
            bmo_rest, "set_needinfo"
        ) as sn:
            code = apply_pending.run(3, dry_run=True, assume_yes=True)
        self.assertEqual(code, 0)
        sf.assert_not_called()
        pc.assert_not_called()
        sn.assert_not_called()
        # Dry run does not delete the pending file.
        self.assertIsNotNone(pending_store.load_pending(3))

    def test_full_success_deletes_pending_and_logs(self):
        pending_store.save_pending(_make_pending(bug_id=4))
        bug = _make_bug(bug_id=4, last_change_time="2026-05-14T09:00:00Z")
        with mock.patch.object(
            bmo_rest, "get_bug", return_value=bug
        ), mock.patch.object(
            bmo_rest, "set_fields", return_value={}
        ), mock.patch.object(
            bmo_rest, "post_comment", return_value={}
        ), mock.patch.object(
            bmo_rest, "set_needinfo", return_value={}
        ):
            code = apply_pending.run(4, dry_run=False, assume_yes=True)
        self.assertEqual(code, 0)
        self.assertIsNone(pending_store.load_pending(4))
        with open(pending_store.log_path(), "r", encoding="utf-8") as f:
            log = json.load(f)
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0]["bug_id"], 4)
        self.assertEqual(log[0]["decision"], "triaged")

    def test_partial_failure_preserves_pending(self):
        pending_store.save_pending(_make_pending(bug_id=5))
        bug = _make_bug(bug_id=5, last_change_time="2026-05-14T09:00:00Z")
        err = bmo_rest.BMOError("boom", status_code=500)
        with mock.patch.object(
            bmo_rest, "get_bug", return_value=bug
        ), mock.patch.object(
            bmo_rest, "set_fields", return_value={}
        ), mock.patch.object(
            bmo_rest, "post_comment", side_effect=err
        ), mock.patch.object(
            bmo_rest, "set_needinfo"
        ):
            code = apply_pending.run(5, dry_run=False, assume_yes=True)
        self.assertEqual(code, 4)
        # Pending preserved for retry; log entry records partial.
        self.assertIsNotNone(pending_store.load_pending(5))
        with open(pending_store.log_path(), "r", encoding="utf-8") as f:
            log = json.load(f)
        self.assertEqual(log[0]["decision"], "apply_partial")
        self.assertIn("post_comment", log[0]["failed"])

    def test_user_abort_exits_5(self):
        pending_store.save_pending(_make_pending(bug_id=6))
        bug = _make_bug(bug_id=6, last_change_time="2026-05-14T09:00:00Z")
        # Empty input on stdin means abort.
        stdin = io.StringIO("\n")
        with mock.patch.object(
            bmo_rest, "get_bug", return_value=bug
        ), mock.patch.object(bmo_rest, "set_fields") as sf, mock.patch.object(
            bmo_rest, "post_comment"
        ) as pc:
            code = apply_pending.run(6, dry_run=False, assume_yes=False, stdin=stdin)
        self.assertEqual(code, 5)
        sf.assert_not_called()
        pc.assert_not_called()
        # Pending preserved.
        self.assertIsNotNone(pending_store.load_pending(6))


class TestApplyPendingFieldReconciliation(unittest.TestCase):

    def test_skip_already_set_scalar(self):
        pending = _make_pending(priority="P2", severity="S3")
        current = _make_bug(priority="P2", severity="S4")
        fields = apply_pending.build_field_payload(pending, current)
        # priority already P2 → skipped; severity differs → included.
        self.assertNotIn("priority", fields)
        self.assertEqual(fields["severity"], "S3")

    def test_compute_missing_blocks(self):
        pending = _make_pending(blocks_add=[1, 2, 3])
        current = _make_bug(blocks=[2])
        fields = apply_pending.build_field_payload(pending, current)
        self.assertEqual(fields["blocks"], {"add": [1, 3]})

    def test_no_changes_returns_empty(self):
        pending = _make_pending(priority="P2", severity="S3")
        current = _make_bug(priority="P2", severity="S3")
        fields = apply_pending.build_field_payload(pending, current)
        self.assertEqual(fields, {})


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------


class TestRenderReport(unittest.TestCase):

    def test_header_contains_bug_id_and_url(self):
        bug = _make_bug(bug_id=42, summary="Foo")
        body = render_report.render(bug, _make_pending(bug_id=42), "media", {}, [])
        self.assertIn("Bug 42 Triage Analysis", body)
        self.assertIn("https://bugzilla.mozilla.org/show_bug.cgi?id=42", body)

    def test_includes_scope_and_assessment(self):
        bug = _make_bug(bug_id=7, severity="S3", priority="P3")
        pending = _make_pending(bug_id=7, severity="S2", priority="P2")
        body = render_report.render(bug, pending, "graphics", {}, [])
        self.assertIn("Scope:** graphics", body)
        self.assertIn("Suggested Severity:** S2", body)
        self.assertIn("Suggested Priority:** P2", body)

    def test_classification_table_present(self):
        bug = _make_bug(bug_id=8)
        body = render_report.render(bug, {}, "media", {}, [])
        self.assertIn("## Classification", body)
        for label in ("Clear STR", "Test Case", "Crash Stack", "Fuzzing"):
            self.assertIn(label, body)

    def test_draft_response_block(self):
        pending = _make_pending(comment="Hello there.")
        body = render_report.render(_make_bug(), pending, "media", {}, [])
        self.assertIn("## Draft Response", body)
        self.assertIn("Hello there.", body)

    def test_usage_footer_when_provided(self):
        body = render_report.render(
            _make_bug(bug_id=1),
            {},
            "media",
            {"bugs_fetched": 12, "searches_issued": 3, "inaccessible": 1},
            [],
        )
        self.assertIn("Bugs fetched: 12", body)
        self.assertIn("Inaccessible bugs (permissions / deleted): 1", body)

    def test_regression_section_only_when_signal_present(self):
        body_plain = render_report.render(
            _make_bug(bug_id=1),
            {},
            "media",
            {},
            [],
        )
        self.assertNotIn("Regression Timeline", body_plain)
        body_reg = render_report.render(
            _make_bug(bug_id=1, regressed_by=[111, 222]),
            {},
            "media",
            {},
            [],
        )
        self.assertIn("Regression Timeline", body_reg)
        self.assertIn("111", body_reg)


class TestRenderReportCli(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="render-cli-")

    def tearDown(self):
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def _write(self, name, payload):
        path = os.path.join(self._tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        return path

    def test_cli_writes_default_path(self):
        bug_path = self._write("bug.json", _make_bug(bug_id=33))
        pending_path = self._write("pending.json", _make_pending(bug_id=33))
        out_path = os.path.join(self._tmp, "out.md")
        code = render_report.main(
            [
                "--bug",
                bug_path,
                "--pending",
                pending_path,
                "--scope",
                "media",
                "--out",
                out_path,
            ]
        )
        self.assertEqual(code, 0)
        with open(out_path, "r", encoding="utf-8") as f:
            body = f.read()
        self.assertIn("Bug 33 Triage Analysis", body)

    def test_cli_invalid_input_exits_1(self):
        # Missing --bug/--pending and missing --out
        code = render_report.main([])
        self.assertEqual(code, 1)


# ---------------------------------------------------------------------------
# triage_paths
# ---------------------------------------------------------------------------


class TestTriagePathsResolution(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="triage-paths-")
        self._cfg = os.path.join(self._tmp, "config.toml")
        self._cfg_patcher = mock.patch.object(triage_paths, "CONFIG_PATH", self._cfg)
        self._cfg_patcher.start()
        triage_paths.clear_override()

    def tearDown(self):
        self._cfg_patcher.stop()
        triage_paths.clear_override()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_unset_raises(self):
        with self.assertRaises(triage_paths.OutputRootUnset):
            triage_paths.output_root()

    def test_override_wins_over_config(self):
        triage_paths.persist_output_dir("/from-config")
        triage_paths.set_override("/from-override")
        self.assertEqual(triage_paths.output_root(), "/from-override")

    def test_config_when_no_override(self):
        triage_paths.persist_output_dir(self._tmp)
        self.assertEqual(triage_paths.output_root(), self._tmp)

    def test_per_bug_paths(self):
        triage_paths.set_override("/root")
        self.assertEqual(triage_paths.bug_dir(42), "/root/triage-bug-42")
        self.assertEqual(triage_paths.report_path(42), "/root/triage-bug-42/triage.md")
        self.assertEqual(
            triage_paths.pending_path(42), "/root/triage-bug-42/pending.json"
        )
        self.assertEqual(
            triage_paths.test_page_path(42), "/root/triage-bug-42/test.html"
        )
        self.assertEqual(
            triage_paths.bug_snapshot_path(42), "/root/triage-bug-42/bug.json"
        )
        self.assertEqual(triage_paths.log_path(), "/root/triage-log.json")

    def test_bug_id_coerced_from_string(self):
        triage_paths.set_override("/root")
        self.assertEqual(triage_paths.bug_dir("99"), "/root/triage-bug-99")
        self.assertEqual(
            triage_paths.pending_path("99"), "/root/triage-bug-99/pending.json"
        )

    def test_persist_writes_and_reads_back(self):
        triage_paths.persist_output_dir(self._tmp)
        with open(self._cfg, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn("output_dir", text)
        self.assertIn(self._tmp, text)
        self.assertEqual(triage_paths.read_output_dir_from_config(), self._tmp)

    def test_persist_replaces_existing_value(self):
        triage_paths.persist_output_dir("/first")
        triage_paths.persist_output_dir("/second")
        self.assertEqual(triage_paths.read_output_dir_from_config(), "/second")
        # No duplicate line in the file.
        with open(self._cfg, "r", encoding="utf-8") as f:
            occurrences = sum(1 for line in f if line.strip().startswith("output_dir"))
        self.assertEqual(occurrences, 1)

    def test_persist_preserves_other_fields(self):
        with open(self._cfg, "w", encoding="utf-8") as f:
            f.write('api_key = "shh"\n')
            f.write('default_scope = "media"\n')
        triage_paths.persist_output_dir("/root")
        with open(self._cfg, "r", encoding="utf-8") as f:
            text = f.read()
        self.assertIn('api_key = "shh"', text)
        self.assertIn('default_scope = "media"', text)
        self.assertIn('output_dir = "/root"', text)

    def test_toml_ignores_comments_and_whitespace(self):
        with open(self._cfg, "w", encoding="utf-8") as f:
            f.write("# header comment\n")
            f.write("\n")
            f.write('output_dir = "/path/from/toml"  # trailing\n')
            f.write('default_scope = "graphics"\n')
        self.assertEqual(triage_paths.read_output_dir_from_config(), "/path/from/toml")
        self.assertEqual(triage_paths.read_default_scope_from_config(), "graphics")


class TestTriagePathsCli(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="triage-cli-")
        self._cfg = os.path.join(self._tmp, "config.toml")
        self._cfg_patcher = mock.patch.object(triage_paths, "CONFIG_PATH", self._cfg)
        self._cfg_patcher.start()

    def tearDown(self):
        self._cfg_patcher.stop()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def _capture(self, argv):
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            code = triage_paths._cli(argv)
        return code, buf.getvalue().strip()

    def test_get_output_dir_empty_when_unset(self):
        code, out = self._capture(["--get-output-dir"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_set_then_get_round_trips(self):
        code, out = self._capture(["--set-output-dir", "/wonderland"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "/wonderland")
        code, out = self._capture(["--get-output-dir"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "/wonderland")

    def test_config_path_action(self):
        code, out = self._capture(["--config-path"])
        self.assertEqual(code, 0)
        self.assertEqual(out, self._cfg)


# ---------------------------------------------------------------------------
# Snapshot-based stale check
# ---------------------------------------------------------------------------


class TestSnapshotStaleCheck(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="triage-snap-")
        triage_paths.set_override(self._tmp)

    def tearDown(self):
        triage_paths.clear_override()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_no_snapshot_returns_false(self):
        self.assertFalse(
            pending_store.is_stale_against_snapshot(1, "2026-05-14T10:00:00Z")
        )

    def test_snapshot_older_than_fresh_is_stale(self):
        pending_store.save_bug_snapshot(
            1, {"id": 1, "last_change_time": "2026-05-14T09:00:00Z"}
        )
        self.assertTrue(
            pending_store.is_stale_against_snapshot(1, "2026-05-14T10:00:00Z")
        )

    def test_snapshot_equal_or_newer_not_stale(self):
        pending_store.save_bug_snapshot(
            2, {"id": 2, "last_change_time": "2026-05-14T10:00:00Z"}
        )
        self.assertFalse(
            pending_store.is_stale_against_snapshot(2, "2026-05-14T10:00:00Z")
        )
        self.assertFalse(
            pending_store.is_stale_against_snapshot(2, "2026-05-14T09:00:00Z")
        )

    def test_snapshot_round_trip(self):
        bug = {"id": 5, "summary": "x", "last_change_time": "2026-05-14T10:00:00Z"}
        pending_store.save_bug_snapshot(5, bug)
        loaded = pending_store.load_bug_snapshot(5)
        self.assertEqual(loaded, bug)


if __name__ == "__main__":
    unittest.main()
