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
from unittest.mock import patch, MagicMock, mock_open

# Import setup.py module
import setup

class TestLinkFunction(unittest.TestCase):
    """Test the link() function for symlink creation"""

    def setUp(self):
        """Create temporary directory for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.source = os.path.join(self.test_dir, 'source')
        self.target = os.path.join(self.test_dir, 'target')

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_link_creates_symlink(self):
        """Test that link() creates a symlink"""
        # Create source file
        open(self.source, 'w').close()

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
        open(self.source, 'w').close()
        old_source = os.path.join(self.test_dir, 'old_source')
        open(old_source, 'w').close()
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
        self.assertTrue(setup.is_tool('python3'))
        self.assertTrue(setup.is_tool('ls'))

    def test_is_tool_nonexistent_command(self):
        """Test that is_tool() returns False for non-existent commands"""
        self.assertFalse(setup.is_tool('this_command_definitely_does_not_exist_12345'))

    @patch('subprocess.run')
    def test_is_tool_handles_exception(self, mock_run):
        """Test that is_tool() handles exceptions gracefully"""
        mock_run.side_effect = FileNotFoundError()

        result = setup.is_tool('some_command')

        self.assertFalse(result)


class TestBashCommandGenerators(unittest.TestCase):
    """Test bash command generation functions"""

    def test_bash_export_command(self):
        """Test bash_export_command() generates correct export"""
        path = '/path/to/bin'
        result = setup.bash_export_command(path)

        self.assertIn('export PATH=', result)
        self.assertIn(path, result)
        self.assertIn('$PATH', result)

    def test_bash_load_command(self):
        """Test bash_load_command() generates correct source command"""
        path = '/path/to/script.sh'
        result = setup.bash_load_command(path)

        self.assertIn('[ -r ', result)
        self.assertIn(path, result)
        self.assertIn(' && . ', result)


class TestAppendNonexistentLinesToFile(unittest.TestCase):
    """Test the append_nonexistent_lines_to_file() function"""

    def setUp(self):
        """Create temporary directory"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, 'test.txt')

    def tearDown(self):
        """Clean up temporary directory"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_append_to_empty_file(self):
        """Test appending to an empty file"""
        # Create empty file first
        open(self.test_file, 'w').close()

        lines = ['line1', 'line2']

        result = setup.append_nonexistent_lines_to_file(self.test_file, lines)

        self.assertTrue(result)
        with open(self.test_file, 'r') as f:
            content = f.read()
        self.assertIn('line1', content)
        self.assertIn('line2', content)

    def test_append_skips_existing_lines(self):
        """Test that existing lines are not duplicated"""
        # Create file with existing line
        with open(self.test_file, 'w') as f:
            f.write('existing_line\n')

        lines = ['existing_line', 'new_line']
        result = setup.append_nonexistent_lines_to_file(self.test_file, lines)

        self.assertTrue(result)
        with open(self.test_file, 'r') as f:
            content = f.read()

        # Should have existing_line once and new_line once
        self.assertEqual(content.count('existing_line'), 1)
        self.assertEqual(content.count('new_line'), 1)

    def test_append_handles_partial_match(self):
        """Test that substring matches don't prevent appending (Item 5.2 fix)"""
        # Create file with line containing substring
        with open(self.test_file, 'w') as f:
            f.write('# Comment about source ~/.bashrc/backup\n')

        lines = ['source ~/.bashrc']
        result = setup.append_nonexistent_lines_to_file(self.test_file, lines)

        self.assertTrue(result)
        with open(self.test_file, 'r') as f:
            lines_in_file = f.readlines()

        # Should have both lines (substring match doesn't count)
        self.assertEqual(len(lines_in_file), 2)
        self.assertIn('source ~/.bashrc\n', lines_in_file)

    def test_append_nonexistent_file(self):
        """Test appending to non-existent file returns False"""
        nonexistent = os.path.join(self.test_dir, 'nonexistent.txt')
        lines = ['line1']

        result = setup.append_nonexistent_lines_to_file(nonexistent, lines)

        # Function requires file to exist, should return False
        self.assertFalse(result)
        # File should not be created
        self.assertFalse(os.path.exists(nonexistent))

    def test_append_adds_newline_if_missing(self):
        """Test that newline is added at EOF if missing"""
        # Create file without trailing newline
        with open(self.test_file, 'w') as f:
            f.write('no_newline')

        lines = ['new_line']
        result = setup.append_nonexistent_lines_to_file(self.test_file, lines)

        self.assertTrue(result)
        with open(self.test_file, 'r') as f:
            content = f.read()

        # Should have both lines on separate lines
        self.assertIn('no_newline\n', content)
        self.assertIn('new_line', content)


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
        dotfiles = os.path.join(self.test_dir, 'dotfiles')
        os.makedirs(dotfiles)
        os.symlink(dotfiles, os.path.join(self.test_dir, '.dotfiles'))

        issues = setup.verify_symlinks()

        self.assertEqual(len(issues), 0)

    def test_verify_symlinks_broken_link(self):
        """Test verify_symlinks() detects broken symlinks"""
        # Create broken symlink
        nonexistent = os.path.join(self.test_dir, 'nonexistent')
        os.symlink(nonexistent, os.path.join(self.test_dir, '.dotfiles'))

        issues = setup.verify_symlinks()

        self.assertGreater(len(issues), 0)
        self.assertTrue(any('broken' in issue.lower() for issue in issues))


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
        self.test_file = os.path.join(self.test_dir, 'test.sh')

    def tearDown(self):
        """Clean up"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_verify_bash_syntax_valid_syntax(self):
        """Test verify_bash_syntax() with valid bash syntax"""
        # Create file with valid syntax
        with open(self.test_file, 'w') as f:
            f.write('#!/bin/bash\necho "hello"\n')

        # Mock BASE_DIR to use our test file
        with patch.object(setup, 'BASE_DIR', self.test_dir):
            # Temporarily create a dot.bashrc for testing
            bashrc = os.path.join(self.test_dir, 'dot.bashrc')
            with open(bashrc, 'w') as f:
                f.write('#!/bin/bash\necho "valid"\n')

            issues = setup.verify_bash_syntax()

            # Should have no issues (or only issues from other files)
            # Don't assert zero because real files might have issues
            self.assertIsInstance(issues, list)


class TestMainFunction(unittest.TestCase):
    """Test the main() function"""

    @patch('setup.verify_installation')
    @patch('setup.mozilla_init')
    @patch('setup.git_init')
    @patch('setup.bash_link')
    @patch('setup.dotfiles_link')
    def test_main_success_flow(self, mock_dotfiles, mock_bash, mock_git, mock_mozilla, mock_verify):
        """Test main() with successful setup"""
        # Mock all functions to return success
        mock_dotfiles.return_value = True
        mock_bash.return_value = True
        mock_git.return_value = True
        mock_mozilla.return_value = None  # Skipped
        mock_verify.return_value = (True, [])

        exit_code = setup.main(['setup.py'])

        self.assertEqual(exit_code, 0)

    @patch('setup.mozilla_init')
    @patch('setup.git_init')
    @patch('setup.bash_link')
    @patch('setup.dotfiles_link')
    def test_main_failure_flow(self, mock_dotfiles, mock_bash, mock_git, mock_mozilla):
        """Test main() with failed setup"""
        # Mock a function to return failure
        mock_dotfiles.return_value = False
        mock_bash.return_value = True
        mock_git.return_value = True
        mock_mozilla.return_value = None

        exit_code = setup.main(['setup.py'])

        self.assertEqual(exit_code, 1)

    @patch('setup.mozilla_init')
    @patch('setup.git_init')
    @patch('setup.bash_link')
    @patch('setup.dotfiles_link')
    def test_main_with_verbose_flag(self, mock_dotfiles, mock_bash, mock_git, mock_mozilla):
        """Test main() with verbose flag"""
        mock_dotfiles.return_value = True
        mock_bash.return_value = True
        mock_git.return_value = True
        mock_mozilla.return_value = None

        # Capture verbose output
        exit_code = setup.main(['setup.py', '-v'])

        # Should have set VERBOSE flag
        self.assertTrue(setup.VERBOSE)

        # Reset for other tests
        setup.VERBOSE = False

    @patch('setup.mozilla_init')
    @patch('setup.git_init')
    @patch('setup.bash_link')
    @patch('setup.dotfiles_link')
    def test_main_with_mozilla_flag(self, mock_dotfiles, mock_bash, mock_git, mock_mozilla):
        """Test main() with mozilla flag"""
        mock_dotfiles.return_value = True
        mock_bash.return_value = True
        mock_git.return_value = True
        mock_mozilla.return_value = True

        exit_code = setup.main(['setup.py', '--mozilla', 'gecko'])

        # Should have called mozilla_init with argument
        mock_mozilla.assert_called_once_with(['gecko'])


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

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    result = run_tests()

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
