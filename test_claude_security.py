#!/usr/bin/env python3
"""
Test Suite for Claude Code Security Hooks

Tests the security hook system that prevents Claude from reading sensitive files.

Run with: python test_claude_security.py
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
from pathlib import Path

# Test result tracking
TESTS_RUN = 0
TESTS_PASSED = 0
TESTS_FAILED = 0

# Colors for output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    END = '\033[0m'

def print_pass(message):
    """Print a passing test message."""
    global TESTS_PASSED
    TESTS_PASSED += 1
    print(f"  {Colors.GREEN}✓{Colors.END} {message}")

def print_fail(message):
    """Print a failing test message."""
    global TESTS_FAILED
    TESTS_FAILED += 1
    print(f"  {Colors.RED}✗{Colors.END} {message}")

def print_section(title):
    """Print a test section header."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")

# =============================================================================
# Test Suite 1: Hook Script Behavior
# =============================================================================

def test_hook_script_blocks_ssh_keys():
    """Test that hook blocks SSH private keys."""
    print_section("Test Suite 1: Hook Script Behavior")
    global TESTS_RUN

    TESTS_RUN += 1
    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    # Simulate hook input for reading SSH key
    hook_input = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(Path.home() / ".ssh" / "id_rsa")},
        "session_id": "test-session",
        "cwd": str(Path.cwd())
    }

    try:
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.returncode == 2:  # Exit code 2 = blocked
            print_pass("Hook blocks SSH private key (~/.ssh/id_rsa)")
        else:
            print_fail(f"Hook should block SSH key (exit code 2), got: {result.returncode}")
    except Exception as e:
        print_fail(f"Hook execution failed: {e}")

def test_hook_script_blocks_arcrc():
    """Test that hook blocks Mozilla .arcrc (Phabricator tokens)."""
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    hook_input = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(Path.home() / ".arcrc")},
        "session_id": "test-session",
        "cwd": str(Path.cwd())
    }

    try:
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.returncode == 2:
            print_pass("Hook blocks .arcrc (Phabricator API tokens)")
        else:
            print_fail(f"Hook should block .arcrc (exit code 2), got: {result.returncode}")
    except Exception as e:
        print_fail(f"Hook execution failed: {e}")

def test_hook_script_allows_mozbuild():
    """Test that hook allows ~/.mozbuild files (explicitly safe)."""
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    hook_input = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(Path.home() / ".mozbuild" / "machrc")},
        "session_id": "test-session",
        "cwd": str(Path.cwd())
    }

    try:
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print_pass("Hook allows ~/.mozbuild/machrc (safe build directory)")
        else:
            print_fail(f"Hook should allow ~/.mozbuild files (exit code 0), got: {result.returncode}")
    except Exception as e:
        print_fail(f"Hook execution failed: {e}")

def test_hook_script_blocks_env_with_secrets():
    """Test that hook blocks .env files containing API keys."""
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    # Create temporary .env file with secrets
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("DATABASE_URL=postgres://localhost/mydb\n")
        f.write("API_KEY=secret_key_12345\n")
        f.write("DEBUG=true\n")
        temp_env = f.name

    try:
        hook_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": temp_env},
            "session_id": "test-session",
            "cwd": str(Path.cwd())
        }

        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.returncode == 2:
            print_pass("Hook blocks .env with API_KEY")
        else:
            print_fail(f"Hook should block .env with secrets (exit code 2), got: {result.returncode}")
    finally:
        os.unlink(temp_env)

def test_hook_script_allows_env_without_secrets():
    """Test that hook allows .env files without sensitive keywords."""
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    # Create temporary .env file without secrets
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("DEBUG=true\n")
        f.write("LOG_LEVEL=info\n")
        f.write("PORT=3000\n")
        temp_env = f.name

    try:
        hook_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": temp_env},
            "session_id": "test-session",
            "cwd": str(Path.cwd())
        }

        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print_pass("Hook allows .env without sensitive keywords")
        else:
            print_fail(f"Hook should allow safe .env (exit code 0), got: {result.returncode}")
    finally:
        os.unlink(temp_env)

def test_hook_script_blocks_bash_cat_ssh():
    """Test that hook blocks bash commands accessing SSH keys."""
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    hook_input = {
        "tool_name": "Bash",
        "tool_input": {"command": "cat ~/.ssh/id_rsa"},
        "session_id": "test-session",
        "cwd": str(Path.cwd())
    }

    try:
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if result.returncode == 2:
            print_pass("Hook blocks bash command accessing SSH key")
        else:
            print_fail(f"Hook should block bash accessing SSH (exit code 2), got: {result.returncode}")
    except Exception as e:
        print_fail(f"Hook execution failed: {e}")

