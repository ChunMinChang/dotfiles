#!/usr/bin/env python3
"""Tests for the media-security-report skill helper scripts.

Run from the repo root:

    python3 -m unittest discover -s mozilla/firefox/dot.codex/skills/media-security-report/scripts

Stdlib only, no network, no Firefox checkout required; mirrors the style of
the triage suite next door.
"""

import os
import re
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import channel_policy
import media_lib_facts
import validate_media_report as validator


SKILL_DIR = Path(__file__).resolve().parent.parent
REFERENCES = SKILL_DIR / "references"


def write_tree(root, files):
    """Materialize a fake checkout: {relative path: contents}."""
    for relative, contents in files.items():
        path = Path(root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(contents), encoding="utf-8")


MINIMAL_CHECKOUT = {
    "mach": "#!/usr/bin/env python3\n",
    "media/moz.build": """\
        with Files("**"):
            BUG_COMPONENT = ("Core", "Audio/Video")

        with Files("openmax_il/**"):
            BUG_COMPONENT = ("Core", "Audio/Video: Playback")
        """,
}


# A report that satisfies the universal core for an upstream library. Tests
# mutate copies of this rather than carrying a fixture file in the repo.
GOOD_REPORT = """\
    # libogg: heap-buffer-overflow in oggpack_look

    ## Attribution
    Human reviewer: A. Reviewer. Finder credit: B. Finder.
    AI usage: no AI was used; verified by a human by hand.

    ## Source revision
    Vendored revision: v1.3.6 (git commit tag).

    ## Reproduction
    Testcase: `./oggtest input-ogg-trigger.ogg` reproduces on the revision above.
    Standalone test: added to the libogg `make check` suite as 01-test-oggpack-look.patch.

    ## Delivery
    Crash input: delivered inline as base64 below, never as an upload.
    Filed as a confidential work item with confidentiality set at creation.

    ## Stack trace
    ```
    #0 oggpack_look bitwise.c:214
    #1 ogg_sync_pageseek framing.c:412
    ```

    ## Analysis
    Root cause: the buffer length check is skipped, so the read runs past the end.
    Impact: out-of-bounds read of up to 4 bytes.
    [oggpack_look](https://gitlab.xiph.org/xiph/ogg/-/blob/v1.3.6/src/bitwise.c#L214)

    ## History
    Introducing commit: unknown; checked git log -S over src/bitwise.c.

    ## Fix
    Proposed fix: 03-fix-oggpack-look.patch, included inline below.

    ## Identifier
    CVE: none assigned at report time.
    """


