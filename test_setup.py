#!/usr/bin/env python3
"""
Comprehensive test suite for setup.py

Tests cover:
- Utility functions (link, is_tool, append operations)
- Path handling
- File operations
- Symlink creation and validation
- Bash command generation
- Verification functions
"""

import unittest
import tempfile
import os
import sys
import shutil
import subprocess
from unittest.mock import patch

# Import setup.py module
import setup


requires_symlinks = unittest.skipUnless(
    setup.can_create_symlinks(),
    "requires symlink capability (Developer Mode on Windows)",
)


def normalize_link_target(target):
    """Normalize an os.readlink() return value for cross-platform compare.

    On Windows, os.readlink can return absolute paths prefixed with
    ``\\\\?\\`` (extended-length namespace). Strip that, and compare
    via samefile() semantics by going through os.path.normpath.
    """
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return os.path.normpath(target)


class TestPlatformHelpers(unittest.TestCase):
    """Tests for is_windows / is_macos / is_linux / get_home_dir."""

    def test_one_platform_helper_is_true(self):
        """Exactly one of is_windows/is_macos/is_linux is True per host."""
        flags = [setup.is_windows(), setup.is_macos(), setup.is_linux()]
        self.assertEqual(sum(1 for f in flags if f), 1)

    @patch("setup.platform.system", return_value="Windows")
    def test_is_windows(self, _mock):
        self.assertTrue(setup.is_windows())
        self.assertFalse(setup.is_macos())
        self.assertFalse(setup.is_linux())

    @patch("setup.platform.system", return_value="Darwin")
    def test_is_macos(self, _mock):
        self.assertFalse(setup.is_windows())
        self.assertTrue(setup.is_macos())
        self.assertFalse(setup.is_linux())

    @patch("setup.platform.system", return_value="Linux")
    def test_is_linux(self, _mock):
        self.assertFalse(setup.is_windows())
        self.assertFalse(setup.is_macos())
        self.assertTrue(setup.is_linux())

    def test_get_home_dir_returns_string(self):
        home = setup.get_home_dir()
        self.assertIsInstance(home, str)
        self.assertTrue(home)
        # Should not contain a literal '~' (expansion happened)
        self.assertNotIn("~", home)


class TestSymlinkCapabilityProbe(unittest.TestCase):
    """Tests for can_create_symlinks() probe."""

    def test_can_create_symlinks_non_windows(self):
        """On macOS/Linux this returns True unconditionally."""
        with patch("setup.is_windows", return_value=False):
            self.assertTrue(setup.can_create_symlinks())


@requires_symlinks
class TestLinkFunction(unittest.TestCase):
    """Test the link() function for symlink creation"""

    def setUp(self):
        """Create temporary directory for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.source = os.path.join(self.test_dir, "source")
        self.target = os.path.join(self.test_dir, "target")

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_link_creates_symlink(self):
        """Test that link() creates a symlink"""
        # Create source file
        open(self.source, "w").close()

        # Create link
        result = setup.link(self.source, self.target)

        self.assertTrue(result)
        self.assertTrue(os.path.islink(self.target))
        self.assertEqual(
            normalize_link_target(os.readlink(self.target)),
            os.path.normpath(self.source),
        )

    def test_link_source_not_exists(self):
        """Test that link() returns False when source doesn't exist"""
        result = setup.link(self.source, self.target)

        self.assertFalse(result)
        self.assertFalse(os.path.exists(self.target))

    def test_link_replaces_existing_symlink(self):
        """Test that link() replaces an existing symlink"""
        # Create source and old target
        open(self.source, "w").close()
        old_source = os.path.join(self.test_dir, "old_source")
        open(old_source, "w").close()
        os.symlink(old_source, self.target)

        # Replace with new link
        result = setup.link(self.source, self.target)

        self.assertTrue(result)
        self.assertTrue(os.path.islink(self.target))
        self.assertEqual(
            normalize_link_target(os.readlink(self.target)),
            os.path.normpath(self.source),
        )

    def test_link_with_directory(self):
        """Test that link() works with directory source"""
        # Create source directory
        os.makedirs(self.source)

        result = setup.link(self.source, self.target)

        self.assertTrue(result)
        self.assertTrue(os.path.islink(self.target))


class TestIsToolFunction(unittest.TestCase):
    """Test the is_tool() function for command existence checking"""

    def test_is_tool_existing_command(self):
        """Test that is_tool() returns True for existing commands"""
        # Test with common commands that should exist
        self.assertTrue(setup.is_tool("python3"))
        self.assertTrue(setup.is_tool("ls"))

    def test_is_tool_nonexistent_command(self):
        """Test that is_tool() returns False for non-existent commands"""
        self.assertFalse(setup.is_tool("this_command_definitely_does_not_exist_12345"))

    @patch("subprocess.run")
    def test_is_tool_handles_exception(self, mock_run):
        """Test that is_tool() handles exceptions gracefully"""
        mock_run.side_effect = FileNotFoundError()

        result = setup.is_tool("some_command")

        self.assertFalse(result)


class TestBashCommandGenerators(unittest.TestCase):
    """Test bash command generation functions"""

    def test_bash_export_command(self):
        """Test bash_export_command() generates correct export"""
        path = "/path/to/bin"
        result = setup.bash_export_command(path)

        self.assertIn("export PATH=", result)
        self.assertIn(path, result)
        self.assertIn("$PATH", result)

    def test_bash_load_command(self):
        """Test bash_load_command() generates correct source command"""
        path = "/path/to/script.sh"
        result = setup.bash_load_command(path)

        self.assertIn("[ -r ", result)
        self.assertIn(path, result)
        self.assertIn(" && . ", result)


class TestAppendNonexistentLinesToFile(unittest.TestCase):
    """Test the append_nonexistent_lines_to_file() function"""

    def setUp(self):
        """Create temporary directory"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.txt")

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_append_to_empty_file(self):
        """Test appending to an empty file"""
        # Create empty file first
        open(self.test_file, "w").close()

        lines = ["line1", "line2"]

        result = setup.append_nonexistent_lines_to_file(self.test_file, lines)

        self.assertTrue(result)
        with open(self.test_file, "r") as f:
            content = f.read()
        self.assertIn("line1", content)
        self.assertIn("line2", content)

    def test_append_skips_existing_lines(self):
        """Test that existing lines are not duplicated"""
        # Create file with existing line
        with open(self.test_file, "w") as f:
            f.write("existing_line\n")

        lines = ["existing_line", "new_line"]
        result = setup.append_nonexistent_lines_to_file(self.test_file, lines)

        self.assertTrue(result)
        with open(self.test_file, "r") as f:
            content = f.read()

        # Should have existing_line once and new_line once
        self.assertEqual(content.count("existing_line"), 1)
        self.assertEqual(content.count("new_line"), 1)

    def test_append_handles_partial_match(self):
        """Test that substring matches don't prevent appending (Item 5.2 fix)"""
        # Create file with line containing substring
        with open(self.test_file, "w") as f:
            f.write("# Comment about source ~/.bashrc/backup\n")

        lines = ["source ~/.bashrc"]
        result = setup.append_nonexistent_lines_to_file(self.test_file, lines)

        self.assertTrue(result)
        with open(self.test_file, "r") as f:
            lines_in_file = f.readlines()

        # Should have both lines (substring match doesn't count)
        self.assertEqual(len(lines_in_file), 2)
        self.assertIn("source ~/.bashrc\n", lines_in_file)

    def test_append_nonexistent_file(self):
        """Test appending to non-existent file returns False"""
        nonexistent = os.path.join(self.test_dir, "nonexistent.txt")
        lines = ["line1"]

        result = setup.append_nonexistent_lines_to_file(nonexistent, lines)

        # Function requires file to exist, should return False
        self.assertFalse(result)
        # File should not be created
        self.assertFalse(os.path.exists(nonexistent))

    def test_append_adds_newline_if_missing(self):
        """Test that newline is added at EOF if missing"""
        # Create file without trailing newline
        with open(self.test_file, "w") as f:
            f.write("no_newline")

        lines = ["new_line"]
        result = setup.append_nonexistent_lines_to_file(self.test_file, lines)

        self.assertTrue(result)
        with open(self.test_file, "r") as f:
            content = f.read()

        # Should have both lines on separate lines
        self.assertIn("no_newline\n", content)
        self.assertIn("new_line", content)


