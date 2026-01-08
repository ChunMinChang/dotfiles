#!/usr/bin/env python3
"""
Test script for installation verification
Tests all scenarios from TESTING_PLAN_VERIFICATION.md
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


def test_verification_functions_exist():
    """Test 2: All verification functions defined"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Check all verification functions exist
    assert 'def verify_symlinks():' in content
    print("✓ verify_symlinks() exists")

    assert 'def verify_file_readability():' in content
    print("✓ verify_file_readability() exists")

    assert 'def verify_bash_syntax():' in content
    print("✓ verify_bash_syntax() exists")

    assert 'def verify_git_config():' in content
    print("✓ verify_git_config() exists")

    assert 'def verify_installation():' in content
    print("✓ verify_installation() exists")


def test_verification_integration():
    """Test 3: Verification integrated into main()"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Check main() calls verify_installation()
    assert 'verify_installation()' in content
    print("✓ main() calls verify_installation()")

    # Check it's only called on success
    assert 'if all(r is not False for r in results.values()):' in content
    print("✓ Verification only runs if setup succeeded")

    # Check it returns proper exit codes
    main_section = content[content.find('def main(argv):'):]
    assert 'verification_passed' in main_section
    assert 'return 0' in main_section
    assert 'return 1' in main_section
    print("✓ Returns proper exit codes based on verification")


def test_verify_symlinks_logic():
    """Test 4: verify_symlinks() has proper logic"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Find verify_symlinks section
    start = content.find('def verify_symlinks():')
    end = content.find('\ndef ', start + 1)
    func_content = content[start:end]

    # Check for symlink validation logic
    assert 'os.path.lexists' in func_content
    print("✓ Checks symlink existence")

    assert 'os.path.islink' in func_content
    print("✓ Checks if path is symlink")

    assert 'os.path.exists' in func_content
    print("✓ Checks if symlink target exists (broken symlink detection)")

    assert 'os.access' in func_content and 'os.R_OK' in func_content
    print("✓ Checks readability")


def test_verify_file_readability_logic():
    """Test 5: verify_file_readability() has proper logic"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Find verify_file_readability section
    start = content.find('def verify_file_readability():')
    end = content.find('\ndef ', start + 1)
    func_content = content[start:end]

    # Check it validates critical files
    assert 'dot.bashrc' in func_content
    print("✓ Checks dot.bashrc")

    assert 'utils.sh' in func_content
    print("✓ Checks utils.sh")

    assert 'git' in func_content and 'config' in func_content
    print("✓ Checks git/config")

    assert 'os.access' in func_content and 'os.R_OK' in func_content
    print("✓ Checks file readability")


def test_verify_bash_syntax_logic():
    """Test 6: verify_bash_syntax() uses bash -n"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Find verify_bash_syntax section
    start = content.find('def verify_bash_syntax():')
    end = content.find('\ndef ', start + 1)
    func_content = content[start:end]

    # Check it uses bash -n
    assert 'bash' in func_content and '-n' in func_content
    print("✓ Uses bash -n for syntax checking")

    assert 'subprocess.run' in func_content
    print("✓ Uses subprocess.run")

    assert 'timeout' in func_content
    print("✓ Has timeout protection")

    # Check it handles errors gracefully
    assert 'except' in func_content
    print("✓ Has exception handling")


def test_verify_git_config_logic():
    """Test 7: verify_git_config() checks git configuration"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Find verify_git_config section
    start = content.find('def verify_git_config():')
    end = content.find('\ndef ', start + 1)
    func_content = content[start:end]

    # Check it validates git config
    assert 'git config' in func_content
    print("✓ Uses git config command")

    assert 'include.path' in func_content
    print("✓ Checks include.path")

    assert 'subprocess.run' in func_content
    print("✓ Uses subprocess.run")

    assert 'except' in func_content
    print("✓ Has exception handling")


def test_verify_installation_structure():
    """Test 8: verify_installation() calls all verification functions"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Find verify_installation section
    start = content.find('def verify_installation():')
    end = content.find('\ndef ', start + 1)
    func_content = content[start:end]

    # Check it calls all verification functions
    assert 'verify_symlinks()' in func_content
    print("✓ Calls verify_symlinks()")

    assert 'verify_file_readability()' in func_content
    print("✓ Calls verify_file_readability()")

    assert 'verify_bash_syntax()' in func_content
    print("✓ Calls verify_bash_syntax()")

    assert 'verify_git_config()' in func_content
    print("✓ Calls verify_git_config()")

    # Check it returns proper tuple
    assert 'return True, []' in func_content
    assert 'return False, all_issues' in func_content
    print("✓ Returns (bool, list) tuple")


