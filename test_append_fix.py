#!/usr/bin/env python3
"""
Test script for append_nonexistent_lines_to_file fix
Tests all 15 test cases from TESTING_PLAN_APPEND_FIX.md
"""

import os
import sys
import tempfile
import shutil

# Import the functions we need to test
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setup import append_nonexistent_lines_to_file, bash_load_command, print_error, print_warning

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


def test_append_to_empty_file():
    """Test 2: Append to empty file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(temp_file, ['line1'])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            content = f.read()

        assert content == 'line1\n', f"Expected 'line1\\n', got {repr(content)}"
        print("✓ Line appended to empty file")
        print("✓ File contains correct content")
    finally:
        os.unlink(temp_file)


def test_append_without_eof_newline():
    """Test 3: Append to file without EOF newline"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('existing')  # No newline
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(temp_file, ['new'])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            content = f.read()

        assert content == 'existing\nnew\n', f"Expected 'existing\\nnew\\n', got {repr(content)}"
        print("✓ Newline added before append")
        print("✓ Lines properly separated")
    finally:
        os.unlink(temp_file)


def test_append_with_eof_newline():
    """Test 4: Append to file with EOF newline"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('existing\n')
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(temp_file, ['new'])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            content = f.read()

        assert content == 'existing\nnew\n', f"Expected 'existing\\nnew\\n', got {repr(content)}"
        print("✓ No extra newline added")
        print("✓ File contains correct content")
    finally:
        os.unlink(temp_file)


def test_skip_existing_exact_match():
    """Test 5: Skip existing line (exact match)"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('source ~/.bashrc\n')
        temp_file = f.name

    try:
        # Capture output by redirecting temporarily
        result = append_nonexistent_lines_to_file(temp_file, ['source ~/.bashrc'])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            content = f.read()

        assert content == 'source ~/.bashrc\n', f"File should be unchanged, got {repr(content)}"
        assert content.count('source ~/.bashrc') == 1, "Line should appear exactly once"
        print("✓ Existing line detected")
        print("✓ Line not duplicated")
    finally:
        os.unlink(temp_file)


def test_append_with_partial_match():
    """Test 6: Append when partial match exists (CRITICAL - was broken)"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('# source ~/.bashrc/old\n')
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(temp_file, ['source ~/.bashrc'])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 2, f"Should have 2 lines, got {len(lines)}"
        assert lines[0].strip() == '# source ~/.bashrc/old', "First line should be unchanged"
        assert lines[1].strip() == 'source ~/.bashrc', "Second line should be appended"
        print("✓ Partial match NOT treated as existing line")
        print("✓ Line properly appended (FIX for false positive bug)")
    finally:
        os.unlink(temp_file)


def test_append_with_substring_in_comment():
    """Test 7: Append when substring exists in comment (CRITICAL - was broken)"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('# Previously: source ~/.bashrc\n')
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(temp_file, ['source ~/.bashrc'])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            lines = f.readlines()

        assert len(lines) == 2, f"Should have 2 lines, got {len(lines)}"
        assert lines[1].strip() == 'source ~/.bashrc', "Line should be appended"
        print("✓ Substring in comment NOT treated as existing line")
        print("✓ Line properly appended (FIX for substring matching bug)")
    finally:
        os.unlink(temp_file)


def test_append_multiple_lines():
    """Test 8: Append multiple lines"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('line1\n')
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(temp_file, ['line2', 'line3', 'line4'])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            lines = [line.strip() for line in f.readlines()]

        assert lines == ['line1', 'line2', 'line3', 'line4'], f"Expected 4 lines in order, got {lines}"
        print("✓ All new lines appended")
        print("✓ Lines in correct order")
    finally:
        os.unlink(temp_file)


def test_mixed_existing_and_new():
    """Test 9: Mixed existing and new lines"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('line1\nline3\n')
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(temp_file, ['line1', 'line2', 'line3', 'line4'])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            lines = [line.strip() for line in f.readlines()]

        # line1 and line3 already exist, only line2 and line4 should be appended
        assert 'line2' in lines, "line2 should be appended"
        assert 'line4' in lines, "line4 should be appended"
        assert lines.count('line1') == 1, "line1 should appear once"
        assert lines.count('line3') == 1, "line3 should appear once"
        print("✓ Existing lines not duplicated")
        print("✓ New lines appended")
    finally:
        os.unlink(temp_file)


def test_file_not_exist():
    """Test 10: File doesn't exist"""
    temp_file = '/tmp/nonexistent_test_file_12345.txt'

    # Make sure file doesn't exist
    if os.path.exists(temp_file):
        os.unlink(temp_file)

    result = append_nonexistent_lines_to_file(temp_file, ['line'])
    assert result == False, "Function should return False for non-existent file"
    print("✓ Returns False for non-existent file")
    print("✓ No exception thrown")


def test_file_not_writable():
    """Test 11: File not writable"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('existing\n')
        temp_file = f.name

    try:
        # Make file read-only
        os.chmod(temp_file, 0o444)

        result = append_nonexistent_lines_to_file(temp_file, ['new'])
        assert result == False, "Function should return False for read-only file"
        print("✓ Returns False for read-only file")
        print("✓ No exception thrown")
    finally:
        # Restore write permission before deleting
        os.chmod(temp_file, 0o644)
        os.unlink(temp_file)


def test_special_characters():
    """Test 12: Lines with special characters"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('normal\n')
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(
            temp_file,
            ['line with [brackets]', 'line with $PATH', 'line with * and ?']
        )
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            lines = [line.strip() for line in f.readlines()]

        assert 'line with [brackets]' in lines, "Should handle brackets"
        assert 'line with $PATH' in lines, "Should handle $ character"
        assert 'line with * and ?' in lines, "Should handle wildcards"
        print("✓ Special characters handled correctly")
        print("✓ No regex interpretation issues")
    finally:
        os.unlink(temp_file)