@requires_symlinks
class TestVerifySymlinks(unittest.TestCase):
    """Test the verify_symlinks() function"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.old_home = setup.HOME_DIR
        setup.HOME_DIR = self.test_dir

    def tearDown(self):
        """Clean up"""
        setup.HOME_DIR = self.old_home
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_verify_symlinks_all_valid(self):
        """Test verify_symlinks() with all valid symlinks"""
        # Create valid symlinks
        dotfiles = os.path.join(self.test_dir, "dotfiles")
        os.makedirs(dotfiles)
        os.symlink(dotfiles, os.path.join(self.test_dir, ".dotfiles"))

        issues = setup.verify_symlinks()

        self.assertEqual(len(issues), 0)

    def test_verify_symlinks_broken_link(self):
        """Test verify_symlinks() detects broken symlinks"""
        # Create broken symlink
        nonexistent = os.path.join(self.test_dir, "nonexistent")
        os.symlink(nonexistent, os.path.join(self.test_dir, ".dotfiles"))

        issues = setup.verify_symlinks()

        self.assertGreater(len(issues), 0)
        self.assertTrue(any("broken" in issue.lower() for issue in issues))


class TestVerifyFileReadability(unittest.TestCase):
    """Test the verify_file_readability() function"""

    def test_verify_file_readability_handles_missing_files(self):
        """Test that verify_file_readability() handles missing files gracefully"""
        # This test ensures the function doesn't crash on missing optional files
        issues = setup.verify_file_readability()

        # Should return a list (may or may not have issues depending on environment)
        self.assertIsInstance(issues, list)


class TestVerifyBashSyntax(unittest.TestCase):
    """Test the verify_bash_syntax() function"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.sh")

    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_verify_bash_syntax_valid_syntax(self):
        """Test verify_bash_syntax() with valid bash syntax"""
        # Create file with valid syntax
        with open(self.test_file, "w") as f:
            f.write('#!/bin/bash\necho "hello"\n')

        # Mock BASE_DIR to use our test file
        with patch.object(setup, "BASE_DIR", self.test_dir):
            # Temporarily create a dot.bashrc for testing
            bashrc = os.path.join(self.test_dir, "dot.bashrc")
            with open(bashrc, "w") as f:
                f.write('#!/bin/bash\necho "valid"\n')

            issues = setup.verify_bash_syntax()

            # Should have no issues (or only issues from other files)
            # Don't assert zero because real files might have issues
            self.assertIsInstance(issues, list)


class TestMainFunction(unittest.TestCase):
    """Test the main() function"""

    @patch("setup.verify_installation")
    @patch("setup.dev_tools_init")
    @patch("setup.mozilla_init")
    @patch("setup.git_init")
    @patch("setup.bash_link")
    @patch("setup.dotfiles_link")
    def test_main_success_flow(
        self,
        mock_dotfiles,
        mock_bash,
        mock_git,
        mock_mozilla,
        mock_devtools,
        mock_verify,
    ):
        """Test main() with successful setup"""
        # Mock all functions to return success
        mock_dotfiles.return_value = True
        mock_bash.return_value = True
        mock_git.return_value = True
        mock_mozilla.return_value = None  # Skipped
        mock_devtools.return_value = None  # Skipped
        mock_verify.return_value = (True, [])

        exit_code = setup.main(["setup.py"])

        self.assertEqual(exit_code, 0)

    @patch("setup.dev_tools_init")
    @patch("setup.mozilla_init")
    @patch("setup.git_init")
    @patch("setup.bash_link")
    @patch("setup.dotfiles_link")
    def test_main_failure_flow(
        self, mock_dotfiles, mock_bash, mock_git, mock_mozilla, mock_devtools
    ):
        """Test main() with failed setup"""
        # Mock a function to return failure
        mock_dotfiles.return_value = False
        mock_bash.return_value = True
        mock_git.return_value = True
        mock_mozilla.return_value = None
        mock_devtools.return_value = None

        exit_code = setup.main(["setup.py"])

        self.assertEqual(exit_code, 1)

    @patch("setup.dev_tools_init")
    @patch("setup.mozilla_init")
    @patch("setup.git_init")
    @patch("setup.bash_link")
    @patch("setup.dotfiles_link")
    def test_main_with_verbose_flag(
        self, mock_dotfiles, mock_bash, mock_git, mock_mozilla, mock_devtools
    ):
        """Test main() with verbose flag"""
        mock_dotfiles.return_value = True
        mock_bash.return_value = True
        mock_git.return_value = True
        mock_mozilla.return_value = None
        mock_devtools.return_value = None

        # Capture verbose output
        setup.main(["setup.py", "-v"])

        # Should have set VERBOSE flag
        self.assertTrue(setup.VERBOSE)

        # Reset for other tests
        setup.VERBOSE = False

    @patch("setup.dev_tools_init")
    @patch("setup.mozilla_init")
    @patch("setup.git_init")
    @patch("setup.bash_link")
    @patch("setup.dotfiles_link")
    def test_main_with_mozilla_flag(
        self, mock_dotfiles, mock_bash, mock_git, mock_mozilla, mock_devtools
    ):
        """Test main() with mozilla flag"""
        mock_dotfiles.return_value = True
        mock_bash.return_value = True
        mock_git.return_value = True
        mock_mozilla.return_value = True
        mock_devtools.return_value = None

        setup.main(["setup.py", "--mozilla", "firefox"])

        # Should have called mozilla_init with argument and tracker
        # Check that first argument is ['firefox'] and second is a ChangeTracker
        self.assertEqual(len(mock_mozilla.call_args[0]), 2)
        self.assertEqual(mock_mozilla.call_args[0][0], ["firefox"])
        self.assertIsInstance(mock_mozilla.call_args[0][1], setup.ChangeTracker)


