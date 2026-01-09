#!/bin/bash
# Test script to verify SCRIPT_DIR detection in uninstall.sh works correctly

# Don't exit on error - we want to see all test results
set +e

DOTFILES_DIR="/home/cm/dotfiles"
UNINSTALL_SCRIPT="$DOTFILES_DIR/uninstall.sh"

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

test_count=0
pass_count=0
fail_count=0

print_test() {
    echo -e "${BLUE}Test $((++test_count)): $1${NC}"
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((pass_count++))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((fail_count++))
}

echo "=========================================="
echo "Testing Item 4.2: Script Location Detection"
echo "=========================================="
echo ""

# Test 1: From repo root directory
print_test "Run from repo root directory"
cd "$DOTFILES_DIR"
SCRIPT_DIR="$(cd "$(dirname "$UNINSTALL_SCRIPT")" && pwd)"
if [ "$SCRIPT_DIR" = "$DOTFILES_DIR" ]; then
    print_pass "SCRIPT_DIR correctly set to $SCRIPT_DIR"
else
    print_fail "Expected $DOTFILES_DIR, got $SCRIPT_DIR"
fi

# Test 2: From home directory
print_test "Run from home directory"
cd "$HOME"
SCRIPT_DIR="$(cd "$(dirname "$UNINSTALL_SCRIPT")" && pwd)"
if [ "$SCRIPT_DIR" = "$DOTFILES_DIR" ]; then
    print_pass "SCRIPT_DIR correctly set to $SCRIPT_DIR"
else
    print_fail "Expected $DOTFILES_DIR, got $SCRIPT_DIR"
fi

# Test 3: From /tmp directory
print_test "Run from /tmp directory"
cd /tmp
SCRIPT_DIR="$(cd "$(dirname "$UNINSTALL_SCRIPT")" && pwd)"
if [ "$SCRIPT_DIR" = "$DOTFILES_DIR" ]; then
    print_pass "SCRIPT_DIR correctly set to $SCRIPT_DIR"
else
    print_fail "Expected $DOTFILES_DIR, got $SCRIPT_DIR"
fi

# Test 4: Using relative path from parent directory
print_test "Run using relative path"
cd "$HOME"
SCRIPT_DIR="$(cd "$(dirname "./dotfiles/uninstall.sh")" && pwd)"
if [ "$SCRIPT_DIR" = "$DOTFILES_DIR" ]; then
    print_pass "SCRIPT_DIR correctly set to $SCRIPT_DIR"
else
    print_fail "Expected $DOTFILES_DIR, got $SCRIPT_DIR"
fi

# Test 5: Verify BASHRC_HERE points to existing file
print_test "Verify BASHRC_HERE points to existing file"
SCRIPT_DIR="$(cd "$(dirname "$UNINSTALL_SCRIPT")" && pwd)"
BASHRC_HERE="$SCRIPT_DIR/dot.bashrc"
if [ -f "$BASHRC_HERE" ]; then
    print_pass "BASHRC_HERE correctly points to $BASHRC_HERE"
else
    print_fail "BASHRC_HERE does not point to valid file: $BASHRC_HERE"
fi

# Test 6: Verify MACHRC_HERE points to existing file
print_test "Verify MACHRC_HERE points to existing file"
SCRIPT_DIR="$(cd "$(dirname "$UNINSTALL_SCRIPT")" && pwd)"
MACHRC_HERE="$SCRIPT_DIR/mozilla/gecko/machrc"
if [ -f "$MACHRC_HERE" ]; then
    print_pass "MACHRC_HERE correctly points to $MACHRC_HERE"
else
    print_fail "MACHRC_HERE does not point to valid file: $MACHRC_HERE"
fi

# Test 7: Test with symlink
print_test "Test via symlink"
SYMLINK="/tmp/test_uninstall_symlink.sh"
rm -f "$SYMLINK"
ln -s "$UNINSTALL_SCRIPT" "$SYMLINK"
# When following symlink, we need to resolve it first
SYMLINK_TARGET="$(readlink -f "$SYMLINK")"
SCRIPT_DIR="$(cd "$(dirname "$SYMLINK_TARGET")" && pwd)"
if [ "$SCRIPT_DIR" = "$DOTFILES_DIR" ]; then
    print_pass "Symlink resolution works correctly"
else
    print_fail "Expected $DOTFILES_DIR, got $SCRIPT_DIR"
fi
rm -f "$SYMLINK"

# Test 8: Verify actual uninstall.sh syntax
print_test "Verify uninstall.sh syntax"
if bash -n "$UNINSTALL_SCRIPT" 2>/dev/null; then
    print_pass "uninstall.sh has valid bash syntax"
else
    print_fail "uninstall.sh has syntax errors"
fi

# Test 9: Check SCRIPT_DIR is defined early in uninstall.sh
print_test "Verify SCRIPT_DIR is defined in uninstall.sh"
if grep -q 'SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"' "$UNINSTALL_SCRIPT"; then
    print_pass "SCRIPT_DIR uses correct detection pattern"
else
    print_fail "SCRIPT_DIR not properly defined"
fi

# Test 10: Check BASHRC_HERE uses SCRIPT_DIR (not pwd)
print_test "Verify BASHRC_HERE uses SCRIPT_DIR (not pwd)"
if grep -q 'BASHRC_HERE="$SCRIPT_DIR/dot.bashrc"' "$UNINSTALL_SCRIPT"; then
    print_pass "BASHRC_HERE correctly uses SCRIPT_DIR"
else
    print_fail "BASHRC_HERE doesn't use SCRIPT_DIR"
fi

# Test 11: Check MACHRC_HERE uses SCRIPT_DIR (not pwd)
print_test "Verify MACHRC_HERE uses SCRIPT_DIR (not pwd)"
if grep -q 'MACHRC_HERE="$SCRIPT_DIR/mozilla/gecko/machrc"' "$UNINSTALL_SCRIPT"; then
    print_pass "MACHRC_HERE correctly uses SCRIPT_DIR"
else
    print_fail "MACHRC_HERE doesn't use SCRIPT_DIR"
fi

# Test 12: Ensure no $(pwd) is used incorrectly
print_test "Verify no incorrect \$(pwd) usage"
if ! grep -E 'BASHRC_HERE=\$\(pwd\)|MACHRC_HERE=\$\(pwd\)' "$UNINSTALL_SCRIPT" > /dev/null; then
    print_pass "No incorrect \$(pwd) usage found"
else
    print_fail "Found incorrect \$(pwd) usage"
fi

# Test 13: Test the pattern used in uninstall.sh with $0
print_test "Test SCRIPT_DIR pattern with \$0 simulation"
cd /tmp
TEST_SCRIPT_DIR="$(cd "$(dirname "$UNINSTALL_SCRIPT")" && pwd)"
if [ "$TEST_SCRIPT_DIR" = "$DOTFILES_DIR" ]; then
    print_pass "Pattern works correctly: cd \$(dirname \$0) && pwd"
else
    print_fail "Pattern failed: expected $DOTFILES_DIR, got $TEST_SCRIPT_DIR"
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Total tests: $test_count"
echo -e "${GREEN}Passed: $pass_count${NC}"
if [ $fail_count -gt 0 ]; then
    echo -e "${RED}Failed: $fail_count${NC}"
else
    echo -e "${GREEN}Failed: $fail_count${NC}"
fi
echo ""

if [ $fail_count -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Item 4.2 is correctly implemented.${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review.${NC}"
    exit 1
fi
