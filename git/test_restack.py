#!/usr/bin/env python3
"""Tests for git/restack.py, run against throwaway repositories.

Each test gets an `up.git` (the upstream), a `fork.git` (origin) and a
`work` clone, with global/system git config isolated so the user's own
settings (signing, hooks, aliases) cannot leak in.
"""

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "restack.py")
sys.path.insert(0, HERE)

import restack  # noqa: E402


class RepoTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="restack-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        empty_config = os.path.join(self.tmp, "gitconfig")
        open(empty_config, "w").close()
        env = {
            "HOME": self.tmp,
            "GIT_CONFIG_GLOBAL": empty_config,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
            "GIT_EDITOR": "true",
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.up = os.path.join(self.tmp, "up.git")
        self.fork = os.path.join(self.tmp, "fork.git")
        self.work = os.path.join(self.tmp, "work")
        self.other = os.path.join(self.tmp, "other")
        self.git("init", "-q", "--bare", "-b", "main", self.up, cwd=self.tmp)
        self.git("init", "-q", "--bare", "-b", "main", self.fork, cwd=self.tmp)

        # A second clone stands in for everyone else pushing upstream.
        self.git("clone", "-q", self.up, self.other, cwd=self.tmp)
        self.commit(self.other, "README", "hello\n", "initial")
        self.git("push", "-q", "origin", "main", cwd=self.other)

        self.git("clone", "-q", "-o", "upstream", self.up, self.work, cwd=self.tmp)
        self.git("remote", "add", "origin", self.fork)

    # -- helpers ------------------------------------------------------------

    def git(self, *args, cwd=None, check=True):
        result = subprocess.run(
            ["git", *args],
            cwd=cwd or self.work,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail("git {} failed: {}".format(" ".join(args), result.stderr))
        return result.stdout.strip()

    def commit(self, repo, path, content, message):
        with open(os.path.join(repo, path), "w") as f:
            f.write(content)
        self.git("add", path, cwd=repo)
        self.git("commit", "-q", "-m", message, cwd=repo)
        return self.git("rev-parse", "HEAD", cwd=repo)

    def upstream_commit(self, path="up.txt", content=None, message="upstream"):
        """Land a commit upstream, as somebody else would."""
        content = content or message + "\n"
        sha = self.commit(self.other, path, content, message)
        self.git("push", "-q", "origin", "main", cwd=self.other)
        return sha

    def branch(self, name, start, path, content):
        self.git("checkout", "-q", "-b", name, start)
        return self.commit(self.work, path, content, name)

    def restack(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, SCRIPT, *args],
            cwd=cwd or self.work,
            capture_output=True,
            text=True,
        )

    def assertRestackOk(self, *args, cwd=None):
        result = self.restack(*args, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def checkouts(self):
        reflog = self.git("reflog", "--format=%gs", "HEAD").splitlines()
        return [line for line in reflog if line.startswith("checkout: moving")]

    def rev(self, ref, cwd=None):
        return self.git("rev-parse", ref, cwd=cwd)

    def subjects(self, span):
        return self.git("log", "--format=%s", span).splitlines()

    def upstream_tip(self):
        return self.git("rev-parse", "main", cwd=self.up)


class TestBasicFlow(RepoTestCase):
    def test_plain_repo_rebases_current_branch_onto_updated_base(self):
        self.branch("feature", "main", "f.txt", "f\n")
        self.upstream_commit()

        self.assertRestackOk()

        self.assertEqual(self.rev("main"), self.upstream_tip())
        self.assertEqual(self.rev("feature~1"), self.rev("main"))
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD"), "feature")
        self.assertTrue(os.path.exists(os.path.join(self.work, "up.txt")))

    def test_base_and_layer_are_updated_without_checking_them_out(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.branch("feature", "overlay", "f.txt", "f\n")
        self.upstream_commit()

        checkouts_before = self.checkouts()

        self.assertRestackOk("--layer", "overlay")

        self.assertEqual(self.rev("overlay~1"), self.rev("main"))
        self.assertEqual(self.rev("feature~1"), self.rev("overlay"))
        self.assertEqual(self.subjects("main..feature"), ["feature", "overlay"])
        # Only feature itself was rebased in place; main and overlay never
        # passed through the working tree.
        self.assertEqual(self.checkouts(), checkouts_before)

    def test_layers_from_config(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.git("checkout", "-q", "main")
        self.git("config", "--add", "restack.layer", "overlay")
        self.upstream_commit()

        self.assertRestackOk()

        self.assertEqual(self.rev("overlay~1"), self.upstream_tip())

    def test_missing_configured_layer_is_skipped_with_a_warning(self):
        self.git("config", "--add", "restack.layer", "nope")
        self.branch("feature", "main", "f.txt", "f\n")
        self.upstream_commit()

        result = self.assertRestackOk()

        self.assertIn("layer 'nope' does not exist", result.stdout)
        self.assertEqual(self.rev("feature~1"), self.upstream_tip())

    def test_running_on_the_base_branch_just_updates_it(self):
        self.upstream_commit()

        self.assertRestackOk()

        self.assertEqual(self.rev("HEAD"), self.upstream_tip())
        self.assertTrue(os.path.exists(os.path.join(self.work, "up.txt")))

    def test_dry_run_changes_nothing(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.branch("feature", "overlay", "f.txt", "f\n")
        self.upstream_commit()
        before = self.git("for-each-ref", "refs/heads")

        result = self.assertRestackOk("-n", "-l", "overlay")

        self.assertEqual(self.git("for-each-ref", "refs/heads"), before)
        self.assertIn("feature onto overlay", result.stdout)
        self.assertIn("overlay onto main", result.stdout)


class TestParentDetection(RepoTestCase):
    def test_stale_branch_finds_layer_rewritten_by_an_earlier_run(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.branch("feature", "overlay", "f.txt", "f\n")
        # An earlier run from main moves overlay but not feature...
        self.git("checkout", "-q", "main")
        self.upstream_commit(message="first")
        self.assertRestackOk("-l", "overlay")
        # ...then overlay's own content is bumped, so its old commit no
        # longer applies cleanly on top of the new one.
        self.git("checkout", "-q", "overlay")
        self.commit(self.work, "overlay.txt", "v2\n", "overlay")
        self.git("reset", "-q", "--soft", "HEAD~2")
        self.git("commit", "-q", "-m", "overlay")
        self.upstream_commit(message="second")

        self.git("checkout", "-q", "feature")
        self.assertRestackOk("-l", "overlay")

        self.assertEqual(self.rev("feature~1"), self.rev("overlay"))
        self.assertEqual(self.subjects("main..feature"), ["feature", "overlay"])
        with open(os.path.join(self.work, "overlay.txt")) as f:
            self.assertEqual(f.read(), "v2\n")

    def test_branch_on_base_is_not_attributed_to_a_layer(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.branch("feature", "main", "f.txt", "f\n")
        self.upstream_commit()

        self.assertRestackOk("-l", "overlay")

        self.assertEqual(self.subjects("main..feature"), ["feature"])

    def test_branch_without_own_commits_follows_its_layer(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.git("checkout", "-q", "-b", "feature", "overlay")
        self.upstream_commit()

        self.assertRestackOk("-l", "overlay")

        self.assertEqual(self.rev("feature"), self.rev("overlay"))
        self.assertEqual(self.rev("overlay~1"), self.upstream_tip())

    def test_stacked_targets_move_together(self):
        self.branch("a", "main", "a.txt", "a\n")
        self.branch("b", "a", "b.txt", "b\n")
        self.upstream_commit()

        self.assertRestackOk("b", "a")

        self.assertEqual(self.rev("a~1"), self.upstream_tip())
        self.assertEqual(self.rev("b~1"), self.rev("a"))

    def test_fully_landed_branch_becomes_the_base(self):
        self.git("checkout", "-q", "-b", "feature", "main")
        self.upstream_commit()
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--ff-only", "upstream/main", check=False)
        self.git("fetch", "-q", "upstream")
        self.git("merge", "-q", "--ff-only", "upstream/main")
        # feature is now strictly behind main
        self.git("checkout", "-q", "feature")
        self.upstream_commit(message="later")

        self.assertRestackOk()

        self.assertEqual(self.rev("feature"), self.upstream_tip())


class TestInMemoryRebase(RepoTestCase):
    def test_commit_that_landed_upstream_is_dropped(self):
        self.branch("feature", "main", "f.txt", "f\n")
        self.commit(self.work, "g.txt", "g\n", "mine")
        self.upstream_commit("f.txt", "f\n", "feature landed")
        self.git("checkout", "-q", "main")

        self.assertRestackOk("feature")

        self.assertEqual(self.subjects("main..feature"), ["mine"])

    def test_originally_empty_commit_is_kept(self):
        self.git("checkout", "-q", "-b", "feature")
        self.git("commit", "-q", "--allow-empty", "-m", "marker")
        self.git("checkout", "-q", "main")
        self.upstream_commit()

        self.assertRestackOk("feature")

        self.assertEqual(self.subjects("main..feature"), ["marker"])

    def test_author_and_message_are_preserved(self):
        self.git("checkout", "-q", "-b", "feature")
        with open(os.path.join(self.work, "f.txt"), "w") as f:
            f.write("f\n")
        self.git("add", "f.txt")
        self.git(
            "commit",
            "-q",
            "--author",
            "Someone Else <else@example.com>",
            "--date",
            "2001-02-03T04:05:06+0700",
            "-m",
            "Subject line\n\nBody line\n",
        )
        self.git("checkout", "-q", "main")
        self.upstream_commit()

        self.assertRestackOk("feature")

        fmt = "%an <%ae> %ad%n%B"
        log = self.git("log", "-1", "--date=iso", "--format=" + fmt, "feature")
        self.assertEqual(
            log,
            "Someone Else <else@example.com> 2001-02-03 04:05:06 +0700\n"
            "Subject line\n\nBody line",
        )

    def test_conflict_leaves_branch_untouched(self):
        old = self.branch("feature", "main", "up.txt", "mine\n")
        self.git("checkout", "-q", "main")
        self.upstream_commit("up.txt", "theirs\n")

        result = self.restack("feature")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.rev("feature"), old)
        self.assertIn("conflict replaying", result.stdout)
        self.assertEqual(self.rev("main"), self.upstream_tip())

    def test_descendants_of_a_failed_branch_are_skipped(self):
        self.branch("a", "main", "up.txt", "mine\n")
        old_b = self.branch("b", "a", "b.txt", "b\n")
        self.git("checkout", "-q", "main")
        self.upstream_commit("up.txt", "theirs\n")

        result = self.restack("a", "b")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.rev("b"), old_b)
        self.assertIn("skipped: a was not restacked", result.stdout)


class TestCurrentBranch(RepoTestCase):
    def test_conflict_leaves_rebase_in_progress(self):
        self.branch("feature", "main", "up.txt", "mine\n")
        self.upstream_commit("up.txt", "theirs\n")

        result = self.restack()

        self.assertEqual(result.returncode, 1)
        self.assertIn("rebase in progress here", result.stdout)
        self.assertTrue(
            os.path.isdir(self.git("rev-parse", "--absolute-git-dir") + "/rebase-merge")
        )

    def test_refuses_to_start_during_a_rebase(self):
        self.branch("feature", "main", "up.txt", "mine\n")
        self.upstream_commit("up.txt", "theirs\n")
        self.restack()

        result = self.restack()

        self.assertEqual(result.returncode, 1)
        self.assertIn("rebase is in progress", result.stderr)

    def test_dirty_tree_is_refused_before_anything_moves(self):
        self.branch("feature", "main", "f.txt", "f\n")
        old_main = self.rev("main")
        self.upstream_commit()
        with open(os.path.join(self.work, "f.txt"), "w") as f:
            f.write("edited\n")

        result = self.restack()

        self.assertEqual(result.returncode, 1)
        self.assertIn("--autostash", result.stderr)
        self.assertEqual(self.rev("main"), old_main)

    def test_autostash_keeps_local_changes(self):
        self.branch("feature", "main", "f.txt", "f\n")
        self.upstream_commit()
        with open(os.path.join(self.work, "f.txt"), "w") as f:
            f.write("edited\n")

        self.assertRestackOk("--autostash")

        self.assertEqual(self.rev("feature~1"), self.upstream_tip())
        with open(os.path.join(self.work, "f.txt")) as f:
            self.assertEqual(f.read(), "edited\n")

    def test_untracked_files_do_not_block(self):
        self.branch("feature", "main", "f.txt", "f\n")
        self.upstream_commit()
        open(os.path.join(self.work, "scratch.txt"), "w").close()

        self.assertRestackOk()


class TestBaseAndPush(RepoTestCase):
    def test_diverged_base_is_refused(self):
        self.commit(self.work, "local.txt", "x\n", "local only")
        self.upstream_commit()

        result = self.restack()

        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot fast-forward", result.stderr)

    def test_push_to_named_remote(self):
        self.upstream_commit()

        self.assertRestackOk("--push=origin")

        self.assertEqual(
            self.git("rev-parse", "main", cwd=self.fork), self.upstream_tip()
        )

    def test_bare_push_refuses_to_push_back_to_upstream(self):
        # branch.main.remote=upstream and no remote.pushDefault, so
        # main@{push} is upstream/main -- the trap this guards against.
        old_main = self.rev("main")
        self.upstream_commit()

        result = self.restack("--push")

        self.assertEqual(result.returncode, 1)
        self.assertIn("remote.pushDefault", result.stderr)
        self.assertEqual(self.rev("main"), old_main)

    def test_bare_push_follows_push_default(self):
        self.git("config", "remote.pushDefault", "origin")
        self.upstream_commit()

        self.assertRestackOk("--push")

        self.assertEqual(
            self.git("rev-parse", "main", cwd=self.fork), self.upstream_tip()
        )

    def test_push_from_config_and_no_push_override(self):
        self.git("config", "restack.push", "origin")
        self.upstream_commit()

        self.assertRestackOk("--no-push")
        self.assertEqual(self.git("branch", "--list", "main", cwd=self.fork), "")

        self.assertRestackOk()
        self.assertEqual(
            self.git("rev-parse", "main", cwd=self.fork), self.upstream_tip()
        )

    def test_push_flag_does_not_swallow_a_branch_name(self):
        self.git("config", "remote.pushDefault", "origin")
        self.branch("feature", "main", "f.txt", "f\n")
        self.git("checkout", "-q", "main")
        self.upstream_commit()

        self.assertRestackOk("--push", "feature")

        self.assertEqual(self.rev("feature~1"), self.upstream_tip())
        self.assertEqual(
            self.git("rev-parse", "main", cwd=self.fork), self.upstream_tip()
        )

    def test_explicit_upstream_without_tracking_config(self):
        self.git("branch", "--unset-upstream", "main")
        self.upstream_commit()

        self.assertRestackOk("--upstream", "upstream/main")

        self.assertEqual(self.rev("main"), self.upstream_tip())

    def test_master_default_with_single_origin_remote(self):
        repo = os.path.join(self.tmp, "solo")
        remote = os.path.join(self.tmp, "solo.git")
        self.git("init", "-q", "--bare", "-b", "master", remote, cwd=self.tmp)
        self.git("clone", "-q", self.other, repo, cwd=self.tmp)  # any history
        self.git("branch", "-q", "-m", "main", "master", cwd=repo)
        self.git("remote", "set-url", "origin", remote, cwd=repo)
        self.git("push", "-q", "-u", "origin", "master", cwd=repo)
        self.git("remote", "set-head", "origin", "master", cwd=repo)
        self.git("checkout", "-q", "-b", "feature", cwd=repo)
        self.commit(repo, "f.txt", "f\n", "feature")
        pusher = os.path.join(self.tmp, "solo-pusher")
        self.git("clone", "-q", remote, pusher, cwd=self.tmp)
        tip = self.commit(pusher, "new.txt", "n\n", "new")
        self.git("push", "-q", "origin", "master", cwd=pusher)

        self.assertRestackOk(cwd=repo)

        self.assertEqual(self.rev("master", cwd=repo), tip)
        self.assertEqual(self.rev("feature~1", cwd=repo), tip)


class TestBaseTrackingAFork(RepoTestCase):
    """Cloning a fork leaves main tracking origin, which nobody syncs."""

    def setUp(self):
        super().setUp()
        self.git("push", "-q", "origin", "main")
        self.git("fetch", "-q", "origin")
        self.git("branch", "-q", "--set-upstream-to=origin/main", "main")
        self.branch("feature", "main", "f.txt", "f\n")
        self.stale = self.rev("main")
        self.upstream_commit()
        self.git("fetch", "-q", "upstream")

    def test_base_is_updated_from_upstream_not_the_fork(self):
        result = self.assertRestackOk()

        self.assertIn("main <- upstream/main", result.stdout)
        self.assertIn("note: main tracks origin/main", result.stdout)
        self.assertEqual(self.rev("main"), self.upstream_tip())
        self.assertEqual(self.rev("feature~1"), self.upstream_tip())

    def test_restack_upstream_config_keeps_the_fork(self):
        self.git("config", "restack.upstream", "origin")

        result = self.assertRestackOk()

        self.assertIn("main <- origin/main", result.stdout)
        self.assertNotIn("note:", result.stdout)
        self.assertEqual(self.rev("main"), self.stale)

    def test_bad_restack_upstream_names_the_config(self):
        self.git("config", "restack.upstream", "nowhere/main")

        result = self.restack()

        self.assertEqual(result.returncode, 1)
        self.assertIn("restack.upstream 'nowhere/main'", result.stderr)

    def test_bare_push_syncs_the_fork(self):
        # main@{push} is origin/main, no longer the place main comes from.
        self.assertRestackOk("--push")

        self.assertEqual(
            self.git("rev-parse", "main", cwd=self.fork), self.upstream_tip()
        )

    def test_unfetched_upstream_branch_falls_back_to_tracking(self):
        # The upstream may call it something else; do not guess.
        self.git("update-ref", "-d", "refs/remotes/upstream/main")

        result = self.assertRestackOk()

        self.assertIn("main <- origin/main", result.stdout)
        self.assertEqual(self.rev("main"), self.stale)


class TestBaseDetection(RepoTestCase):
    """The base is whatever the remote calls its default, not just main/master."""

    def make_repo(self, default="trailblazer", remote_name="origin"):
        """A remote whose default branch is `default`, cloned under `remote_name`.

        Returns (clone, pusher): commit in `pusher` and push to move the remote.
        """
        remote = os.path.join(self.tmp, "custom.git")
        seed = os.path.join(self.tmp, "seed")
        self.git("init", "-q", "--bare", "-b", default, remote, cwd=self.tmp)
        self.git("init", "-q", "-b", default, seed, cwd=self.tmp)
        self.commit(seed, "README", "hi\n", "initial")
        self.git("push", "-q", remote, default, cwd=seed)
        repo = os.path.join(self.tmp, "custom")
        self.git("clone", "-q", "-o", remote_name, remote, repo, cwd=self.tmp)
        self.git("checkout", "-q", "-b", "feature", cwd=repo)
        self.commit(repo, "f.txt", "f\n", "feature")
        pusher = os.path.join(self.tmp, "custom-pusher")
        self.git("clone", "-q", remote, pusher, cwd=self.tmp)
        return repo, pusher

    def advance(self, pusher, branch="trailblazer"):
        tip = self.commit(pusher, "new.txt", "n\n", "new")
        self.git("push", "-q", "origin", branch, cwd=pusher)
        return tip

    def test_custom_default_branch_from_origin_head(self):
        repo, pusher = self.make_repo()
        tip = self.advance(pusher)

        result = self.assertRestackOk(cwd=repo)

        self.assertIn("trailblazer <- origin/trailblazer", result.stdout)
        self.assertEqual(self.rev("trailblazer", cwd=repo), tip)
        self.assertEqual(self.rev("feature~1", cwd=repo), tip)

    def test_default_branch_from_a_remote_with_another_name(self):
        repo, pusher = self.make_repo(remote_name="mozilla")
        tip = self.advance(pusher)

        self.assertRestackOk(cwd=repo)

        self.assertEqual(self.rev("feature~1", cwd=repo), tip)

    def test_unknown_base_explains_how_to_set_it(self):
        repo, pusher = self.make_repo()
        self.git("remote", "set-head", "origin", "--delete", cwd=repo)

        result = self.restack(cwd=repo)

        self.assertEqual(result.returncode, 1)
        self.assertIn("restack.base", result.stderr)
        self.assertIn("set-head origin --auto", result.stderr)

        self.git("config", "restack.base", "trailblazer", cwd=repo)
        tip = self.advance(pusher)
        self.assertRestackOk(cwd=repo)
        self.assertEqual(self.rev("feature~1", cwd=repo), tip)

    def test_push_hint_names_a_remote_other_than_the_upstream(self):
        # origin is the upstream here; the fork has some other name.
        repo, _ = self.make_repo()
        self.git("remote", "add", "cmc", self.fork, cwd=repo)

        result = self.restack("--push", cwd=repo)

        self.assertEqual(result.returncode, 1)
        self.assertIn("remote.pushDefault cmc", result.stderr)

    def test_dry_run_shows_the_plan_even_when_it_would_refuse(self):
        repo, _ = self.make_repo()
        with open(os.path.join(repo, "f.txt"), "w") as f:
            f.write("edited\n")

        result = self.restack("-n", cwd=repo)

        self.assertEqual(result.returncode, 1)
        self.assertIn("feature onto trailblazer", result.stdout)
        self.assertIn("--autostash", result.stderr)


class TestRememberedTips(RepoTestCase):
    """.git/restack-tips stands in for reflogs that expired or were deleted."""

    def record(self):
        path = os.path.join(self.work, ".git", "restack-tips")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [tuple(line.split()) for line in f if not line.startswith("#")]

    def stale_feature(self, lose_history):
        """feature sits on overlay v1; an earlier run moved overlay from under
        it, then `lose_history` wipes overlay's reflog."""
        old_overlay = self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.branch("feature", "overlay", "f.txt", "f\n")
        self.git("checkout", "-q", "main")
        self.upstream_commit(message="first")
        self.assertRestackOk("-l", "overlay")
        lose_history()
        self.upstream_commit(message="second")
        self.git("checkout", "-q", "feature")
        return old_overlay

    def expire_reflogs(self):
        self.git(
            "reflog", "expire", "--expire=now", "--expire-unreachable=now", "--all"
        )

    def recreate_overlay(self):
        # What a fresh overlay install does: the branch (and its reflog) goes.
        self.git("branch", "-q", "-D", "overlay")
        self.git("checkout", "-q", "-b", "overlay", "main")
        self.commit(self.work, "overlay.txt", "v2\n", "overlay")
        self.git("checkout", "-q", "main")

    def assertFeatureOnOverlay(self):
        self.assertEqual(self.rev("feature~1"), self.rev("overlay"))
        self.assertEqual(self.subjects("main..feature"), ["feature", "overlay"])

    def test_survives_expired_reflog(self):
        self.stale_feature(self.expire_reflogs)

        result = self.assertRestackOk("-l", "overlay")

        self.assertIn("feature onto overlay", result.stdout)
        self.assertFeatureOnOverlay()

    def test_survives_layer_deleted_and_recreated(self):
        self.stale_feature(self.recreate_overlay)

        result = self.assertRestackOk("-l", "overlay")

        self.assertIn("feature onto overlay", result.stdout)
        self.assertFeatureOnOverlay()
        with open(os.path.join(self.work, "overlay.txt")) as f:
            self.assertEqual(f.read(), "v2\n")

    def test_without_the_record_it_falls_back_and_warns(self):
        self.stale_feature(self.recreate_overlay)
        os.remove(os.path.join(self.work, ".git", "restack-tips"))

        result = self.assertRestackOk("-n", "-l", "overlay")

        self.assertIn("feature onto main", result.stdout)
        self.assertIn("like layer overlay", result.stdout)
        self.assertRegex(result.stdout, r"git rebase --onto overlay \w+ feature")

    def test_entry_kept_while_a_branch_sits_on_it_then_pruned(self):
        old_overlay = self.stale_feature(lambda: None)
        self.assertIn((old_overlay, "overlay"), self.record())

        # Restacking feature moves it off the old overlay...
        self.assertRestackOk("-l", "overlay")
        # ...so the next run finds nothing needing that entry.
        self.assertRestackOk("-l", "overlay")

        self.assertNotIn((old_overlay, "overlay"), self.record())

    def test_entry_dropped_when_its_last_branch_is_deleted(self):
        old_overlay = self.stale_feature(lambda: None)
        self.git("checkout", "-q", "main")
        self.git("branch", "-q", "-D", "feature")

        self.assertRestackOk("-l", "overlay")

        self.assertNotIn((old_overlay, "overlay"), self.record())

    def test_unneeded_record_is_removed_entirely(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.git("checkout", "-q", "main")
        self.assertRestackOk("-l", "overlay")  # records overlay's tip...
        self.assertTrue(self.record())
        self.git("branch", "-q", "-D", "overlay")

        self.assertRestackOk()  # ...which nothing needs any more

        self.assertFalse(
            os.path.exists(os.path.join(self.work, ".git", "restack-tips"))
        )

    def test_dry_run_does_not_write_the_record(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")

        self.assertRestackOk("-n", "-l", "overlay")

        self.assertFalse(
            os.path.exists(os.path.join(self.work, ".git", "restack-tips"))
        )

    def test_record_is_shared_by_worktrees(self):
        overlay = self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.branch("feature", "overlay", "f.txt", "f\n")
        self.git("checkout", "-q", "main")
        wt = os.path.join(self.tmp, "wt")
        self.git("worktree", "add", "-q", wt, "feature")

        self.assertRestackOk("-l", "overlay", cwd=wt)

        self.assertIn((overlay, "overlay"), self.record())

    def test_branch_on_a_hand_amended_branch_is_found_by_restacks_link(self):
        self.branch("a", "main", "a.txt", "a\n")
        self.branch("b", "a", "b.txt", "b\n")
        self.assertRestackOk("a", "b")  # records "b placed on a at <a>"
        self.git("checkout", "-q", "a")
        self.git("commit", "-q", "--amend", "-m", "a amended")
        self.upstream_commit()
        self.git("checkout", "-q", "b")

        result = self.assertRestackOk("a", "b")

        self.assertIn("b onto a", result.stdout)
        self.assertEqual(self.subjects("main..b"), ["b", "a amended"])

    def test_branch_equal_to_an_old_layer_version_follows_the_layer(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.git("checkout", "-q", "-b", "feature")  # no commits of its own
        self.git("checkout", "-q", "main")
        self.upstream_commit(message="first")
        self.assertRestackOk("-l", "overlay")  # moves overlay away from feature
        self.upstream_commit(message="second")
        self.git("checkout", "-q", "feature")

        self.assertRestackOk("-l", "overlay")

        self.assertEqual(self.rev("feature"), self.rev("overlay"))
        self.assertEqual(self.subjects("main..feature"), ["overlay"])

    def test_remembered_tip_cannot_create_a_cycle(self):
        # b was made from a without commits; a run records both at the same
        # commit. Once b gains a commit, b's old tip equals a, but b now
        # contains a, so it must not become a's parent.
        self.branch("a", "main", "a.txt", "a\n")
        self.git("checkout", "-q", "-b", "b")
        self.assertRestackOk("a", "b")
        self.commit(self.work, "b.txt", "b\n", "b")
        self.upstream_commit()

        result = self.assertRestackOk("a", "b")

        self.assertIn("a onto main", result.stdout)
        self.assertIn("b onto a", result.stdout)
        self.assertEqual(self.rev("a~1"), self.upstream_tip())
        self.assertEqual(self.rev("b~1"), self.rev("a"))


class TestBranchReflogsAreNotTrusted(RepoTestCase):
    def test_branch_created_from_another_does_not_become_its_parent(self):
        # `git checkout -b b a` writes a's tip into b's reflog. After b is
        # moved elsewhere, that must not make b look like a's parent (which
        # would reset a to a copy of b).
        a = self.branch("a", "main", "a.txt", "a\n")
        self.git("checkout", "-q", "-b", "b")
        self.commit(self.work, "b.txt", "b\n", "b")
        self.git("rebase", "-q", "--onto", "main", "a", "b")
        self.upstream_commit()

        result = self.assertRestackOk("a", "b")

        self.assertIn("a onto main", result.stdout)
        self.assertIn("b onto main", result.stdout)
        self.assertEqual(self.subjects("main..a"), ["a"])
        self.assertEqual(self.subjects("main..b"), ["b"])
        self.assertNotEqual(self.rev("a"), a)


class TestLookalikeWarning(RepoTestCase):
    def test_overlay_committed_directly_on_a_branch_is_flagged(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.git("checkout", "-q", "-b", "feature", "main")
        # An older overlay version committed straight onto the branch.
        self.commit(self.work, "overlay.txt", "v0\n", "overlay")
        self.commit(self.work, "f.txt", "f\n", "feature")
        self.upstream_commit()

        result = self.assertRestackOk("-l", "overlay")

        self.assertIn("feature sits on main but has commit", result.stdout)
        self.assertIn('"overlay", like layer overlay', result.stdout)
        # Only a warning: the branch is restacked onto main as detected.
        self.assertEqual(self.subjects("main..feature"), ["feature", "overlay"])
        self.assertEqual(self.rev("feature~2"), self.upstream_tip())

    def test_no_warning_for_a_branch_on_its_layer(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.branch("feature", "overlay", "f.txt", "f\n")
        self.upstream_commit()

        result = self.assertRestackOk("-l", "overlay")

        self.assertNotIn("warning", result.stdout)


class TestWorktrees(RepoTestCase):
    def test_branch_in_another_clean_worktree_is_rebased_there(self):
        self.branch("feature", "main", "f.txt", "f\n")
        self.git("checkout", "-q", "main")
        wt = os.path.join(self.tmp, "wt")
        self.git("worktree", "add", "-q", wt, "feature")
        self.upstream_commit()

        self.assertRestackOk("feature")

        self.assertEqual(self.rev("feature~1"), self.upstream_tip())
        self.assertTrue(os.path.exists(os.path.join(wt, "up.txt")))
        self.assertEqual(self.git("status", "--porcelain", cwd=wt), "")

    def test_branch_in_another_dirty_worktree_is_skipped(self):
        old = self.branch("feature", "main", "f.txt", "f\n")
        self.git("checkout", "-q", "main")
        wt = os.path.join(self.tmp, "wt")
        self.git("worktree", "add", "-q", wt, "feature")
        with open(os.path.join(wt, "f.txt"), "w") as f:
            f.write("dirty\n")
        self.upstream_commit()

        result = self.restack("feature")

        self.assertEqual(result.returncode, 1)
        self.assertIn("is dirty", result.stdout)
        self.assertEqual(self.rev("feature"), old)

    def test_base_checked_out_in_another_worktree(self):
        self.branch("feature", "main", "f.txt", "f\n")
        wt = os.path.join(self.tmp, "wt-main")
        self.git("worktree", "add", "-q", wt, "main")
        self.upstream_commit()

        self.assertRestackOk()

        self.assertEqual(self.rev("main"), self.upstream_tip())
        self.assertTrue(os.path.exists(os.path.join(wt, "up.txt")))


class TestOldGitFallback(RepoTestCase):
    """git < 2.40 has no `merge-tree --merge-base`; branches get checked out."""

    def run_in_process(self, *args):
        cwd = os.getcwd()
        os.chdir(self.work)
        self.addCleanup(os.chdir, cwd)
        out = io.StringIO()
        with mock.patch.object(restack, "git_version", return_value=(2, 39)):
            with contextlib.redirect_stdout(out):
                code = restack.main(list(args))
        return code, out.getvalue()

    def test_non_current_branches_are_rebased_and_head_restored(self):
        self.branch("overlay", "main", "overlay.txt", "v1\n")
        self.branch("feature", "overlay", "f.txt", "f\n")
        self.git("checkout", "-q", "main")
        self.git("checkout", "-q", "-b", "elsewhere")
        self.upstream_commit()

        code, out = self.run_in_process("-l", "overlay", "feature")

        self.assertEqual(code, 0, out)
        self.assertEqual(self.rev("overlay~1"), self.upstream_tip())
        self.assertEqual(self.rev("feature~1"), self.rev("overlay"))
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD"), "elsewhere")

    def test_dirty_tree_is_refused(self):
        self.branch("feature", "main", "f.txt", "f\n")
        self.git("checkout", "-q", "main")
        self.upstream_commit()
        with open(os.path.join(self.work, "README"), "w") as f:
            f.write("edited\n")

        with self.assertRaises(restack.RestackError) as ctx:
            self.run_in_process("feature")
        self.assertIn("git < 2.40", str(ctx.exception))


class TestArgumentHelpers(unittest.TestCase):
    def test_split_remote_ref_prefers_longest_remote(self):
        remotes = ["up", "upstream", "origin"]
        self.assertEqual(
            restack.split_remote_ref("upstream/main", remotes), ("upstream", "main")
        )
        self.assertEqual(
            restack.split_remote_ref("up/release/1.0", remotes), ("up", "release/1.0")
        )
        self.assertEqual(restack.split_remote_ref("origin", remotes), ("origin", None))
        self.assertEqual(restack.split_remote_ref("nope/main", remotes), (None, None))

    def test_parse_bool_or_remote(self):
        self.assertEqual(restack.parse_bool_or_remote("true"), "")
        self.assertEqual(restack.parse_bool_or_remote("Yes"), "")
        self.assertIsNone(restack.parse_bool_or_remote("false"))
        self.assertIsNone(restack.parse_bool_or_remote("off"))
        self.assertEqual(restack.parse_bool_or_remote("origin"), "origin")

    def test_push_takes_a_value_only_with_equals(self):
        parser = restack.build_parser()
        args = parser.parse_args(restack.normalize_argv(["--push", "topic"]))
        self.assertEqual(args.push, "")
        self.assertEqual(args.branches, ["topic"])
        args = parser.parse_args(restack.normalize_argv(["--push=origin"]))
        self.assertEqual(args.push, "origin")
        args = parser.parse_args(restack.normalize_argv(["--no-push"]))
        self.assertIs(args.push, False)
        args = parser.parse_args([])
        self.assertIsNone(args.push)


if __name__ == "__main__":
    unittest.main()