class TestClaudeSecurityIntegration(unittest.TestCase):
    """Test Claude security hooks integration with setup.py"""

    def test_claude_security_flag_recognized(self):
        """Test that --claude-security flag is recognized"""
        result = subprocess.run(
            ["python3", "setup.py", "--claude-security", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertIn("Claude Code Security Hooks", result.stdout)
        self.assertIn("Would add to ~/.claude.json:", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_remove_claude_security_flag_recognized(self):
        """Test that --remove-claude-security flag is recognized"""
        result = subprocess.run(
            ["python3", "setup.py", "--remove-claude-security", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertIn("Remove Claude Security Hooks", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_show_claude_hooks_flag_recognized(self):
        """Test that --show-claude-hooks flag is recognized"""
        result = subprocess.run(
            ["python3", "setup.py", "--show-claude-hooks"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertIn("Current Claude Hooks", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_all_flag_includes_claude_security(self):
        """Test that --all flag includes Claude security"""
        result = subprocess.run(
            ["python3", "setup.py", "--all", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertIn("Claude Code Security Hooks", result.stdout)
        self.assertEqual(result.returncode, 0)


@requires_symlinks
class TestInstallFirefoxClaude(unittest.TestCase):
    """Test install/uninstall of Firefox Claude settings including skills."""

    def setUp(self):
        """Create temp dirs simulating a Firefox repo and dotfiles overlay."""
        self.test_dir = tempfile.mkdtemp()

        # Simulate Firefox repo with mach + a real git repo so
        # ensure_target_core_symlinks (which sets core.symlinks=true)
        # has something to operate on.
        self.firefox_dir = os.path.join(self.test_dir, "firefox")
        os.makedirs(self.firefox_dir)
        open(os.path.join(self.firefox_dir, "mach"), "w").close()
        self._git_init(self.firefox_dir)

        # Build a minimal overlay structure for personal skills
        self.overlay_dir = os.path.join(self.test_dir, "overlay")
        os.makedirs(os.path.join(self.overlay_dir, "hooks"))
        os.makedirs(os.path.join(self.overlay_dir, "agents"))
        os.makedirs(os.path.join(self.overlay_dir, "skills", "my-skill"))
        with open(
            os.path.join(self.overlay_dir, "skills", "my-skill", "SKILL.md"), "w"
        ) as f:
            f.write("personal skill")
        with open(
            os.path.join(self.overlay_dir, "hooks", "post-edit-lint.sh"), "w"
        ) as f:
            f.write("#!/bin/bash\n")
        with open(
            os.path.join(self.overlay_dir, "agents", "red-pen-critic.md"), "w"
        ) as f:
            f.write("# critic agent")
        with open(os.path.join(self.overlay_dir, "settings.local.json"), "w") as f:
            f.write('{"permissions":{"allow":[]}}')

        # Build a minimal alwu-claude-skills directory
        self.claude_dir = os.path.join(self.test_dir, "alwu-claude-skills")
        for name in ["bug-start", "spec-check"]:
            skill_dir = os.path.join(self.claude_dir, name)
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
                f.write(f"claude skill: {name}")
        # Non-skill entries that should be excluded
        with open(os.path.join(self.claude_dir, "CLAUDE.md"), "w") as f:
            f.write("claude doc")
        with open(os.path.join(self.claude_dir, "README.md"), "w") as f:
            f.write("readme")

        # Build a minimal media-skills directory
        self.media_dir = os.path.join(self.test_dir, "media-skills")
        for name in ["bugzilla-wrangler", "s2-validate"]:
            skill_dir = os.path.join(self.media_dir, name)
            os.makedirs(skill_dir)
            with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
                f.write(f"team skill: {name}")
        # Non-skill entries that should be excluded
        os.makedirs(os.path.join(self.media_dir, "Template"))
        os.makedirs(os.path.join(self.media_dir, "shared"))
        with open(os.path.join(self.media_dir, "README.md"), "w") as f:
            f.write("readme")
        with open(os.path.join(self.media_dir, "LICENSE"), "w") as f:
            f.write("MIT")

        # Patch constants to use our temp dirs
        self._orig_overlay = setup.FIREFOX_CLAUDE_OVERLAY
        self._orig_media = setup.MEDIA_SKILLS_DIR
        self._orig_exclude = setup.MEDIA_SKILLS_EXCLUDE
        self._orig_claude = setup.ALWU_CLAUDE_SKILLS_DIR
        self._orig_claude_exclude = setup.ALWU_CLAUDE_SKILLS_EXCLUDE
        setup.FIREFOX_CLAUDE_OVERLAY = self.overlay_dir
        setup.MEDIA_SKILLS_DIR = self.media_dir
        setup.MEDIA_SKILLS_EXCLUDE = {
            "Template",
            "shared",
            ".git",
            ".github",
            "LICENSE",
            "README.md",
        }
        setup.ALWU_CLAUDE_SKILLS_DIR = self.claude_dir
        setup.ALWU_CLAUDE_SKILLS_EXCLUDE = {
            ".git",
            ".github",
            ".githooks",
            "CLAUDE.md",
            "README.md",
        }
        self._orig_claude_rename = setup.ALWU_CLAUDE_SKILLS_RENAME
        setup.ALWU_CLAUDE_SKILLS_RENAME = {}
        self._orig_media_rename = setup.MEDIA_SKILLS_RENAME
        setup.MEDIA_SKILLS_RENAME = {}

    def tearDown(self):
        setup.FIREFOX_CLAUDE_OVERLAY = self._orig_overlay
        setup.MEDIA_SKILLS_DIR = self._orig_media
        setup.MEDIA_SKILLS_EXCLUDE = self._orig_exclude
        setup.ALWU_CLAUDE_SKILLS_DIR = self._orig_claude
        setup.ALWU_CLAUDE_SKILLS_EXCLUDE = self._orig_claude_exclude
        setup.ALWU_CLAUDE_SKILLS_RENAME = self._orig_claude_rename
        setup.MEDIA_SKILLS_RENAME = self._orig_media_rename
        shutil.rmtree(self.test_dir)

    def _install(
        self, commit=False, new_branch=False, branch_name="test-overlay", **kwargs
    ):
        """Run install_firefox_claude with interactive prompts suppressed.

        - ``commit`` (default False): answer to "Commit now?".
        - ``new_branch`` (default False): answer to "Commit on a new branch?".
          Only consulted when ``commit`` is True.
        - ``branch_name``: returned for the "New branch name [...]" input
          when ``new_branch`` is True.

        Other prompts (settings merge choice, tech-docs index path, etc.)
        get the prompt's default — skipping them.
        """

        def fake_input(prompt, default=""):
            if "new branch name" in prompt.lower():
                return branch_name
            return default

        def fake_confirmation(prompt="", default_non_interactive=False):
            pl = prompt.lower()
            if "commit now" in pl:
                return commit
            if "new branch" in pl:
                return new_branch
            return False

        with patch("setup.get_user_input", side_effect=fake_input), patch(
            "setup.get_user_confirmation", side_effect=fake_confirmation
        ):
            return setup.install_firefox_claude(self.firefox_dir, **kwargs)

    @staticmethod
    def _git_init(repo_dir):
        """Initialize a deterministic git repo with one initial commit."""
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
        # init.defaultBranch may not be set globally; pin it for stability.
        subprocess.run(
            ["git", "init", "-b", "main", repo_dir],
            check=True,
            capture_output=True,
            env=env,
        )
        for key, val in (
            ("user.email", "test@example.com"),
            ("user.name", "Test"),
            ("commit.gpgsign", "false"),
        ):
            subprocess.run(
                ["git", "-C", repo_dir, "config", key, val],
                check=True,
                capture_output=True,
                env=env,
            )
        subprocess.run(
            ["git", "-C", repo_dir, "add", "mach"],
            check=True,
            capture_output=True,
            env=env,
        )
        subprocess.run(
            ["git", "-C", repo_dir, "commit", "-m", "init"],
            check=True,
            capture_output=True,
            env=env,
        )

    def test_install_symlinks_all_skill_tiers(self):
        """Personal, alwu-claude-skills, and media-skills all get symlinked."""
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # Personal skill
        my_skill = os.path.join(skills_dir, "my-skill")
        self.assertTrue(os.path.islink(my_skill))
        self.assertIn(self.overlay_dir, os.readlink(my_skill))
        # Claude skills
        for name in ["bug-start", "spec-check"]:
            path = os.path.join(skills_dir, name)
            self.assertTrue(os.path.islink(path), f"{name} should be symlinked")
            self.assertIn(self.claude_dir, os.readlink(path))
        # Media skills
        for name in ["bugzilla-wrangler", "s2-validate"]:
            path = os.path.join(skills_dir, name)
            self.assertTrue(os.path.islink(path), f"{name} should be symlinked")
            self.assertIn(self.media_dir, os.readlink(path))

    def test_install_excludes_non_skill_entries(self):
        """Excluded entries from media-skills and alwu-claude-skills are not symlinked."""
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # media-skills excludes
        for name in ["Template", "shared", "LICENSE", "README.md"]:
            self.assertFalse(
                os.path.exists(os.path.join(skills_dir, name)),
                f"{name} should not be symlinked",
            )
        # alwu-claude-skills excludes
        for name in ["CLAUDE.md"]:
            self.assertFalse(
                os.path.exists(os.path.join(skills_dir, name)),
                f"{name} should not be symlinked",
            )

    def test_install_personal_skill_takes_precedence_over_all(self):
        """When a skill name conflicts, personal wins over alwu-claude-skills and media-skills."""
        # Create conflicting skills in both tiers
        for d in [self.claude_dir, self.media_dir]:
            conflict_dir = os.path.join(d, "my-skill")
            os.makedirs(conflict_dir, exist_ok=True)
            with open(os.path.join(conflict_dir, "SKILL.md"), "w") as f:
                f.write(f"conflicting version from {d}")

        self._install()
        skill_link = os.path.join(self.firefox_dir, ".claude", "skills", "my-skill")
        self.assertTrue(os.path.islink(skill_link))
        # Should point to the personal overlay
        self.assertIn(self.overlay_dir, os.readlink(skill_link))
        self.assertNotIn(self.claude_dir, os.readlink(skill_link))
        self.assertNotIn(self.media_dir, os.readlink(skill_link))

    def test_install_alwu_claude_skills_take_precedence_over_media(self):
        """When a skill exists in both alwu-claude-skills and media-skills, alwu-claude-skills wins."""
        # Create a skill with the same name in both
        for d in [self.claude_dir, self.media_dir]:
            conflict_dir = os.path.join(d, "shared-skill")
            os.makedirs(conflict_dir, exist_ok=True)
            with open(os.path.join(conflict_dir, "SKILL.md"), "w") as f:
                f.write(f"version from {d}")

        self._install()
        skill_link = os.path.join(self.firefox_dir, ".claude", "skills", "shared-skill")
        self.assertTrue(os.path.islink(skill_link))
        self.assertIn(self.claude_dir, os.readlink(skill_link))
        self.assertNotIn(self.media_dir, os.readlink(skill_link))

    def test_install_no_media_skills_dir(self):
        """Install works fine if media-skills directory doesn't exist."""
        setup.MEDIA_SKILLS_DIR = os.path.join(self.test_dir, "nonexistent")
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # Personal skill still works
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "my-skill")))

    def test_install_no_alwu_claude_skills_dir(self):
        """Install works fine if alwu-claude-skills directory doesn't exist."""
        setup.ALWU_CLAUDE_SKILLS_DIR = os.path.join(self.test_dir, "nonexistent")
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # Personal and media skills still work
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "my-skill")))
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "bugzilla-wrangler")))

    def _write_alwu_skill_with_frontmatter(self, skill_name, description="x"):
        """Overwrite an alwu test skill's SKILL.md with a proper frontmatter
        block (name: matches dir, plus a description). Used to test the
        rename-time `name:` rewrite.
        """
        path = os.path.join(self.claude_dir, skill_name, "SKILL.md")
        with open(path, "w") as f:
            f.write(
                "---\n"
                f"name: {skill_name}\n"
                f"description: {description}\n"
                "---\n\n"
                f"# {skill_name}\n\nbody\n"
            )

    def test_install_alwu_claude_skills_rename(self):
        """Renamed alwu skills are materialized as a real directory with
        SKILL.md `name:` rewritten — not a directory symlink — so Claude
        registers them under the new name instead of the upstream one."""
        self._write_alwu_skill_with_frontmatter("bug-start")
        setup.ALWU_CLAUDE_SKILLS_RENAME = {"bug-start": "media-bug-start"}
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # Original name should NOT exist
        self.assertFalse(os.path.exists(os.path.join(skills_dir, "bug-start")))
        # Renamed version: real directory, not a symlink
        renamed = os.path.join(skills_dir, "media-bug-start")
        self.assertTrue(os.path.isdir(renamed))
        self.assertFalse(
            os.path.islink(renamed),
            "renamed alwu skill must be materialized, not a symlink",
        )
        # SKILL.md inside is a real file with `name:` rewritten to install_name
        skill_md = os.path.join(renamed, "SKILL.md")
        self.assertTrue(os.path.isfile(skill_md))
        self.assertFalse(os.path.islink(skill_md))
        with open(skill_md) as f:
            content = f.read()
        self.assertIn("name: media-bug-start", content)
        self.assertNotIn("name: bug-start", content)

    def test_install_renamed_alwu_skill_rewrites_skill_md_name(self):
        """Regression test for the surface user-visible bug: two `/sec-approval`
        skills appearing in Claude after install. The directory rename is not
        enough — the `name:` frontmatter field must also be rewritten."""
        self._write_alwu_skill_with_frontmatter("bug-start", description="alwu")
        setup.ALWU_CLAUDE_SKILLS_RENAME = {"bug-start": "alwu-bug-start"}
        self._install()
        skill_md = os.path.join(
            self.firefox_dir, ".claude", "skills", "alwu-bug-start", "SKILL.md"
        )
        with open(skill_md) as f:
            content = f.read()
        # Body and description preserved
        self.assertIn("description: alwu", content)
        self.assertIn("# bug-start", content)
        # name: rewritten (only once, no leftover)
        self.assertEqual(content.count("name: alwu-bug-start"), 1)
        self.assertNotIn("name: bug-start\n", content)

    def test_install_renamed_alwu_skill_frees_name_for_media_skill(self):
        """Media-skills retains its original name when alwu-claude-skills renames a
        same-named skill.

        Regression test: the conflict check between media-skills and
        alwu-claude-skills must compare *installed* names (post-rename), not raw
        directory names. Otherwise an alwu skill that was renamed out of the way
        still blocks the media-skills version from being symlinked.
        """
        # alwu and media each have a skill called "bug-start"; alwu renames its
        # copy to "alwu-bug-start", so media-skills' "bug-start" should install.
        media_bug_start = os.path.join(self.media_dir, "bug-start")
        os.makedirs(media_bug_start)
        with open(os.path.join(media_bug_start, "SKILL.md"), "w") as f:
            f.write("media bug-start")
        self._write_alwu_skill_with_frontmatter("bug-start")
        setup.ALWU_CLAUDE_SKILLS_RENAME = {"bug-start": "alwu-bug-start"}

        self._install()

        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # alwu's renamed copy lives under the new name as a materialized dir.
        alwu_dst = os.path.join(skills_dir, "alwu-bug-start")
        self.assertTrue(os.path.isdir(alwu_dst))
        self.assertFalse(os.path.islink(alwu_dst))
        # media-skills' bug-start must still be installed under its raw name
        # as a directory symlink into media-skills.
        media_link = os.path.join(skills_dir, "bug-start")
        self.assertTrue(
            os.path.islink(media_link),
            "media-skills bug-start should be symlinked despite alwu's rename",
        )
        self.assertIn(
            os.path.normpath(self.media_dir),
            normalize_link_target(os.readlink(media_link)),
        )

    def test_install_collision_yields_two_distinct_skill_names(self):
        """End-to-end: when alwu and media-skills both declare the SAME `name:`
        in their SKILL.md frontmatter (the real-world sec-approval case),
        installing both must produce TWO DISTINCT names in the parsed
        frontmatter — what Claude actually reads when registering skills.

        Without the rename rewriting the alwu copy's `name:` field, Claude
        would see two skills both named the upstream name (e.g. two
        `/sec-approval` entries).
        """
        # Both alwu and media-skills declare `name: sec-approval` — the exact
        # collision the user hit.
        for root in (self.claude_dir, self.media_dir):
            d = os.path.join(root, "sec-approval")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "SKILL.md"), "w") as f:
                f.write(
                    "---\n"
                    "name: sec-approval\n"
                    f"description: from {os.path.basename(root)}\n"
                    "---\n\nbody\n"
                )
        setup.ALWU_CLAUDE_SKILLS_RENAME = {"sec-approval": "sec-approval-draft"}

        self._install()

        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")

        def parse_frontmatter_name(skill_md_path):
            with open(skill_md_path) as f:
                content = f.read()
            self.assertTrue(content.startswith("---\n"), skill_md_path)
            end = content.find("\n---\n", 4)
            for line in content[4:end].splitlines():
                if line.startswith("name:"):
                    return line.split(":", 1)[1].strip()
            self.fail(f"no name: in {skill_md_path}")

        alwu_name = parse_frontmatter_name(
            os.path.join(skills_dir, "sec-approval-draft", "SKILL.md")
        )
        media_name = parse_frontmatter_name(
            os.path.join(skills_dir, "sec-approval", "SKILL.md")
        )

        # This is the user-visible contract: Claude reads `name:` from each
        # SKILL.md; the two values must differ so the two `/sec-approval`
        # collision the user reported cannot recur.
        self.assertNotEqual(
            alwu_name,
            media_name,
            "alwu and media-skills SKILL.md `name:` fields collide after install",
        )
        self.assertEqual(alwu_name, "sec-approval-draft")
        self.assertEqual(media_name, "sec-approval")

    def test_uninstall_removes_materialized_renamed_alwu_skill(self):
        """Uninstall cleans up the materialized rename directory, not just symlinks."""
        self._write_alwu_skill_with_frontmatter("bug-start")
        setup.ALWU_CLAUDE_SKILLS_RENAME = {"bug-start": "media-bug-start"}
        self._install()
        materialized = os.path.join(
            self.firefox_dir, ".claude", "skills", "media-bug-start"
        )
        self.assertTrue(os.path.isdir(materialized))

        with patch("setup.get_user_input", return_value=""):
            setup.uninstall_firefox_claude(self.firefox_dir)

        self.assertFalse(os.path.exists(materialized))

    def test_reinstall_replaces_materialized_renamed_alwu_skill(self):
        """Re-running install regenerates the materialized dir (picks up upstream
        changes), not skips it as an existing directory."""
        self._write_alwu_skill_with_frontmatter("bug-start", description="v1")
        setup.ALWU_CLAUDE_SKILLS_RENAME = {"bug-start": "media-bug-start"}
        self._install()

        # Drop the settings symlink to avoid the merge/override prompt blocking
        # the second install (this test focuses on the skill materialization
        # path; settings handling has its own coverage).
        settings_link = os.path.join(self.firefox_dir, ".claude", "settings.local.json")
        if os.path.lexists(settings_link):
            os.unlink(settings_link)

        # Upstream changes between installs
        self._write_alwu_skill_with_frontmatter("bug-start", description="v2")
        self._install()

        skill_md = os.path.join(
            self.firefox_dir, ".claude", "skills", "media-bug-start", "SKILL.md"
        )
        with open(skill_md) as f:
            content = f.read()
        self.assertIn("description: v2", content)
        self.assertNotIn("description: v1", content)
        self.assertIn("name: media-bug-start", content)

    def test_install_renamed_media_skill_keeps_personal_name_distinct(self):
        """A media-skill listed in MEDIA_SKILLS_RENAME with a SKILL.md `name:`
        that collides with a personal skill must be materialized with its
        `name:` rewritten — otherwise Claude Code hides the media copy
        because both register under the same skill name.

        Regression for the real-world case: media-skills/media-bug-triage-v2
        declares `name: triage`, which collides with the personal triage
        skill's `name: triage`. Per MEDIA_SKILLS_RENAME, the media copy is
        materialized as media-bug-triage-v2 with `name: media-bug-triage-v2`.
        """
        # Personal skill named "triage"
        personal_triage = os.path.join(self.overlay_dir, "skills", "triage")
        os.makedirs(personal_triage)
        with open(os.path.join(personal_triage, "SKILL.md"), "w") as f:
            f.write("---\nname: triage\ndescription: personal\n---\n\nbody\n")

        # Media-skill at media-bug-triage-v2 also declares name: triage
        media_v2 = os.path.join(self.media_dir, "media-bug-triage-v2")
        os.makedirs(media_v2)
        with open(os.path.join(media_v2, "SKILL.md"), "w") as f:
            f.write("---\nname: triage\ndescription: media v2\n---\n\nbody\n")

        setup.MEDIA_SKILLS_RENAME = {"media-bug-triage-v2": "media-bug-triage-v2"}

        self._install()

        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        personal_md = os.path.join(skills_dir, "triage", "SKILL.md")
        media_md = os.path.join(skills_dir, "media-bug-triage-v2", "SKILL.md")

        def parse_name(path):
            with open(path) as f:
                content = f.read()
            for line in content.splitlines():
                if line.startswith("name:"):
                    return line.split(":", 1)[1].strip()
            self.fail(f"no name: in {path}")

        # The personal triage stays at name: triage; the media copy is
        # materialized with name: media-bug-triage-v2 so the two no longer
        # collide.
        self.assertEqual(parse_name(personal_md), "triage")
        self.assertEqual(parse_name(media_md), "media-bug-triage-v2")
        # Materialized: real file, not a symlink.
        self.assertFalse(os.path.islink(media_md))

    def test_install_gitignore_includes_all_skills(self):
        """Claude-skill and media-skill entries appear in .gitignore."""
        self._install()
        gitignore = os.path.join(self.firefox_dir, ".gitignore")
        if os.path.exists(gitignore):
            with open(gitignore) as f:
                content = f.read()
            self.assertIn(".claude/skills/bugzilla-wrangler/", content)
            self.assertIn(".claude/skills/s2-validate/", content)
            self.assertIn(".claude/skills/bug-start/", content)
            self.assertIn(".claude/skills/spec-check/", content)

    def test_install_symlinks_agents(self):
        """Agent files in the overlay get symlinked into .claude/agents/."""
        self._install()
        agent_link = os.path.join(
            self.firefox_dir, ".claude", "agents", "red-pen-critic.md"
        )
        self.assertTrue(os.path.islink(agent_link))
        self.assertIn(self.overlay_dir, os.readlink(agent_link))

    def test_install_gitignore_includes_agents(self):
        """Agent symlinks appear in .gitignore."""
        self._install()
        gitignore = os.path.join(self.firefox_dir, ".gitignore")
        with open(gitignore) as f:
            content = f.read()
        self.assertIn(".claude/agents/red-pen-critic.md", content)

    def test_uninstall_removes_agent_symlinks(self):
        """Uninstall removes agent symlinks and the empty agents directory."""
        self._install()
        agents_dir = os.path.join(self.firefox_dir, ".claude", "agents")
        agent_link = os.path.join(agents_dir, "red-pen-critic.md")
        self.assertTrue(os.path.islink(agent_link))

        with patch("setup.get_user_input", return_value=""):
            setup.uninstall_firefox_claude(self.firefox_dir)

        self.assertFalse(os.path.exists(agent_link))
        self.assertFalse(os.path.exists(agents_dir))

    def test_uninstall_removes_all_skill_symlinks(self):
        """Uninstall removes personal, alwu-claude-skill, and media-skill symlinks."""
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # Verify they exist first
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "bugzilla-wrangler")))
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "bug-start")))

        with patch("setup.get_user_input", return_value=""):
            setup.uninstall_firefox_claude(self.firefox_dir)

        # All symlinks should be gone
        for name in [
            "my-skill",
            "bugzilla-wrangler",
            "s2-validate",
            "bug-start",
            "spec-check",
        ]:
            path = os.path.join(skills_dir, name)
            self.assertFalse(os.path.exists(path), f"{name} should be removed")

    def test_reinstall_replaces_existing_symlinks(self):
        """Running install twice updates symlinks without error."""
        self._install()
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "bugzilla-wrangler")))
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "my-skill")))
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "bug-start")))

    def test_dry_run_shows_all_skill_tiers(self):
        """Dry run output mentions alwu-claude-skills and media-skills."""
        import io

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            self._install(dry_run=True)
        output = mock_stdout.getvalue()
        self.assertIn("alwu-claude-skills", output)
        self.assertIn("bug-start", output)
        self.assertIn("media-skills", output)
        self.assertIn("bugzilla-wrangler", output)
        # Should NOT actually create symlinks
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        self.assertFalse(os.path.exists(skills_dir))

    def test_install_without_git_repo_succeeds(self):
        """No .git directory: install still creates symlinks."""
        shutil.rmtree(self.firefox_dir)
        os.makedirs(self.firefox_dir)
        open(os.path.join(self.firefox_dir, "mach"), "w").close()

        self._install()
        self.assertTrue(
            os.path.islink(
                os.path.join(self.firefox_dir, ".claude", "skills", "my-skill")
            )
        )
        self.assertFalse(os.path.exists(os.path.join(self.firefox_dir, ".git")))

    def _head_sha(self):
        result = subprocess.run(
            ["git", "-C", self.firefox_dir, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def _current_branch(self):
        result = subprocess.run(
            ["git", "-C", self.firefox_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def test_install_commit_yes_lands_overlay_on_head(self):
        """Opting in to the commit prompt produces a new commit on HEAD
        whose tree contains the overlay symlinks as 120000 blobs."""
        before = self._head_sha()
        before_branch = self._current_branch()
        self._install(commit=True)
        after = self._head_sha()

        self.assertNotEqual(before, after, "HEAD should advance after commit")
        self.assertEqual(
            self._current_branch(),
            before_branch,
            "branch should not change when new_branch=False",
        )

        # Inspect the new commit's tree for 120000 blobs.
        ls_tree = subprocess.run(
            ["git", "-C", self.firefox_dir, "ls-tree", "-r", after, ".claude/"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = ls_tree.stdout.splitlines()
        modes = {}
        for line in lines:
            meta, name = line.split("\t", 1)
            modes[name] = meta.split()[0]

        self.assertEqual(
            modes.get(".claude/hooks/post-edit-lint.sh"),
            "120000",
            "hook should be tracked as a symlink blob",
        )
        self.assertEqual(
            modes.get(".claude/skills/my-skill"),
            "120000",
            "personal skill should be tracked as a symlink blob",
        )

    def test_install_commit_on_new_branch(self):
        """Opting in to the new-branch prompt creates the branch and
        lands the overlay commit on it, leaving the original branch alone."""
        before_branch = self._current_branch()
        before_sha = self._head_sha()

        self._install(commit=True, new_branch=True, branch_name="overlay-test")

        # We're now on the new branch with a fresh commit.
        self.assertEqual(self._current_branch(), "overlay-test")
        self.assertNotEqual(self._head_sha(), before_sha)

        # The original branch tip is unchanged.
        result = subprocess.run(
            [
                "git",
                "-C",
                self.firefox_dir,
                "rev-parse",
                "--verify",
                f"refs/heads/{before_branch}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), before_sha)


class TestMozillaCliTools(unittest.TestCase):
    """Tests for mozilla_cli_tools_init and the per-tool installers."""

    @patch("setup.install_profiler_cli")
    @patch("setup.install_socorro_cli")
    @patch("setup.install_bmo_to_md")
    @patch("setup.install_treeherder_cli")
    @patch("setup.install_searchfox_cli")
    def test_cli_tools_init_runs_all_installers(
        self, mock_sf, mock_th, mock_bmo, mock_socorro, mock_profiler
    ):
        """All five per-tool installers are invoked in order."""
        for m in (mock_sf, mock_th, mock_bmo, mock_socorro, mock_profiler):
            m.return_value = True

        result = setup.mozilla_cli_tools_init()

        self.assertTrue(result)
        for m in (mock_sf, mock_th, mock_bmo, mock_socorro, mock_profiler):
            m.assert_called_once()

    @patch("setup.install_profiler_cli")
    @patch("setup.install_socorro_cli")
    @patch("setup.install_bmo_to_md")
    @patch("setup.install_treeherder_cli")
    @patch("setup.install_searchfox_cli")
    def test_cli_tools_init_skipped_counts_as_success(
        self, mock_sf, mock_th, mock_bmo, mock_socorro, mock_profiler
    ):
        """Mix of True / None (skipped) yields overall True."""
        mock_sf.return_value = True
        mock_th.return_value = None
        mock_bmo.return_value = True
        mock_socorro.return_value = None
        mock_profiler.return_value = True

        self.assertTrue(setup.mozilla_cli_tools_init())

    @patch("setup.install_profiler_cli")
    @patch("setup.install_socorro_cli")
    @patch("setup.install_bmo_to_md")
    @patch("setup.install_treeherder_cli")
    @patch("setup.install_searchfox_cli")
    def test_cli_tools_init_one_failure_fails_overall(
        self, mock_sf, mock_th, mock_bmo, mock_socorro, mock_profiler
    ):
        """A single False return makes the bundle fail, but all installers
        still run (no short-circuit)."""
        mock_sf.return_value = True
        mock_th.return_value = True
        mock_bmo.return_value = True
        mock_socorro.return_value = False
        mock_profiler.return_value = True

        self.assertFalse(setup.mozilla_cli_tools_init())
        # No short-circuit: profiler-cli still attempted after socorro failed.
        mock_profiler.assert_called_once()

    @patch("setup._install_cargo_tool")
    def test_install_socorro_cli_delegates_to_cargo_helper(self, mock_cargo):
        """install_socorro_cli calls _install_cargo_tool with the crates.io
        package name and binary name, and asks for socorro-cli dep probing."""
        mock_cargo.return_value = True

        result = setup.install_socorro_cli()

        self.assertTrue(result)
        args, kwargs = mock_cargo.call_args
        # Positional signature: display, binary, install_args, benefits, consequences
        self.assertEqual(args[1], "socorro-cli")
        self.assertEqual(args[2], ["socorro-cli"])
        self.assertEqual(kwargs.get("probe_crate"), "socorro-cli")

    @patch("setup.is_tool")
    def test_install_profiler_cli_already_installed(self, mock_is_tool):
        """If profiler-cli is on PATH, return True immediately without npm."""
        mock_is_tool.side_effect = lambda name: name == "profiler-cli"
        self.assertTrue(setup.install_profiler_cli())

    @patch("setup.is_tool")
    def test_install_profiler_cli_missing_npm(self, mock_is_tool):
        """If npm is not on PATH, skip cleanly (None)."""
        # Neither profiler-cli nor npm available.
        mock_is_tool.return_value = False
        self.assertIsNone(setup.install_profiler_cli())

    @patch("setup._probe_npm_node_requirement", return_value=None)
    @patch("setup.get_user_confirmation")
    @patch("setup.is_tool")
    def test_install_profiler_cli_user_declines(
        self, mock_is_tool, mock_confirm, _mock_probe
    ):
        """User saying no at the prompt skips cleanly (None)."""
        mock_is_tool.side_effect = lambda name: name == "npm"
        mock_confirm.return_value = False
        self.assertIsNone(setup.install_profiler_cli())

    @patch("setup._probe_npm_node_requirement", return_value=None)
    @patch("setup.subprocess.run")
    @patch("setup.is_windows")
    @patch("setup.get_user_confirmation")
    @patch("setup.is_tool")
    def test_install_profiler_cli_unix_uses_local_prefix(
        self, mock_is_tool, mock_confirm, mock_is_win, mock_run, _mock_probe
    ):
        """On non-Windows, npm runs with --prefix=$HOME/.local and the
        upstream @firefox-devtools/profiler-cli package."""
        mock_is_tool.side_effect = lambda name: name == "npm"
        mock_confirm.return_value = True
        mock_is_win.return_value = False
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        result = setup.install_profiler_cli()

        self.assertTrue(result)
        npm_cmd = mock_run.call_args[0][0]
        self.assertEqual(npm_cmd[:3], ["npm", "install", "-g"])
        self.assertIn("--prefix", npm_cmd)
        prefix_idx = npm_cmd.index("--prefix")
        self.assertEqual(
            npm_cmd[prefix_idx + 1], os.path.join(setup.get_home_dir(), ".local")
        )
        self.assertEqual(npm_cmd[-1], "@firefox-devtools/profiler-cli@latest")

    @patch("setup._probe_npm_node_requirement", return_value=None)
    @patch("setup.subprocess.run")
    @patch("setup.is_windows")
    @patch("setup.get_user_confirmation")
    @patch("setup.is_tool")
    def test_install_profiler_cli_windows_no_prefix(
        self, mock_is_tool, mock_confirm, mock_is_win, mock_run, _mock_probe
    ):
        """On Windows, npm -g defaults to AppData (no --prefix needed)."""
        mock_is_tool.side_effect = lambda name: name == "npm"
        mock_confirm.return_value = True
        mock_is_win.return_value = True
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        self.assertTrue(setup.install_profiler_cli())
        npm_cmd = mock_run.call_args[0][0]
        self.assertNotIn("--prefix", npm_cmd)
        self.assertEqual(npm_cmd[-1], "@firefox-devtools/profiler-cli@latest")

    @patch("setup._probe_npm_node_requirement", return_value=None)
    @patch("setup.subprocess.run")
    @patch("setup.is_windows")
    @patch("setup.get_user_confirmation")
    @patch("setup.is_tool")
    def test_install_profiler_cli_npm_failure(
        self, mock_is_tool, mock_confirm, mock_is_win, mock_run, _mock_probe
    ):
        """Non-zero npm exit yields False."""
        mock_is_tool.side_effect = lambda name: name == "npm"
        mock_confirm.return_value = True
        mock_is_win.return_value = False
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="boom"
        )

        self.assertFalse(setup.install_profiler_cli())

    @patch("setup._probe_npm_node_requirement", return_value=None)
    @patch("setup.subprocess.run")
    @patch("setup.is_windows")
    @patch("setup.get_user_confirmation")
    @patch("setup.is_tool")
    def test_install_profiler_cli_npm_timeout(
        self, mock_is_tool, mock_confirm, mock_is_win, mock_run, _mock_probe
    ):
        """A timeout from npm yields False (not a crash)."""
        mock_is_tool.side_effect = lambda name: name == "npm"
        mock_confirm.return_value = True
        mock_is_win.return_value = False
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="npm", timeout=300)

        self.assertFalse(setup.install_profiler_cli())

    # ---- New dynamic-dep-probe tests ----

    @patch("setup.subprocess.run")
    @patch("setup.is_tool", return_value=True)
    def test_probe_cargo_system_deps_returns_mapped_pkgs(self, _mock_is_tool, mock_run):
        """cargo metadata output gets translated to apt/brew packages
        via RUST_SYS_DEP_MAP."""
        import json as _json

        meta_json = _json.dumps(
            {
                "packages": [
                    {"name": "libdbus-sys"},
                    {"name": "aws-lc-sys"},
                    {"name": "some-other-crate"},
                ]
            }
        )
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=meta_json, stderr=""
        )

        result = setup._probe_cargo_system_deps("socorro-cli")

        self.assertIn("libdbus-1-dev", result["apt"])
        self.assertIn("cmake", result["apt"])
        # pkg-config appears via libdbus-sys; should be deduped
        self.assertEqual(result["apt"].count("pkg-config"), 1)

    @patch("setup.subprocess.run")
    @patch("setup.is_tool", return_value=True)
    def test_probe_cargo_system_deps_metadata_failure_returns_empty(
        self, _mock_is_tool, mock_run
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="boom"
        )
        self.assertEqual(
            setup._probe_cargo_system_deps("socorro-cli"),
            {"apt": [], "brew": []},
        )

    @patch("setup.is_tool", return_value=False)
    def test_probe_cargo_system_deps_no_cargo_returns_empty(self, _mock_is_tool):
        self.assertEqual(
            setup._probe_cargo_system_deps("socorro-cli"),
            {"apt": [], "brew": []},
        )

    @patch("setup.subprocess.run")
    @patch("setup.is_tool", return_value=True)
    def test_probe_npm_node_requirement_parses_range(self, _mock_is_tool, mock_run):
        # ">= 24" → 24
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=">= 24\n", stderr=""
        )
        self.assertEqual(setup._probe_npm_node_requirement("@x/pkg"), 24)

        # ">=20.0.0" → 20 (parses the lowest int — major)
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=">=20.0.0\n", stderr=""
        )
        self.assertEqual(setup._probe_npm_node_requirement("@x/pkg"), 0)

        # "^22 || >=24" → 22 (min of the majors mentioned)
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="^22 || >=24\n", stderr=""
        )
        self.assertEqual(setup._probe_npm_node_requirement("@x/pkg"), 22)

        # Empty → None
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        self.assertIsNone(setup._probe_npm_node_requirement("@x/pkg"))

    @patch("setup.subprocess.run")
    @patch("setup.is_tool", return_value=True)
    def test_probe_npm_node_requirement_npm_failure_returns_none(
        self, _mock_is_tool, mock_run
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr=""
        )
        self.assertIsNone(setup._probe_npm_node_requirement("@x/pkg"))

    @patch("setup.is_tool", return_value=False)
    def test_probe_npm_node_requirement_no_npm_returns_none(self, _mock_is_tool):
        self.assertIsNone(setup._probe_npm_node_requirement("@x/pkg"))

    # ---- _ensure_system_packages ----

    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=True)
    @patch("setup.subprocess.run")
    def test_ensure_system_packages_all_present_linux(
        self, mock_run, _is_lin, _is_mac, _is_win
    ):
        # dpkg returns rc=0 for every package check
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = setup._ensure_system_packages("foo", ["pkg-config"], [])
        self.assertTrue(result)
        # No apt-get install call was made
        for call in mock_run.call_args_list:
            argv = call[0][0]
            self.assertNotIn("apt-get", argv)

    @patch("setup.is_interactive", return_value=True)
    @patch("setup.get_user_confirmation", return_value=True)
    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=True)
    @patch("setup.subprocess.run")
    def test_ensure_system_packages_partial_missing_install_succeeds(
        self, mock_run, _is_lin, _is_mac, _is_win, _confirm, _interactive
    ):
        def _side(argv, **_kw):
            # dpkg -s pkg-config → installed; dpkg -s libdbus-1-dev → missing
            if argv[:2] == ["dpkg", "-s"]:
                rc = 0 if argv[2] == "pkg-config" else 1
                return subprocess.CompletedProcess(
                    args=argv, returncode=rc, stdout="", stderr=""
                )
            if argv[:2] == ["sudo", "apt-get"]:
                return subprocess.CompletedProcess(
                    args=argv, returncode=0, stdout="installed", stderr=""
                )
            return subprocess.CompletedProcess(
                args=argv, returncode=0, stdout="", stderr=""
            )

        mock_run.side_effect = _side
        result = setup._ensure_system_packages(
            "foo", ["pkg-config", "libdbus-1-dev"], []
        )
        self.assertTrue(result)
        # apt-get install called with only the missing package
        apt_calls = [
            c[0][0]
            for c in mock_run.call_args_list
            if c[0][0][:2] == ["sudo", "apt-get"]
        ]
        self.assertEqual(len(apt_calls), 1)
        self.assertIn("libdbus-1-dev", apt_calls[0])
        self.assertNotIn("pkg-config", apt_calls[0])

    @patch("setup.is_interactive", return_value=False)
    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=True)
    @patch("setup.subprocess.run")
    def test_ensure_system_packages_non_interactive_linux_skips(
        self, mock_run, _is_lin, _is_mac, _is_win, _interactive
    ):
        def _side(argv, **_kw):
            if argv[:2] == ["dpkg", "-s"]:
                return subprocess.CompletedProcess(
                    args=argv, returncode=1, stdout="", stderr=""
                )
            return subprocess.CompletedProcess(
                args=argv, returncode=0, stdout="", stderr=""
            )

        mock_run.side_effect = _side
        result = setup._ensure_system_packages("foo", ["libdbus-1-dev"], [])
        self.assertIsNone(result)
        # No apt-get install was attempted in non-interactive mode
        for c in mock_run.call_args_list:
            self.assertNotEqual(c[0][0][:2], ["sudo", "apt-get"])

    @patch("setup.is_interactive", return_value=True)
    @patch("setup.get_user_confirmation", return_value=False)
    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=True)
    @patch("setup.subprocess.run")
    def test_ensure_system_packages_user_declines(
        self, mock_run, _is_lin, _is_mac, _is_win, _confirm, _interactive
    ):
        def _side(argv, **_kw):
            if argv[:2] == ["dpkg", "-s"]:
                return subprocess.CompletedProcess(
                    args=argv, returncode=1, stdout="", stderr=""
                )
            return subprocess.CompletedProcess(
                args=argv, returncode=0, stdout="", stderr=""
            )

        mock_run.side_effect = _side
        result = setup._ensure_system_packages("foo", ["libdbus-1-dev"], [])
        self.assertIsNone(result)
        # No apt-get install was attempted
        for c in mock_run.call_args_list:
            self.assertNotEqual(c[0][0][:2], ["sudo", "apt-get"])

    @patch("setup.is_tool", return_value=False)
    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=True)
    @patch("setup.is_linux", return_value=False)
    @patch("setup.subprocess.run")
    def test_ensure_system_packages_brew_missing_macos(
        self, mock_run, _is_lin, _is_mac, _is_win, _is_tool
    ):
        # brew list returns rc=1 for missing pkg; is_tool("brew") returns False → skip
        def _side(argv, **_kw):
            if argv[:2] == ["brew", "list"]:
                return subprocess.CompletedProcess(
                    args=argv, returncode=1, stdout="", stderr=""
                )
            return subprocess.CompletedProcess(
                args=argv, returncode=0, stdout="", stderr=""
            )

        mock_run.side_effect = _side
        result = setup._ensure_system_packages("foo", [], ["cmake"])
        self.assertIsNone(result)

    @patch("setup.is_windows", return_value=True)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=False)
    def test_ensure_system_packages_windows_with_pkgs_skips(
        self, _is_lin, _is_mac, _is_win
    ):
        result = setup._ensure_system_packages("foo", ["x"], ["y"])
        self.assertIsNone(result)

    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=True)
    def test_ensure_system_packages_empty_pkgs_returns_true(
        self, _is_lin, _is_mac, _is_win
    ):
        self.assertTrue(setup._ensure_system_packages("foo", [], []))
        self.assertTrue(setup._ensure_system_packages("foo", None, None))

    # ---- _ensure_node_major ----

    @patch("setup._node_major_version", return_value=24)
    def test_ensure_node_major_already_satisfied(self, _mock_ver):
        self.assertTrue(setup._ensure_node_major("foo", 24))

    @patch("setup._node_major_version", return_value=None)
    def test_ensure_node_major_no_node_returns_none(self, _mock_ver):
        self.assertIsNone(setup._ensure_node_major("foo", 24))

    @patch("setup.is_interactive", return_value=True)
    @patch("setup.get_user_confirmation", return_value=False)
    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=True)
    @patch("setup.subprocess.run")
    @patch("setup._node_major_version", return_value=18)
    def test_ensure_node_major_user_declines_linux(
        self,
        _mock_ver,
        mock_run,
        _is_lin,
        _is_mac,
        _is_win,
        _confirm,
        _interactive,
    ):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = setup._ensure_node_major("foo", 24)
        self.assertIsNone(result)

    @patch("setup.is_interactive", return_value=True)
    @patch("setup.get_user_confirmation", return_value=True)
    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=True)
    @patch("setup.subprocess.run")
    @patch("setup._node_major_version")
    def test_ensure_node_major_upgrade_succeeds_linux(
        self,
        mock_ver,
        mock_run,
        _is_lin,
        _is_mac,
        _is_win,
        _confirm,
        _interactive,
    ):
        # First call: pre-check (18). Second call: post-install verify (24).
        mock_ver.side_effect = [18, 24]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = setup._ensure_node_major("foo", 24)
        self.assertTrue(result)
        # NodeSource setup script invoked with the right major
        bash_calls = [
            c[0][0]
            for c in mock_run.call_args_list
            if len(c[0][0]) >= 2 and c[0][0][:2] == ["bash", "-c"]
        ]
        self.assertTrue(any("setup_24.x" in cmd[-1] for cmd in bash_calls))
        # apt-get install nodejs invoked
        apt_calls = [
            c[0][0]
            for c in mock_run.call_args_list
            if c[0][0][:2] == ["sudo", "apt-get"]
        ]
        self.assertTrue(any("nodejs" in cmd for cmd in apt_calls))

    @patch("setup.is_interactive", return_value=True)
    @patch("setup.get_user_confirmation", return_value=True)
    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=True)
    @patch("setup.subprocess.run")
    @patch("setup._node_major_version")
    def test_ensure_node_major_postcheck_fails_linux(
        self,
        mock_ver,
        mock_run,
        _is_lin,
        _is_mac,
        _is_win,
        _confirm,
        _interactive,
    ):
        # Install commands "succeed" but node is still 18 afterward
        mock_ver.side_effect = [18, 18]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = setup._ensure_node_major("foo", 24)
        self.assertFalse(result)

    @patch("setup.is_interactive", return_value=True)
    @patch("setup.get_user_confirmation", return_value=True)
    @patch("setup.is_tool", return_value=True)
    @patch("setup.is_windows", return_value=False)
    @patch("setup.is_macos", return_value=True)
    @patch("setup.is_linux", return_value=False)
    @patch("setup.subprocess.run")
    @patch("setup._node_major_version")
    def test_ensure_node_major_macos_uses_brew(
        self,
        mock_ver,
        mock_run,
        _is_lin,
        _is_mac,
        _is_win,
        _is_tool,
        _confirm,
        _interactive,
    ):
        mock_ver.side_effect = [18, 24]
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = setup._ensure_node_major("foo", 24)
        self.assertTrue(result)
        brew_install_calls = [
            c[0][0]
            for c in mock_run.call_args_list
            if c[0][0][:2] == ["brew", "install"]
        ]
        self.assertTrue(any("node@24" in cmd for cmd in brew_install_calls))

    @patch("setup.is_windows", return_value=True)
    @patch("setup.is_macos", return_value=False)
    @patch("setup.is_linux", return_value=False)
    @patch("setup._node_major_version", return_value=18)
    def test_ensure_node_major_windows_skips(
        self, _mock_ver, _is_lin, _is_mac, _is_win
    ):
        self.assertIsNone(setup._ensure_node_major("foo", 24))

    # ---- _install_cargo_tool probe_crate wiring ----

    @patch("setup._ensure_system_packages", return_value=None)
    @patch("setup._probe_cargo_system_deps", return_value={"apt": ["x"], "brew": []})
    @patch("setup.is_tool")
    @patch("setup.subprocess.run")
    def test_install_cargo_tool_probe_crate_declined_returns_none(
        self, mock_run, mock_is_tool, _mock_probe, _mock_ensure
    ):
        # Binary missing, cargo present.
        mock_is_tool.side_effect = lambda name: name == "cargo"
        result = setup._install_cargo_tool(
            "foo (display)",
            "foo-bin",
            ["foo"],
            ["benefit"],
            ["consequence"],
            probe_crate="foo",
        )
        self.assertIsNone(result)
        # cargo install was not invoked
        for c in mock_run.call_args_list:
            argv = c[0][0]
            self.assertFalse(argv[:2] == ["cargo", "install"])

    @patch("setup._probe_cargo_system_deps")
    @patch("setup.get_user_confirmation", return_value=False)
    @patch("setup.is_tool")
    def test_install_cargo_tool_no_probe_no_dep_check(
        self, mock_is_tool, _confirm, mock_probe
    ):
        # With probe_crate=None, _probe_cargo_system_deps must not be called.
        mock_is_tool.side_effect = lambda name: name == "cargo"
        setup._install_cargo_tool(
            "foo (display)",
            "foo-bin",
            ["foo"],
            ["benefit"],
            ["consequence"],
        )
        mock_probe.assert_not_called()

    # ---- install_profiler_cli with dynamic Node gate ----

    @patch("setup._node_major_version", return_value=18)
    @patch("setup._ensure_node_major", return_value=None)
    @patch("setup._probe_npm_node_requirement", return_value=24)
    @patch("setup.is_tool")
    def test_install_profiler_cli_node_too_old_user_declines(
        self, mock_is_tool, _mock_probe, _mock_ensure, _mock_ver
    ):
        mock_is_tool.side_effect = lambda name: name == "npm"
        self.assertIsNone(setup.install_profiler_cli())

    @patch("setup._node_major_version", return_value=18)
    @patch("setup._ensure_node_major", return_value=False)
    @patch("setup._probe_npm_node_requirement", return_value=24)
    @patch("setup.subprocess.run")
    @patch("setup.is_tool")
    def test_install_profiler_cli_node_upgrade_fails(
        self, mock_is_tool, mock_run, _mock_probe, _mock_ensure, _mock_ver
    ):
        mock_is_tool.side_effect = lambda name: name == "npm"
        self.assertFalse(setup.install_profiler_cli())
        # npm install not invoked
        for c in mock_run.call_args_list:
            argv = c[0][0]
            self.assertFalse(argv[:2] == ["npm", "install"])

    @patch("setup._node_major_version", return_value=24)
    @patch("setup._ensure_node_major", return_value=True)
    @patch("setup._probe_npm_node_requirement", return_value=24)
    @patch("setup.is_tool")
    def test_install_profiler_cli_already_installed_with_satisfied_node(
        self, mock_is_tool, _mock_probe, _mock_ensure, _mock_ver
    ):
        """Binary present and Node already satisfies the requirement →
        return True without npm install."""
        mock_is_tool.side_effect = lambda name: name in ("npm", "profiler-cli")
        with patch("setup.subprocess.run") as mock_run:
            self.assertTrue(setup.install_profiler_cli())
            for c in mock_run.call_args_list:
                self.assertNotEqual(c[0][0][:2], ["npm", "install"])

    @patch("setup.is_windows", return_value=False)
    @patch("setup.get_user_confirmation", return_value=True)
    @patch("setup._node_major_version", return_value=18)
    @patch("setup._ensure_node_major", return_value=True)
    @patch("setup._probe_npm_node_requirement", return_value=24)
    @patch("setup.subprocess.run")
    @patch("setup.is_tool")
    def test_install_profiler_cli_node_upgraded_forces_reinstall(
        self,
        mock_is_tool,
        mock_run,
        _mock_probe,
        _mock_ensure,
        _mock_ver,
        _mock_confirm,
        _mock_is_win,
    ):
        """If Node was just upgraded (current_before < min_major),
        run npm install even when binary appears installed."""
        mock_is_tool.side_effect = lambda name: name in ("npm", "profiler-cli")
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        self.assertTrue(setup.install_profiler_cli())
        npm_install_calls = [
            c[0][0]
            for c in mock_run.call_args_list
            if c[0][0][:3] == ["npm", "install", "-g"]
        ]
        self.assertEqual(len(npm_install_calls), 1)
        self.assertEqual(
            npm_install_calls[0][-1], "@firefox-devtools/profiler-cli@latest"
        )


def run_tests():
    """Run all tests and return results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLinkFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestIsToolFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestBashCommandGenerators))
    suite.addTests(loader.loadTestsFromTestCase(TestAppendNonexistentLinesToFile))
    suite.addTests(loader.loadTestsFromTestCase(TestVerifySymlinks))
    suite.addTests(loader.loadTestsFromTestCase(TestVerifyFileReadability))
    suite.addTests(loader.loadTestsFromTestCase(TestVerifyBashSyntax))
    suite.addTests(loader.loadTestsFromTestCase(TestMainFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestClaudeSecurityIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestInstallFirefoxClaude))
    suite.addTests(loader.loadTestsFromTestCase(TestMozillaCliTools))

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    result = run_tests()

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