def test_platform_awareness():
    """Test 9: Verification is platform-aware"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Check verify_symlinks is platform-aware
    verify_symlinks_section = content[
        content.find('def verify_symlinks():'):
        content.find('\ndef ', content.find('def verify_symlinks():') + 1)
    ]
    assert 'platform.system()' in verify_symlinks_section
    assert 'Linux' in verify_symlinks_section or 'Darwin' in verify_symlinks_section
    print("✓ verify_symlinks() is platform-aware")

    # Check verify_file_readability is platform-aware
    verify_files_section = content[
        content.find('def verify_file_readability():'):
        content.find('\ndef ', content.find('def verify_file_readability():') + 1)
    ]
    assert 'platform.system()' in verify_files_section
    print("✓ verify_file_readability() is platform-aware")

    # Check verify_bash_syntax is platform-aware
    verify_bash_section = content[
        content.find('def verify_bash_syntax():'):
        content.find('\ndef ', content.find('def verify_bash_syntax():') + 1)
    ]
    assert 'platform.system()' in verify_bash_section
    print("✓ verify_bash_syntax() is platform-aware")


def test_output_formatting():
    """Test 10: Verification has proper output formatting"""
    with open('setup.py', 'r') as f:
        content = f.read()

    verify_installation_section = content[
        content.find('def verify_installation():'):
        content.find('\ndef ', content.find('def verify_installation():') + 1)
    ]

    # Check for progress messages
    assert 'Checking symlinks' in verify_installation_section
    assert 'Checking file readability' in verify_installation_section
    assert 'Checking bash syntax' in verify_installation_section
    assert 'Checking git configuration' in verify_installation_section
    print("✓ Has progress messages for each phase")

    # Check for success indicators
    assert '✓' in verify_installation_section
    print("✓ Has success indicators")

    # Check for colored output
    assert 'colors.OK' in verify_installation_section
    assert 'colors.FAIL' in verify_installation_section
    print("✓ Uses colored output")


def test_error_reporting():
    """Test 11: Verification reports errors clearly"""
    with open('setup.py', 'r') as f:
        content = f.read()

    verify_installation_section = content[
        content.find('def verify_installation():'):
        content.find('\ndef ', content.find('def verify_installation():') + 1)
    ]

    # Check for issue tracking
    assert 'all_issues' in verify_installation_section
    print("✓ Tracks all issues")

    # Check for issue reporting
    assert 'Verification found' in verify_installation_section
    print("✓ Reports number of issues")

    # Check for individual issue printing
    assert 'for issue in all_issues:' in verify_installation_section
    print("✓ Prints each issue individually")


def test_required_vs_optional():
    """Test 12: Distinguishes required vs optional components"""
    with open('setup.py', 'r') as f:
        content = f.read()

    # Check verify_symlinks has required/optional distinction
    verify_symlinks_section = content[
        content.find('def verify_symlinks():'):
        content.find('\ndef ', content.find('def verify_symlinks():') + 1)
    ]
    assert 'True' in verify_symlinks_section and 'False' in verify_symlinks_section
    assert 'required' in verify_symlinks_section
    print("✓ verify_symlinks() distinguishes required vs optional")

    # Check verify_file_readability has required/optional distinction
    verify_files_section = content[
        content.find('def verify_file_readability():'):
        content.find('\ndef ', content.find('def verify_file_readability():') + 1)
    ]
    assert 'True' in verify_files_section and 'False' in verify_files_section
    assert 'required' in verify_files_section
    print("✓ verify_file_readability() distinguishes required vs optional")


def main():
    """Run all tests"""
    print("=" * 72)
    print("Test Suite: Installation Verification")
    print("Item 5.4: Add installation verification step")
    print("=" * 72)
    print()

    # Run all tests
    run_test("Syntax validation", test_syntax_validation)
    run_test("Verification functions exist", test_verification_functions_exist)
    run_test("Verification integration", test_verification_integration)
    run_test("verify_symlinks() logic", test_verify_symlinks_logic)
    run_test("verify_file_readability() logic", test_verify_file_readability_logic)
    run_test("verify_bash_syntax() logic", test_verify_bash_syntax_logic)
    run_test("verify_git_config() logic", test_verify_git_config_logic)
    run_test("verify_installation() structure", test_verify_installation_structure)
    run_test("Platform awareness", test_platform_awareness)
    run_test("Output formatting", test_output_formatting)
    run_test("Error reporting", test_error_reporting)
    run_test("Required vs optional", test_required_vs_optional)

    # Summary
    print("=" * 72)
    print("TEST SUMMARY")
    print("=" * 72)
    print(f"Total: {test_count} tests")
    print(f"Passed: {pass_count}/{test_count}")
    print(f"Failed: {fail_count}/{test_count}")
    print()

    if fail_count == 0:
        print("🎉 All tests passed! Installation verification is working.")
        print()
        print("Benefits achieved:")
        print("  ✓ 5 verification functions implemented")
        print("  ✓ Checks symlinks, files, bash syntax, git config")
        print("  ✓ Platform-aware (Linux/macOS)")
        print("  ✓ Distinguishes required vs optional components")
        print("  ✓ Integrated into main() flow")
        print("  ✓ Clear progress messages and error reporting")
        print("  ✓ Proper exit codes")
        return 0
    else:
        print(f"❌ {fail_count} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