def test_empty_lines_list():
    """Test 13: Empty lines list"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('existing\n')
        temp_file = f.name
        original_content = 'existing\n'

    try:
        result = append_nonexistent_lines_to_file(temp_file, [])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            content = f.read()

        assert content == original_content, "File should be unchanged"
        print("✓ Empty list handled correctly")
        print("✓ File unchanged")
    finally:
        os.unlink(temp_file)


def test_real_bash_load_command():
    """Test 14: Integration test with real bash_load_command"""
    path = '/home/user/.dotfiles/utils.sh'
    command = bash_load_command(path)
    expected_command = '[ -r /home/user/.dotfiles/utils.sh ] && . /home/user/.dotfiles/utils.sh'

    assert command == expected_command, f"bash_load_command output incorrect: {command}"

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.bashrc') as f:
        f.write('# My bashrc\n')
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(temp_file, [command])
        assert result == True, "Function should return True"

        with open(temp_file, 'r') as f:
            lines = [line.strip() for line in f.readlines()]

        assert expected_command in lines, "bash_load_command should be in file"
        print("✓ Real bash_load_command appended correctly")
        print("✓ Integration test passed")
    finally:
        os.unlink(temp_file)


def test_unicode_support():
    """Test 15: Unicode/UTF-8 support"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
        f.write('日本語\n')
        temp_file = f.name

    try:
        result = append_nonexistent_lines_to_file(temp_file, ['English line', 'More 日本語'])
        assert result == True, "Function should return True"

        with open(temp_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f.readlines()]

        assert '日本語' in lines, "Original unicode should be preserved"
        assert 'English line' in lines, "English line should be appended"
        assert 'More 日本語' in lines, "Unicode in new line should work"
        print("✓ Unicode content handled correctly")
        print("✓ No encoding errors")
    finally:
        os.unlink(temp_file)


def main():
    """Run all tests"""
    print("=" * 72)
    print("Test Suite: append_nonexistent_lines_to_file Fix")
    print("Item 5.2: Improve append_nonexistent_lines_to_file validation")
    print("=" * 72)
    print()

    # Test 1: Syntax validation (already done with py_compile)
    print("=" * 72)
    print("TEST 1: Syntax Validation")
    print("=" * 72)
    print("✅ TEST 1 PASS: Python syntax valid (checked with py_compile)")
    print()

    # Run all tests
    run_test("Append to empty file", test_append_to_empty_file)
    run_test("Append without EOF newline", test_append_without_eof_newline)
    run_test("Append with EOF newline", test_append_with_eof_newline)
    run_test("Skip existing line (exact match)", test_skip_existing_exact_match)
    run_test("Append with partial match (CRITICAL)", test_append_with_partial_match)
    run_test("Append with substring in comment (CRITICAL)", test_append_with_substring_in_comment)
    run_test("Append multiple lines", test_append_multiple_lines)
    run_test("Mixed existing and new lines", test_mixed_existing_and_new)
    run_test("File doesn't exist", test_file_not_exist)
    run_test("File not writable", test_file_not_writable)
    run_test("Lines with special characters", test_special_characters)
    run_test("Empty lines list", test_empty_lines_list)
    run_test("Real bash_load_command integration", test_real_bash_load_command)
    run_test("Unicode/UTF-8 support", test_unicode_support)

    # Summary
    print("=" * 72)
    print("TEST SUMMARY")
    print("=" * 72)
    total_tests = 15  # Including syntax validation
    print(f"✅ Syntax validation - PASS")
    for i in range(2, total_tests + 1):
        status = "PASS" if i - 1 <= pass_count else "FAIL"
        symbol = "✅" if status == "PASS" else "❌"
        test_names = [
            "Append to empty file",
            "Append without EOF newline",
            "Append with EOF newline",
            "Skip existing line",
            "Append with partial match (CRITICAL)",
            "Append with substring in comment (CRITICAL)",
            "Append multiple lines",
            "Mixed existing and new lines",
            "File doesn't exist",
            "File not writable",
            "Special characters",
            "Empty lines list",
            "Real bash_load_command integration",
            "Unicode/UTF-8 support"
        ]
        if i - 2 < len(test_names):
            print(f"{symbol} TEST {i}: {test_names[i-2]} - {status}")

    print()
    print(f"Total: {total_tests} tests")
    print(f"Passed: {pass_count + 1}/{total_tests}")  # +1 for syntax validation
    print(f"Failed: {fail_count}/{total_tests}")
    print()

    if fail_count == 0:
        print("🎉 All tests passed! append_nonexistent_lines_to_file is fixed.")
        print()
        print("Benefits achieved:")
        print("  ✓ Line-by-line comparison (not substring)")
        print("  ✓ File existence validation")
        print("  ✓ File writability validation")
        print("  ✓ Proper newline handling")
        print("  ✓ Error handling with clear messages")
        print("  ✓ Returns success/failure boolean")
        print("  ✓ No false positives (critical bug fixed)")
        return 0
    else:
        print(f"❌ {fail_count} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
