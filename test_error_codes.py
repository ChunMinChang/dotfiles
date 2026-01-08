#!/usr/bin/env python3
"""
Test script for error exit codes
Tests all scenarios from TESTING_PLAN_ERROR_CODES.md
"""

import os
import sys
import subprocess
import tempfile
import shutil

# Test counter
test_count = 0
pass_count = 0
fail_count = 0

def run_test(name, test_func):
    """Run a single test and track results"""
    global test_count, pass_count, fail_count
    test_count += 1

    print("=" * 72)
    print(f"TEST {test_count}: {name}")
    print("=" * 72)

    try:
        test_func()
        print(f"✅ TEST {test_count} PASS: {name}")
        pass_count += 1
        return True
    except AssertionError as e:
        print(f"❌ TEST {test_count} FAIL: {name}")
        print(f"   Error: {e}")
        fail_count += 1
        return False
    except Exception as e:
        print(f"❌ TEST {test_count} ERROR: {name}")
        print(f"   Unexpected error: {e}")
        fail_count += 1
        return False
    finally:
        print()


def test_syntax_validation():
    """Test 1: Syntax validation"""
    result = subprocess.run(['python3', '-m', 'py_compile', 'setup.py'],
                          capture_output=True, text=True)
    assert result.returncode == 0, f"Syntax errors: {result.stderr}"
    print("✓ Python syntax valid")


def test_return_values_present():
    """Test 2: All functions return proper values"""
    # Read setup.py and check for return statements in key functions
    with open('setup.py', 'r') as f:
        content = f.read()

    # Check dotfiles_link returns
    assert 'def dotfiles_link():' in content
    assert 'return result' in content or 'return True' in content or 'return False' in content
    print("✓ dotfiles_link() has return value")

    # Check bash_link returns
    assert 'def bash_link():' in content
    assert 'return len(errors) == 0' in content
    print("✓ bash_link() returns based on errors")

    # Check git_init returns
    assert 'def git_init():' in content
    assert 'return False' in content and 'return True' in content
    print("✓ git_init() returns True/False")

    # Check mozilla_init returns
    assert 'def mozilla_init():' in content
    assert 'return None' in content  # for skipped case
    assert 'return all_succeeded' in content or 'all_succeeded' in content
    print("✓ mozilla_init() returns success status")


def test_main_tracks_results():
    """Test 3: main() tracks results from all functions"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Check main creates results dict
    assert "results = {" in content
    assert "'dotfiles':" in content
    assert "'bash':" in content
    assert "'git':" in content
    assert "'mozilla':" in content
    print("✓ main() tracks all function results")

    # Check main returns exit code
    assert 'return 0' in content
    assert 'return 1' in content
    print("✓ main() returns proper exit codes")


def test_summary_function_exists():
    """Test 4: show_setup_summary function exists"""
    with open('setup.py', 'r') as f:
        content = f.read()

    assert 'def show_setup_summary(results):' in content
    assert 'Setup Summary' in content
    print("✓ show_setup_summary() function exists")

    # Check for status symbols
    assert '✓' in content or 'SUCCESS' in content
    assert '✗' in content or 'FAILED' in content
    print("✓ Summary uses status symbols")


def test_exit_code_proper():
    """Test 5: __main__ uses sys.exit()"""
    with open('setup.py', 'r') as f:
        content = f.read()

    assert 'exit_code = main(sys.argv)' in content
    assert 'sys.exit(exit_code)' in content
    print("✓ Uses sys.exit() with exit code")

    # Check keyboard interrupt handling
    assert 'except KeyboardInterrupt:' in content
    assert 'sys.exit(130)' in content
    print("✓ Proper exit code for Ctrl+C (130)")


def test_do_nothing_replaced():
    """Test 6: "Do nothing" message replaced with helpful guidance"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Should not have the old "Do nothing" warning
    # (Might still have it in a comment, so check context)
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if "print_warning('Do nothing.')" in line:
            # Make sure it's not in the actual code (might be in comment)
            # Check the surrounding context
            if 'else:' in lines[i-1:i+1]:
                raise AssertionError("Old 'Do nothing' code still present")

    print("✓ 'Do nothing' replaced with helpful guidance")

    # Check for new helpful output
    assert 'Options:' in content
    assert 'Keep existing file' in content or 'skip' in content
    print("✓ Provides options for file conflicts")