def test_hook_script_emergency_override():
    """Test that DOTFILES_CLAUDE_SECURITY_DISABLED=true disables hook."""
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    hook_input = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(Path.home() / ".ssh" / "id_rsa")},
        "session_id": "test-session",
        "cwd": str(Path.cwd())
    }

    env = os.environ.copy()
    env['DOTFILES_CLAUDE_SECURITY_DISABLED'] = 'true'

    try:
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode == 0:
            print_pass("Hook respects DOTFILES_CLAUDE_SECURITY_DISABLED=true")
        else:
            print_fail(f"Hook should allow with override (exit code 0), got: {result.returncode}")
    except Exception as e:
        print_fail(f"Hook execution failed: {e}")

def test_hook_script_whitelist():
    """Test that whitelisted paths are allowed."""
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    # Create temp file that would normally be blocked
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write("API_KEY=secret123\n")
        temp_env = f.name

    env = os.environ.copy()
    env['DOTFILES_CLAUDE_SECURITY_WHITELIST'] = temp_env

    try:
        hook_input = {
            "tool_name": "Read",
            "tool_input": {"file_path": temp_env},
            "session_id": "test-session",
            "cwd": str(Path.cwd())
        }

        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode == 0:
            print_pass("Hook respects DOTFILES_CLAUDE_SECURITY_WHITELIST")
        else:
            print_fail(f"Hook should allow whitelisted file (exit code 0), got: {result.returncode}")
    finally:
        os.unlink(temp_env)

# =============================================================================
# Test Suite 2: Logging Functionality
# =============================================================================

def test_logging_creates_log_file():
    """Test that blocked access creates log entries."""
    print_section("Test Suite 2: Logging Functionality")
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'
    log_file = Path.home() / '.dotfiles-claude-hooks' / 'security-blocks.log'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    # Clear log file if exists
    if log_file.exists():
        log_file.unlink()

    # Trigger a block
    hook_input = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(Path.home() / ".ssh" / "id_rsa")},
        "session_id": "test-session-log",
        "cwd": str(Path.cwd())
    }

    try:
        subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if log_file.exists():
            with open(log_file, 'r') as f:
                content = f.read()
                if 'test-session-log' in content and 'id_rsa' in content:
                    print_pass("Hook creates log file with correct entries")
                else:
                    print_fail("Log file missing expected content")
        else:
            print_fail("Hook should create log file on blocked access")
    except Exception as e:
        print_fail(f"Logging test failed: {e}")

def test_logging_prints_to_stderr():
    """Test that blocked access prints visible message to stderr."""
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail("Hook script not found (expected, not yet implemented)")
        return

    hook_input = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(Path.home() / ".ssh" / "id_rsa")},
        "session_id": "test-session",
        "cwd": str(Path.cwd())
    }

    try:
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True
        )

        if '🔒 SECURITY HOOK' in result.stderr and 'id_rsa' in result.stderr:
            print_pass("Hook prints security message to stderr")
        else:
            print_fail("Hook should print security warning to stderr")
    except Exception as e:
        print_fail(f"Stderr test failed: {e}")

# =============================================================================
# Test Suite 3: setup.py Integration
# =============================================================================