class TestMozYamlParsing(unittest.TestCase):
    def _parse(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "moz.yaml"
            path.write_text(textwrap.dedent(body), encoding="utf-8")
            return media_lib_facts.parse_moz_yaml(path)

    def test_prefers_nothing_it_was_not_asked_for(self):
        data = self._parse(
            """\
            schema: 1
            origin:
              name: dav1d
              url: https://code.videolan.org/videolan/dav1d
              revision: 54706fc6bc0cdecab7e9593974a4039cc038fca7
            """
        )
        self.assertEqual(data["origin.name"], "dav1d")
        self.assertNotIn("origin.description", data)

    def test_comment_lines_are_not_mistaken_for_values(self):
        # The moz.yaml schema template literally ships these comments; a naive
        # grep for "revision" matches them.
        data = self._parse(
            """\
            origin:
              # Revision to pull in
              # Must be a long or short commit SHA (long preferred)
              revision: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
            """
        )
        self.assertEqual(data["origin.revision"], "a" * 40)

    def test_quoted_and_unquoted_scalars(self):
        data = self._parse(
            """\
            bugzilla:
              product: "Core"
              component: Audio/Video
            """
        )
        self.assertEqual(data["bugzilla.product"], "Core")
        self.assertEqual(data["bugzilla.component"], "Audio/Video")

    def test_nested_blocks_cannot_inject_a_url(self):
        data = self._parse(
            """\
            vendoring:
              url: https://github.com/real/repo
              source-hosting: github
              update-actions:
                - action: copy-file
                  from: include/vcs_version.h.in
                  to: '{yaml_dir}/vcs_version.h'
            """
        )
        self.assertEqual(data["vendoring.url"], "https://github.com/real/repo")

    def test_trailing_comment_stripped_outside_quotes(self):
        data = self._parse(
            """\
            origin:
              revision: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb # latest
            """
        )
        self.assertEqual(data["origin.revision"], "b" * 40)

    def test_release_without_revision(self):
        data = self._parse(
            """\
            origin:
              release: "c5aaf923d80e9f71e0c93d7d99dc1e2f83d7acbf"
            """
        )
        self.assertNotIn("origin.revision", data)
        self.assertEqual(
            data["origin.release"], "c5aaf923d80e9f71e0c93d7d99dc1e2f83d7acbf"
        )


class TestRevisionClassification(unittest.TestCase):
    def test_kinds(self):
        cases = [
            ("a" * 40, ("a" * 40, "full-hash")),
            ("f20ebb8adb", ("f20ebb8adb", "short-hash")),
            ("v1.3.6", ("v1.3.6", "tag")),
            ("3.1.4.1", ("3.1.4.1", "tag")),
            ("", (None, "none")),
            (None, (None, "none")),
        ]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assertEqual(media_lib_facts.classify_revision(raw), expected)

    def test_release_string_with_trailing_timestamp(self):
        # moz.yaml writes: release: v2.8.0 (2026-03-14T10:49:34+01:00).
        revision, kind = media_lib_facts.classify_revision(
            "v2.8.0 (2026-03-14T10:49:34+01:00)."
        )
        self.assertEqual((revision, kind), ("v2.8.0", "tag"))


class TestRevisionSourceFallbacks(unittest.TestCase):
    def test_ffvpx_reads_readme_mozilla(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(
                tmp,
                dict(
                    MINIMAL_CHECKOUT,
                    **{
                        "media/ffvpx/README_MOZILLA": (
                            "The current files are from FFmpeg as of revision "
                            "9917308cc209a885c6870f0345905104c6ea8799\n"
                        ),
                        "media/ffvpx/moz.build": (
                            'with Files("**"):\n'
                            '    BUG_COMPONENT = ("Core", "Audio/Video: Playback")\n'
                        ),
                    },
                ),
            )
            facts = media_lib_facts.collect("ffvpx", Path(tmp))
        self.assertEqual(facts.revision, "9917308cc209a885c6870f0345905104c6ea8799")
        self.assertEqual(facts.revision_kind, "full-hash")
        self.assertIn("README_MOZILLA", facts.revision_source)
        self.assertEqual(facts.bug_component, "Audio/Video: Playback")

    def test_libwebrtc_short_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(
                tmp,
                dict(
                    MINIMAL_CHECKOUT,
                    **{
                        "third_party/libwebrtc/README.mozilla.last-vendor": (
                            "# ./mach python vendor-libwebrtc.py --commit mozpatches\n"
                            "libwebrtc updated on 2026-07-10.\n"
                            "# base of lastest vendoring\n"
                            "f20ebb8adb\n"
                        ),
                    },
                ),
            )
            facts = media_lib_facts.collect("libwebrtc", Path(tmp))
        self.assertEqual(facts.revision, "f20ebb8adb")
        self.assertEqual(facts.revision_kind, "short-hash")

    def test_no_upstream_component_has_no_revision_and_no_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(tmp, MINIMAL_CHECKOUT)
            facts = media_lib_facts.collect("psshparser", Path(tmp))
        self.assertIsNone(facts.revision)
        self.assertEqual(facts.revision_kind, "none")
        self.assertFalse(facts.has_upstream)
        self.assertIsNone(facts.repo_url)
        self.assertEqual(facts.warnings, ())

    def test_missing_revision_on_an_upstream_library_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(
                tmp,
                dict(
                    MINIMAL_CHECKOUT,
                    **{"media/libogg/moz.yaml": "origin:\n  name: libogg\n"},
                ),
            )
            facts = media_lib_facts.collect("libogg", Path(tmp))
        self.assertIsNone(facts.revision)
        self.assertTrue(any("do not invent" in w for w in facts.warnings))


class TestBugComponentResolution(unittest.TestCase):
    def _collect(self, library, extra):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(tmp, dict(MINIMAL_CHECKOUT, **extra))
            return media_lib_facts.collect(library, Path(tmp))

    def test_from_moz_yaml(self):
        facts = self._collect(
            "libpng",
            {
                "media/libpng/moz.yaml": """\
                bugzilla:
                  product: "Core"
                  component: "Graphics: ImageLib"
                origin:
                  revision: cccccccccccccccccccccccccccccccccccccccc
                vendoring:
                  url: https://github.com/pnggroup/libpng
                  source-hosting: github
                """
            },
        )
        self.assertEqual(facts.bug_component, "Graphics: ImageLib")
        self.assertEqual(facts.bug_component_source, "media/libpng/moz.yaml")

    def test_from_own_moz_build(self):
        facts = self._collect(
            "psshparser",
            {
                "media/psshparser/moz.build": (
                    'with Files("**"):\n    BUG_COMPONENT = ("Core", "Audio/Video")\n'
                )
            },
        )
        self.assertEqual(facts.bug_component_source, "media/psshparser/moz.build")

    def test_inherited_glob_from_ancestor_longest_wins(self):
        facts = self._collect("openmax_il", {})
        self.assertEqual(facts.bug_component, "Audio/Video: Playback")
        self.assertEqual(facts.bug_component_source, "media/moz.build")

    def test_wildcard_ancestor_applies_when_no_specific_glob(self):
        facts = self._collect("mozva", {})
        self.assertEqual(facts.bug_component, "Audio/Video")

    def test_unresolvable_component_is_flagged_as_assumed(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(tmp, {"mach": "", "media/moz.build": "# nothing here\n"})
            facts = media_lib_facts.collect("wmf-clearkey", Path(tmp))
        self.assertIn("assumed", facts.bug_component_source)
        self.assertTrue(any("assumed" in w for w in facts.warnings))


class TestCheckoutResolution(unittest.TestCase):
    def test_walks_up_from_a_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(tmp, MINIMAL_CHECKOUT)
            deep = Path(tmp) / "media" / "libogg"
            deep.mkdir(parents=True, exist_ok=True)
            found = media_lib_facts.find_checkout(start=deep)
        self.assertEqual(found, Path(tmp).resolve())

    def test_rejects_a_directory_that_is_not_a_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(media_lib_facts.find_checkout(explicit=tmp))


class TestLibraryResolution(unittest.TestCase):
    def test_id_and_paths(self):
        cases = [
            ("dav1d", "dav1d"),
            ("media/libdav1d", "dav1d"),
            ("third_party/dav1d", "dav1d"),
            ("third_party/libsrtp/src", "libsrtp"),
            ("media/libspeex_resampler", "speexdsp"),
            ("dom/media/gmp/widevine-adapter", "widevine-adapter"),
        ]
        for token, expected in cases:
            with self.subTest(token=token):
                self.assertEqual(channel_policy.resolve_library(token)[0], expected)

    def test_unknown_media_path_fails_closed(self):
        library_id, note = channel_policy.resolve_library("media/libbrandnew")
        self.assertIsNone(library_id)
        self.assertIn(channel_policy.FALLBACK_PROFILE, note)
        self.assertIn("library-policies.md", note)

    def test_unknown_token_is_not_guessed(self):
        self.assertEqual(channel_policy.resolve_library("bogus")[0], None)

    def test_every_library_has_a_known_profile(self):
        for name, lib in channel_policy.LIBRARIES.items():
            with self.subTest(library=name):
                self.assertTrue(lib.channels, f"{name} has no channel")
                for channel in lib.channels:
                    self.assertIn(channel, channel_policy.PROFILES)

    def test_no_upstream_libraries_never_cc_externals(self):
        for name, lib in channel_policy.LIBRARIES.items():
            if not lib.has_upstream:
                with self.subTest(library=name):
                    self.assertEqual(lib.cc_external, ())
                    self.assertEqual(lib.channels, ("bugzilla-restricted",))


class TestTestHarnesses(unittest.TestCase):
    def test_every_library_resolves_to_a_harness(self):
        # "There was no way to write a test" must never be the default answer,
        # so every library needs somewhere a regression test could live.
        for name in channel_policy.LIBRARIES:
            with self.subTest(library=name):
                harness = channel_policy.harness_for(name)
                self.assertIsNotNone(harness, f"{name} has no harness")
                self.assertTrue(harness.framework)
                self.assertTrue(harness.command)
                self.assertTrue(harness.registration)

    def test_no_upstream_components_fall_back_to_firefox(self):
        harness = channel_policy.harness_for("psshparser")
        self.assertIn("gtest", harness.framework.lower())
        self.assertIn("mach", harness.command)

    def test_harness_reaches_the_facts_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(tmp, MINIMAL_CHECKOUT)
            facts = media_lib_facts.collect("libogg", Path(tmp))
        self.assertIsNotNone(facts.test_harness)
        self.assertIn("check", facts.test_harness["command"])

    def test_harness_table_is_documented(self):
        path = REFERENCES / "library-policies.md"
        text = path.read_text(encoding="utf-8")
        for name in channel_policy.TEST_HARNESSES:
            with self.subTest(library=name):
                self.assertIn(f"`{name}`", text)


class TestStandaloneTestRequirement(unittest.TestCase):
    STANDALONE_LINE = (
        "Standalone test: added to the libogg `make check` suite as "
        "01-test-oggpack-look.patch."
    )

    def test_a_report_with_no_test_statement_is_rejected(self):
        text = textwrap.dedent(GOOD_REPORT).replace(self.STANDALONE_LINE, "")
        errors, _ = validator.check_report(
            text, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        self.assertTrue(any("standalone test status" in e for e in errors), errors)

    def test_an_explicit_blocker_satisfies_it(self):
        text = textwrap.dedent(GOOD_REPORT).replace(
            self.STANDALONE_LINE,
            "No standalone test: the failure only shows under ASan, which this "
            "harness does not build with.",
        )
        errors, _ = validator.check_report(
            text, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        self.assertFalse(any("standalone test status" in e for e in errors), errors)

    def test_a_harness_test_satisfies_it(self):
        for phrasing in ("make check", "FATE", "cargo test", "gtest", "meson test"):
            with self.subTest(phrasing=phrasing):
                text = textwrap.dedent(GOOD_REPORT) + f"\nAdded a {phrasing} case.\n"
                errors, _ = validator.check_report(
                    text, "libogg", "gitlab-confidential", None, "v1.3.6"
                )
                self.assertFalse(any("standalone test status" in e for e in errors))


class TestForgeRefExtraction(unittest.TestCase):
    def _ref(self, forge, url):
        match = re.search(channel_policy.FORGE_PATTERNS[forge], url, re.I)
        return match.group("ref") if match else None

    def test_each_forge_shape(self):
        cases = [
            (
                "github",
                "https://github.com/FFmpeg/FFmpeg/blob/" + "a" * 40 + "/x.c#L1",
                "a" * 40,
            ),
            (
                "gitlab",
                "https://gitlab.xiph.org/xiph/ogg/-/blob/v1.3.6/src/bitwise.c#L214",
                "v1.3.6",
            ),
            (
                "gitlab",
                "https://code.videolan.org/videolan/dav1d/-/blob/"
                + "b" * 40
                + "/src/lib.c#L9",
                "b" * 40,
            ),
            (
                "googlesource",
                "https://chromium.googlesource.com/webm/libvpx/+/"
                + "c" * 40
                + "/vp8/x.c#12",
                "c" * 40,
            ),
            (
                "codeberg",
                "https://codeberg.org/soundtouch/soundtouch/src/commit/"
                + "d" * 40
                + "/a.cpp#L3",
                "d" * 40,
            ),
        ]
        for forge, url, expected in cases:
            with self.subTest(forge=forge, url=url):
                self.assertEqual(self._ref(forge, url), expected)

    def test_line_anchor_is_not_absorbed_into_the_ref(self):
        url = "https://github.com/a/b/blob/" + "e" * 40 + "/f.c#L42"
        self.assertEqual(self._ref("github", url), "e" * 40)


class TestRevisionPinning(unittest.TestCase):
    class _Facts:
        def __init__(self, kind):
            self.revision_kind = kind

    def test_full_hash_always_ok(self):
        self.assertTrue(validator.acceptable_ref("a" * 40, None, "v1.3.6"))

    def test_tag_accepted_only_when_it_is_the_pin(self):
        self.assertTrue(validator.acceptable_ref("v1.3.6", None, "v1.3.6"))
        # libwebp declares tracking: tag but pins a hash, so a tag must fail.
        self.assertFalse(validator.acceptable_ref("v1.3.6", None, "9" * 40))

    def test_moving_refs_rejected(self):
        for ref in ("master", "main", "HEAD", "trunk", "refs/heads/main"):
            with self.subTest(ref=ref):
                self.assertFalse(validator.acceptable_ref(ref, None, "a" * 40))

    def test_short_hash_only_for_short_hash_libraries(self):
        facts = self._Facts("short-hash")
        self.assertTrue(validator.acceptable_ref("f20ebb8adb", facts, "f20ebb8adb"))
        self.assertTrue(validator.acceptable_ref("f20ebb8", facts, "f20ebb8adb"))
        self.assertFalse(
            validator.acceptable_ref("f20ebb8", self._Facts("full-hash"), "a" * 40)
        )

    def test_markdown_link_delimiter_is_not_part_of_commit_ref(self):
        revision = "a" * 40
        facts = self._Facts("full-hash")
        facts.forge = "github"
        facts.repo_url = "https://github.com/FFmpeg/FFmpeg"
        report = "[the fix](https://github.com/FFmpeg/FFmpeg/commit/" + revision + ")"

        warnings = []
        errors = validator._check_source_links(
            report, None, facts, revision, True, warnings
        )

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])


class TestCoreRequirements(unittest.TestCase):
    def test_good_report_passes(self):
        errors, _ = validator.check_report(
            textwrap.dedent(GOOD_REPORT),
            "libogg",
            "gitlab-confidential",
            None,
            "v1.3.6",
        )
        self.assertEqual(errors, [])

    def test_each_core_requirement_is_enforced(self):
        # Deleting the line that satisfies a requirement must surface it.
        removals = {
            "human reviewer": "Human reviewer: A. Reviewer. Finder credit: B. Finder.",
            "human origination / AI-usage disclosure": (
                "AI usage: no AI was used; verified by a human by hand."
            ),
        }
        for label, line in removals.items():
            with self.subTest(requirement=label):
                text = textwrap.dedent(GOOD_REPORT).replace(line, "")
                errors, _ = validator.check_report(
                    text, "libogg", "gitlab-confidential", None, "v1.3.6"
                )
                self.assertTrue(
                    any(label in e for e in errors), f"{label} not reported in {errors}"
                )

    def test_empty_report(self):
        errors, _ = validator.check_report("   ", "libogg", "gitlab-confidential")
        self.assertEqual(errors, ["report is empty"])

    def test_unpinned_source_link_is_an_error(self):
        text = textwrap.dedent(GOOD_REPORT).replace(
            "/-/blob/v1.3.6/", "/-/blob/master/"
        )
        errors, _ = validator.check_report(
            text, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        self.assertTrue(any("not pinned" in e for e in errors))

    def test_missing_vendored_revision_is_an_error(self):
        text = textwrap.dedent(GOOD_REPORT).replace("v1.3.6", "v1.3.5")
        errors, _ = validator.check_report(
            text, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        self.assertTrue(any("never named" in e for e in errors))


class TestCrashStackCompleteness(unittest.TestCase):
    def _errors(self, body):
        return validator._check_stack_completeness(textwrap.dedent(body))

    def test_complete_zero_and_one_based_stacks_pass(self):
        for body in (
            """\
                #0 crash leaf.c:10
                #1 caller caller.c:20
                #2 main main.c:30
                """,
            """\
                #1 crash leaf.c:10
                #2 caller caller.c:20
                #3 main main.c:30
                """,
        ):
            with self.subTest(body=body):
                self.assertEqual(self._errors(body), [])

    def test_gap_in_the_middle_is_rejected(self):
        errors = self._errors(
            """\
            #0 crash leaf.c:10
            #1 caller caller.c:20
            #3 main main.c:30
            """
        )
        self.assertTrue(any("skips frame(s) #2" in error for error in errors), errors)

    def test_stack_must_begin_at_zero_or_one(self):
        errors = self._errors(
            """\
            #4 caller caller.c:20
            #5 main main.c:30
            """
        )
        self.assertTrue(any("starts at frame #4" in error for error in errors), errors)

    def test_duplicate_or_out_of_order_frame_is_rejected(self):
        errors = self._errors(
            """\
            #0 crash leaf.c:10
            #1 caller caller.c:20
            #2 main main.c:30
            #2 duplicate main.c:30
            """
        )
        self.assertTrue(
            any("duplicate or out-of-order frame #2" in error for error in errors),
            errors,
        )

    def test_ellipsis_omission_marker_is_rejected(self):
        errors = self._errors(
            """\
            #0 crash leaf.c:10
            #1 caller caller.c:20
            ...
            """
        )
        self.assertTrue(any("omission marker" in error for error in errors), errors)

    def test_multiple_complete_stacks_are_checked_separately(self):
        errors = self._errors(
            """\
            ## Faulting thread
            ```
            #0 crash leaf.c:10
            #1 caller caller.c:20
            ```

            ## Thread creation
            ```
            #1 create thread.c:40
            #2 main main.c:50
            ```
            """
        )
        self.assertEqual(errors, [])

    def test_check_report_rejects_an_incomplete_stack(self):
        text = textwrap.dedent(GOOD_REPORT).replace(
            "#1 ogg_sync_pageseek framing.c:412",
            "#1 ogg_sync_pageseek framing.c:412\n#3 main main.c:30",
        )
        errors, _ = validator.check_report(
            text, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        self.assertTrue(any("skips frame(s) #2" in error for error in errors), errors)


class TestProfileRequirements(unittest.TestCase):
    def test_gitlab_rejects_an_attached_input(self):
        text = textwrap.dedent(GOOD_REPORT).replace(
            "Testcase:", "Testcase: see the attached crash input."
        )
        errors, _ = validator.check_report(
            text, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        self.assertTrue(any("world-readable" in e for e in errors))

    def test_gitlab_allows_explaining_why_nothing_is_attached(self):
        # A correct report has to use the word "attachment" to explain the rule
        # it is following; only a claim that the input IS attached is a fault.
        text = textwrap.dedent(GOOD_REPORT).replace(
            "Crash input: delivered inline as base64 below, never as an upload.",
            "Crash input: inline base64 below. Not uploaded: attachments on a "
            "confidential issue in a public project are world-readable.",
        )
        errors, _ = validator.check_report(
            text, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        self.assertEqual(errors, [])

    def test_gitlab_requires_confidential_at_creation(self):
        text = textwrap.dedent(GOOD_REPORT)
        errors, _ = validator.check_report(
            text, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        self.assertEqual(errors, [])
        stripped = text.replace("inline", "").replace("base64", "")
        errors, _ = validator.check_report(
            stripped, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        self.assertTrue(any("crash input delivered inline" in e for e in errors))

    def test_buganizer_wants_git_describe_and_cc_yourself(self):
        text = textwrap.dedent(GOOD_REPORT)
        errors, _ = validator.check_report(text, "libvpx", "buganizer", None, "a" * 40)
        self.assertTrue(any("git describe" in e for e in errors))
        self.assertTrue(any("CC yourself" in e for e in errors))

    def test_bugzilla_forbids_cvss_and_cwe(self):
        text = textwrap.dedent(GOOD_REPORT) + "\nCVSS:3.1/AV:N/AC:L and CWE-125.\n"
        errors, _ = validator.check_report(
            text, "libsoundtouch", "bugzilla-restricted", None, "a" * 40
        )
        self.assertTrue(any("CVSS" in e for e in errors))
        self.assertTrue(any("CWE" in e for e in errors))

    def test_github_pvr_allows_cvss(self):
        text = (
            textwrap.dedent(GOOD_REPORT) + "\nSeverity: CVSS:3.1/AV:N/AC:L. CWE-125.\n"
        )
        errors, _ = validator.check_report(
            text, "libpng", "github-pvr", None, "v1.6.58"
        )
        self.assertFalse(any("CVSS" in e for e in errors))

    def test_ffvpx_extras_on_top_of_the_core(self):
        text = textwrap.dedent(GOOD_REPORT)
        errors, _ = validator.check_report(text, "ffvpx", "email-plain", None, "a" * 40)
        self.assertTrue(any("input-generation script" in e for e in errors))

    def test_libjpeg_requires_the_scope_gate(self):
        text = textwrap.dedent(GOOD_REPORT)
        errors, _ = validator.check_report(
            text, "libjpeg-turbo", "email-gpg", None, "3.1.4.1"
        )
        self.assertTrue(any("scope gate" in e for e in errors))


class TestHygieneScan(unittest.TestCase):
    def test_downstream_detail_is_rejected_upstream(self):
        text = textwrap.dedent(GOOD_REPORT) + (
            "\nSee https://bugzilla.mozilla.org/show_bug.cgi?id=1 and "
            "https://searchfox.org/mozilla-central/source/x.cpp, rated sec-high, "
            "found at /home/someone/work/crash.ogg\n"
        )
        errors, _ = validator.check_report(
            text, "libogg", "gitlab-confidential", None, "v1.3.6"
        )
        for expected in (
            "Bugzilla link",
            "searchfox link",
            "security rating",
            "local absolute path",
        ):
            with self.subTest(rule=expected):
                self.assertTrue(any(expected in e for e in errors), errors)

    def test_hygiene_scan_is_skipped_for_bugzilla_reports(self):
        text = (
            textwrap.dedent(GOOD_REPORT)
            + "\nSee https://bugzilla.mozilla.org/show_bug.cgi?id=1\n"
        )
        errors, _ = validator.check_report(
            text, "libsoundtouch", "bugzilla-restricted", None, "a" * 40
        )
        self.assertFalse(any("Bugzilla link" in e for e in errors))

    def test_no_upstream_component_requires_a_searchfox_permalink(self):
        text = textwrap.dedent(GOOD_REPORT)
        errors, _ = validator.check_report(text, "psshparser", "bugzilla-restricted")
        self.assertTrue(any("searchfox" in e for e in errors))
        pinned = (
            text
            + f"\nhttps://searchfox.org/mozilla-central/rev/{'a' * 40}/media/x.cpp\n"
        )
        errors, _ = validator.check_report(pinned, "psshparser", "bugzilla-restricted")
        self.assertFalse(any("searchfox" in e for e in errors))


class TestPolicyTablesInSync(unittest.TestCase):
    """The markdown references and the Python tables must not drift apart."""

    def _read(self, name):
        path = REFERENCES / name
        if not path.is_file():
            self.skipTest(f"{name} not written yet")
        return path.read_text(encoding="utf-8")

    def test_every_library_has_a_row_in_library_policies(self):
        text = self._read("library-policies.md")
        for name in channel_policy.LIBRARIES:
            with self.subTest(library=name):
                self.assertIn(f"`{name}`", text)

    def test_every_profile_has_a_section_and_a_draft(self):
        profiles_doc = self._read("channel-profiles.md")
        drafts_doc = self._read("submission-drafts.md")
        for name, profile in channel_policy.PROFILES.items():
            with self.subTest(profile=name):
                self.assertIn(name, profiles_doc)
                self.assertIn(profile.draft_anchor, drafts_doc)

    def test_report_template_has_its_sections(self):
        text = self._read("report-template.md")
        for heading in (
            "## Attribution and Identifiers",
            "## Summary",
            "## Code Path Trace",
            "## Crash Stacks",
            "## Test Cases",
            "## Input Generation",
            "## How to Reproduce",
            "## Suggested Fix",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, text)

    def test_references_carry_no_personal_identity(self):
        # The template is derived from a real report; names, addresses and
        # employers from it must stay placeholders.
        leaked = re.compile(
            r"cchang@|chun-?min|@mozilla\.com|\bbugmon\b",
            re.I,
        )
        for name in (
            "report-template.md",
            "submission-drafts.md",
            "report-core.md",
            "channel-profiles.md",
            "library-policies.md",
        ):
            with self.subTest(reference=name):
                hits = leaked.findall(self._read(name))
                self.assertEqual(hits, [], f"{name} hardcodes an identity: {hits}")

    def test_no_orphan_profiles(self):
        used = {c for lib in channel_policy.LIBRARIES.values() for c in lib.channels}
        self.assertEqual(used, set(channel_policy.PROFILES))


class TestCli(unittest.TestCase):
    def _report(self, tmp, body):
        path = Path(tmp) / "report.md"
        path.write_text(textwrap.dedent(body), encoding="utf-8")
        return path

    def test_pass_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._report(tmp, GOOD_REPORT)
            code = validator.main(
                [str(path), "--library", "libogg", "--no-tree", "--revision", "v1.3.6"]
            )
        self.assertEqual(code, 0)

    def test_failure_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._report(tmp, "# nothing useful here\n")
            code = validator.main([str(path), "--library", "libogg", "--no-tree"])
        self.assertEqual(code, 1)

    def test_unknown_library_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._report(tmp, GOOD_REPORT)
            code = validator.main([str(path), "--library", "nope", "--no-tree"])
        self.assertEqual(code, 2)

    def test_unreadable_report_exit_two(self):
        code = validator.main(
            ["/nonexistent/report.md", "--library", "libogg", "--no-tree"]
        )
        self.assertEqual(code, 2)

    def test_facts_cli_lists_libraries(self):
        self.assertEqual(media_lib_facts.main(["--list"]), 0)


if __name__ == "__main__":
    unittest.main()