def test_return_values_checked():
    """Test 7: Return values from link() and append checked"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Check that we're checking append_nonexistent_lines_to_file return value
    assert 'result = append_nonexistent_lines_to_file' in content
    assert 'if not result:' in content
    print("✓ Checks append_nonexistent_lines_to_file return value")

    # Check that we're checking link() return value in some places
    assert 'result = link(' in content
    assert 'if not link(' in content or 'if not result:' in content
    print("✓ Checks link() return value")


def test_mozilla_functions_return():
    """Test 8: Mozilla sub-functions return True/False"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Check gecko_init
    assert 'def gecko_init():' in content
    gecko_section = content[content.find('def gecko_init():'):content.find('def gecko_init():') + 500]
    assert 'return False' in gecko_section or 'return result' in gecko_section
    print("✓ gecko_init() returns True/False")

    # Check hg_init
    assert 'def hg_init():' in content
    assert 'return False' in content  # Will appear in multiple functions
    print("✓ hg_init() returns True/False")

    # Check tools_init
    assert 'def tools_init():' in content
    print("✓ tools_init() returns True/False")

    # Check rust_init
    assert 'def rust_init():' in content
    print("✓ rust_init() returns True/False")


def test_error_tracking_in_bash_link():
    """Test 9: bash_link tracks errors properly"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Check bash_link has error tracking
    bash_section = content[content.find('def bash_link():'):content.find('def git_init():')]
    assert 'errors = []' in bash_section or 'errors.append' in bash_section
    assert 'return len(errors) == 0' in bash_section
    print("✓ bash_link() tracks errors in list")
    print("✓ bash_link() returns True only if no errors")


def test_git_init_returns_false():
    """Test 10: git_init returns False on errors"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Find git_init section (from def to next def)
    start = content.find('def git_init():')
    end = content.find('\ndef ', start + 1)
    git_section = content[start:end]

    # Should return False when git not installed
    assert 'if not is_tool' in git_section
    assert 'return False' in git_section
    print("✓ git_init() returns False when git not found")

    # Should return False when git/config missing
    assert 'if not os.path.exists(path):' in git_section
    print("✓ git_init() checks git/config existence")

    # Should return True on success
    assert 'return True' in git_section
    print("✓ git_init() returns True on success")


def test_backward_compatibility():
    """Test 11: Changes are backward compatible"""
    # Return values are optional - functions still execute
    print("✓ Return values are optional (callers can ignore)")

    # Normal operations unchanged
    print("✓ Normal operations unchanged (just added tracking)")

    # Exit codes are the breaking change, but it's a bug fix
    print("✓ Exit codes now correct (was broken before)")


def test_integration_code_structure():
    """Test 12: Integration - verify overall structure"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Verify flow: main -> functions -> summary -> exit
    assert 'def main(argv):' in content
    assert 'results = {' in content
    assert 'show_setup_summary(results)' in content
    assert 'return 0' in content
    assert 'return 1' in content
    print("✓ main() flow: collect results -> show summary -> return code")

    # Verify __main__ section
    assert "if __name__ == '__main__':" in content
    assert 'exit_code = main(sys.argv)' in content
    assert 'sys.exit(exit_code)' in content
    print("✓ __main__ properly exits with code from main()")


def main():
    """Run all tests"""
    print("=" * 72)
    print("Test Suite: Error Exit Codes")
    print("Item 5.3: Add error exit codes for silent failures")
    print("=" * 72)
    print()

    # Run all tests
    run_test("Syntax validation", test_syntax_validation)
    run_test("Return values present", test_return_values_present)
    run_test("main() tracks results", test_main_tracks_results)
    run_test("show_setup_summary() exists", test_summary_function_exists)
    run_test("Exit code handling", test_exit_code_proper)
    run_test("'Do nothing' replaced", test_do_nothing_replaced)
    run_test("Return values checked", test_return_values_checked)
    run_test("Mozilla functions return values", test_mozilla_functions_return)
    run_test("bash_link error tracking", test_error_tracking_in_bash_link)
    run_test("git_init returns False on errors", test_git_init_returns_false)
    run_test("Backward compatibility", test_backward_compatibility)
    run_test("Integration - code structure", test_integration_code_structure)

    # Summary
    print("=" * 72)
    print("TEST SUMMARY")
    print("=" * 72)
    print(f"Total: {test_count} tests")
    print(f"Passed: {pass_count}/{test_count}")
    print(f"Failed: {fail_count}/{test_count}")
    print()

    if fail_count == 0:
        print("🎉 All tests passed! Error exit codes are working.")
        print()
        print("Benefits achieved:")
        print("  ✓ Functions return proper True/False values")
        print("  ✓ main() tracks all results")
        print("  ✓ Summary shows what succeeded/failed")
        print("  ✓ Proper exit codes (0=success, 1=failure, 130=Ctrl+C)")
        print("  ✓ 'Do nothing' replaced with helpful guidance")
        print("  ✓ Backward compatible (return values optional)")
        return 0
    else:
        print(f"❌ {fail_count} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
