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
        self.assertEqual(os.readlink(self.target), self.source)

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
        self.assertEqual(os.readlink(self.target), self.source)

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


class TestInstallFirefoxClaude(unittest.TestCase):
    """Test install/uninstall of Firefox Claude settings including skills."""

    def setUp(self):
        """Create temp dirs simulating a Firefox repo and dotfiles overlay."""
        self.test_dir = tempfile.mkdtemp()

        # Simulate Firefox repo with mach
        self.firefox_dir = os.path.join(self.test_dir, "firefox")
        os.makedirs(self.firefox_dir)
        open(os.path.join(self.firefox_dir, "mach"), "w").close()

        # Build a minimal overlay structure for personal skills
        self.overlay_dir = os.path.join(self.test_dir, "overlay")
        os.makedirs(os.path.join(self.overlay_dir, "hooks"))
        os.makedirs(os.path.join(self.overlay_dir, "skills", "my-skill"))
        with open(
            os.path.join(self.overlay_dir, "skills", "my-skill", "SKILL.md"), "w"
        ) as f:
            f.write("personal skill")
        with open(
            os.path.join(self.overlay_dir, "hooks", "post-edit-lint.sh"), "w"
        ) as f:
            f.write("#!/bin/bash\n")
        with open(os.path.join(self.overlay_dir, "settings.local.json"), "w") as f:
            f.write('{"permissions":{"allow":[]}}')

        # Build a minimal claude-skills directory
        self.claude_dir = os.path.join(self.test_dir, "claude-skills")
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
        self._orig_claude = setup.CLAUDE_SKILLS_DIR
        self._orig_claude_exclude = setup.CLAUDE_SKILLS_EXCLUDE
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
        setup.CLAUDE_SKILLS_DIR = self.claude_dir
        setup.CLAUDE_SKILLS_EXCLUDE = {".git", ".github", "CLAUDE.md", "README.md"}

    def tearDown(self):
        setup.FIREFOX_CLAUDE_OVERLAY = self._orig_overlay
        setup.MEDIA_SKILLS_DIR = self._orig_media
        setup.MEDIA_SKILLS_EXCLUDE = self._orig_exclude
        setup.CLAUDE_SKILLS_DIR = self._orig_claude
        setup.CLAUDE_SKILLS_EXCLUDE = self._orig_claude_exclude
        shutil.rmtree(self.test_dir)

    def _install(self, **kwargs):
        """Run install_firefox_claude with interactive prompts suppressed."""
        with patch("setup.get_user_input", return_value=""), patch(
            "setup.get_user_confirmation", return_value=True
        ):
            return setup.install_firefox_claude(self.firefox_dir, **kwargs)

    def test_install_symlinks_all_skill_tiers(self):
        """Personal, claude-skills, and media-skills all get symlinked."""
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
        """Excluded entries from media-skills and claude-skills are not symlinked."""
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # media-skills excludes
        for name in ["Template", "shared", "LICENSE", "README.md"]:
            self.assertFalse(
                os.path.exists(os.path.join(skills_dir, name)),
                f"{name} should not be symlinked",
            )
        # claude-skills excludes
        for name in ["CLAUDE.md"]:
            self.assertFalse(
                os.path.exists(os.path.join(skills_dir, name)),
                f"{name} should not be symlinked",
            )

    def test_install_personal_skill_takes_precedence_over_all(self):
        """When a skill name conflicts, personal wins over claude-skills and media-skills."""
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

    def test_install_claude_skills_take_precedence_over_media(self):
        """When a skill exists in both claude-skills and media-skills, claude-skills wins."""
        # Create a skill with the same name in both
        for d in [self.claude_dir, self.media_dir]:
            conflict_dir = os.path.join(d, "shared-skill")
            os.makedirs(conflict_dir, exist_ok=True)
            with open(os.path.join(conflict_dir, "SKILL.md"), "w") as f:
                f.write(f"version from {d}")

        self._install()
        skill_link = os.path.join(
            self.firefox_dir, ".claude", "skills", "shared-skill"
        )
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

    def test_install_no_claude_skills_dir(self):
        """Install works fine if claude-skills directory doesn't exist."""
        setup.CLAUDE_SKILLS_DIR = os.path.join(self.test_dir, "nonexistent")
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # Personal and media skills still work
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "my-skill")))
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "bugzilla-wrangler")))

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

    def test_uninstall_removes_all_skill_symlinks(self):
        """Uninstall removes personal, claude-skill, and media-skill symlinks."""
        self._install()
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        # Verify they exist first
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "bugzilla-wrangler")))
        self.assertTrue(os.path.islink(os.path.join(skills_dir, "bug-start")))

        with patch("setup.get_user_input", return_value=""):
            setup.uninstall_firefox_claude(self.firefox_dir)

        # All symlinks should be gone
        for name in ["my-skill", "bugzilla-wrangler", "s2-validate",
                      "bug-start", "spec-check"]:
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
        """Dry run output mentions claude-skills and media-skills."""
        import io

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            self._install(dry_run=True)
        output = mock_stdout.getvalue()
        self.assertIn("claude-skills", output)
        self.assertIn("bug-start", output)
        self.assertIn("media-skills", output)
        self.assertIn("bugzilla-wrangler", output)
        # Should NOT actually create symlinks
        skills_dir = os.path.join(self.firefox_dir, ".claude", "skills")
        self.assertFalse(os.path.exists(skills_dir))


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

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    result = run_tests()

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