def test_setup_claude_security_flag():
    """Test that setup.py accepts --claude-security flag."""
    print_section("Test Suite 3: setup.py Integration")
    global TESTS_RUN
    TESTS_RUN += 1

    try:
        result = subprocess.run(
            [sys.executable, 'setup.py', '--claude-security', '--dry-run'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0 and 'claude' in result.stdout.lower():
            print_pass("setup.py accepts --claude-security flag")
        else:
            print_fail(f"setup.py should accept --claude-security flag: {result.stderr}")
    except Exception as e:
        print_fail(f"Flag test failed: {e}")

def test_setup_dry_run_claude_security():
    """Test that --dry-run shows what would be done."""
    global TESTS_RUN
    TESTS_RUN += 1

    try:
        result = subprocess.run(
            [sys.executable, 'setup.py', '--claude-security', '--dry-run'],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout + result.stderr
        if 'DRY RUN' in output and 'security' in output.lower():
            print_pass("--dry-run shows Claude security installation plan")
        else:
            print_fail("--dry-run should show installation plan")
    except Exception as e:
        print_fail(f"Dry-run test failed: {e}")

def test_setup_all_includes_claude_security():
    """Test that --all flag includes Claude security."""
    global TESTS_RUN
    TESTS_RUN += 1

    try:
        result = subprocess.run(
            [sys.executable, 'setup.py', '--all', '--dry-run'],
            capture_output=True,
            text=True,
            timeout=10
        )

        output = result.stdout + result.stderr
        if 'security' in output.lower() or 'claude' in output.lower():
            print_pass("--all flag includes Claude security")
        else:
            print_fail("--all should include Claude security installation")
    except Exception as e:
        print_fail(f"--all flag test failed: {e}")

def test_setup_remove_claude_security():
    """Test that --remove-claude-security flag exists."""
    global TESTS_RUN
    TESTS_RUN += 1

    try:
        result = subprocess.run(
            [sys.executable, 'setup.py', '--remove-claude-security', '--dry-run'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should either succeed or show it's not installed
        if result.returncode == 0:
            print_pass("setup.py accepts --remove-claude-security flag")
        else:
            print_fail(f"setup.py should accept --remove-claude-security: {result.stderr}")
    except Exception as e:
        print_fail(f"Remove flag test failed: {e}")

def test_setup_show_claude_hooks():
    """Test that --show-claude-hooks displays current hooks."""
    global TESTS_RUN
    TESTS_RUN += 1

    try:
        result = subprocess.run(
            [sys.executable, 'setup.py', '--show-claude-hooks'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print_pass("setup.py accepts --show-claude-hooks flag")
        else:
            print_fail(f"setup.py should accept --show-claude-hooks: {result.stderr}")
    except Exception as e:
        print_fail(f"Show hooks test failed: {e}")

def test_setup_show_security_log():
    """Test that --show-claude-security-log displays log."""
    global TESTS_RUN
    TESTS_RUN += 1

    try:
        result = subprocess.run(
            [sys.executable, 'setup.py', '--show-claude-security-log'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print_pass("setup.py accepts --show-claude-security-log flag")
        else:
            print_fail(f"setup.py should accept --show-claude-security-log: {result.stderr}")
    except Exception as e:
        print_fail(f"Show log test failed: {e}")

# =============================================================================
# Test Suite 4: Hook Installation and Merging
# =============================================================================

def test_hook_installation_creates_files():
    """Test that installation creates necessary files."""
    print_section("Test Suite 4: Hook Installation and Merging")
    global TESTS_RUN
    TESTS_RUN += 1

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if hook_script.exists():
        print_pass("Hook script exists at ~/.dotfiles-claude-hooks/security-read-blocker.py")
    else:
        print_fail("Hook script not found (expected, not yet implemented)")

def test_hook_installation_backs_up_config():
    """Test that installation backs up ~/.claude.json."""
    global TESTS_RUN
    TESTS_RUN += 1

    backup_file = Path.home() / '.claude.json.backup-claude-security'

    if backup_file.exists():
        print_pass("Installation creates backup: ~/.claude.json.backup-claude-security")
    else:
        print_fail("Installation should create config backup (not yet installed)")

def test_hook_merges_with_existing_hooks():
    """Test that installation merges with existing hooks (non-destructive)."""
    global TESTS_RUN
    TESTS_RUN += 1

    config_file = Path.home() / '.claude.json'

    if not config_file.exists():
        print_fail("~/.claude.json not found (skipping merge test)")
        return

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Check if security hook exists
        if 'hooks' in config and 'PreToolUse' in config['hooks']:
            security_hook_found = False
            for entry in config['hooks']['PreToolUse']:
                hooks = entry.get('hooks', [])
                for hook in hooks:
                    if 'security-read-blocker.py' in hook.get('command', ''):
                        security_hook_found = True
                        break

            if security_hook_found:
                print_pass("Security hook properly merged into ~/.claude.json")
            else:
                print_fail("Security hook not found in ~/.claude.json (not yet installed)")
        else:
            print_fail("No hooks section in ~/.claude.json (not yet installed)")
    except Exception as e:
        print_fail(f"Config merge test failed: {e}")

# =============================================================================
# Test Suite 5: Uninstallation
# =============================================================================

def test_uninstall_removes_only_security_hooks():
    """Test that uninstall removes only security hooks (surgical removal)."""
    print_section("Test Suite 5: Uninstallation")
    global TESTS_RUN
    TESTS_RUN += 1

    # This test will be manual verification
    # We can't destructively test without actual installation
    print_fail("Uninstall test requires manual verification (not yet implemented)")

# =============================================================================
# Test Suite 6: Cross-Platform Compatibility
# =============================================================================

def test_hook_script_runs_on_current_platform():
    """Test that hook script runs on current platform."""
    print_section("Test Suite 6: Cross-Platform Compatibility")
    global TESTS_RUN
    TESTS_RUN += 1

    import platform
    system = platform.system()

    hook_script = Path.home() / '.dotfiles-claude-hooks' / 'security-read-blocker.py'

    if not hook_script.exists():
        print_fail(f"Hook script not found on {system} (expected, not yet implemented)")
        return

    # Just test that it runs
    hook_input = {"tool_name": "Read", "tool_input": {"file_path": "/tmp/test"}}

    try:
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(hook_input),
            capture_output=True,
            text=True,
            timeout=5
        )

        # Any exit code is fine, just shouldn't crash
        if result.returncode in [0, 2]:
            print_pass(f"Hook script runs successfully on {system}")
        else:
            print_fail(f"Hook script failed on {system}: {result.stderr}")
    except Exception as e:
        print_fail(f"Hook script crashed on {system}: {e}")

# =============================================================================
# Test Suite 7: Documentation
# =============================================================================

def test_claude_security_documentation_exists():
    """Test that CLAUDE_SECURITY.md documentation exists."""
    print_section("Test Suite 7: Documentation")
    global TESTS_RUN
    TESTS_RUN += 1

    doc_file = Path('CLAUDE_SECURITY.md')

    if doc_file.exists():
        print_pass("CLAUDE_SECURITY.md documentation exists")
    else:
        print_fail("CLAUDE_SECURITY.md not found (not yet created)")

def test_readme_mentions_claude_security():
    """Test that README.md mentions Claude security hooks."""
    global TESTS_RUN
    TESTS_RUN += 1

    readme = Path('README.md')

    if readme.exists():
        content = readme.read_text()
        if 'claude' in content.lower() and 'security' in content.lower():
            print_pass("README.md mentions Claude security hooks")
        else:
            print_fail("README.md should mention Claude security (not yet updated)")
    else:
        print_fail("README.md not found")

# =============================================================================
# Main Test Runner
# =============================================================================

def main():
    """Run all tests and display summary."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Claude Code Security Hooks - Test Suite{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")

    # Test Suite 1: Hook Script Behavior
    test_hook_script_blocks_ssh_keys()
    test_hook_script_blocks_arcrc()
    test_hook_script_allows_mozbuild()
    test_hook_script_blocks_env_with_secrets()
    test_hook_script_allows_env_without_secrets()
    test_hook_script_blocks_bash_cat_ssh()
    test_hook_script_emergency_override()
    test_hook_script_whitelist()

    # Test Suite 2: Logging
    test_logging_creates_log_file()
    test_logging_prints_to_stderr()

    # Test Suite 3: setup.py Integration
    test_setup_claude_security_flag()
    test_setup_dry_run_claude_security()
    test_setup_all_includes_claude_security()
    test_setup_remove_claude_security()
    test_setup_show_claude_hooks()
    test_setup_show_security_log()

    # Test Suite 4: Installation
    test_hook_installation_creates_files()
    test_hook_installation_backs_up_config()
    test_hook_merges_with_existing_hooks()

    # Test Suite 5: Uninstallation
    test_uninstall_removes_only_security_hooks()

    # Test Suite 6: Cross-Platform
    test_hook_script_runs_on_current_platform()

    # Test Suite 7: Documentation
    test_claude_security_documentation_exists()
    test_readme_mentions_claude_security()

    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}Test Summary{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"Tests run:    {TESTS_RUN}")
    print(f"Tests passed: {Colors.GREEN}{TESTS_PASSED}{Colors.END}")
    print(f"Tests failed: {Colors.RED}{TESTS_FAILED}{Colors.END}")

    if TESTS_FAILED == 0:
        print(f"\n{Colors.GREEN}✓ All tests passed!{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}✗ Some tests failed{Colors.END}\n")
        print(f"{Colors.YELLOW}Expected: Most tests will fail until implementation is complete{Colors.END}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
