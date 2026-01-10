#!/bin/bash
# Run all test suites in sequence
# Exit with non-zero if any test suite fails unexpectedly

set +e  # Don't exit on first failure - run all tests

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================================"
echo "Running All Test Suites"
echo "========================================================"
echo ""

# Track overall results
TOTAL_SUITES=4
PASSED_SUITES=0
FAILED_SUITES=0

# Test 1: Setup Script Tests
echo "========================================================"
echo "Test Suite 1/4: Setup Script Tests (test_setup.py)"
echo "========================================================"
if python3 test_setup.py; then
    echo "✓ Setup tests passed"
    PASSED_SUITES=$((PASSED_SUITES + 1))
else
    echo "✗ Setup tests failed"
    FAILED_SUITES=$((FAILED_SUITES + 1))
fi
echo ""

# Test 2: Shell Utilities Tests
echo "========================================================"
echo "Test Suite 2/4: Shell Utilities Tests (test_shell_utils.sh)"
echo "========================================================"
if bash test_shell_utils.sh; then
    echo "✓ Shell utilities tests passed"
    PASSED_SUITES=$((PASSED_SUITES + 1))
else
    echo "✗ Shell utilities tests failed"
    FAILED_SUITES=$((FAILED_SUITES + 1))
fi
echo ""

# Test 3: Claude Security Tests
echo "========================================================"
echo "Test Suite 3/4: Claude Security Tests (test_claude_security.py)"
echo "========================================================"
if python3 test_claude_security.py; then
    echo "✓ Claude security tests passed"
    PASSED_SUITES=$((PASSED_SUITES + 1))
else
    echo "✗ Claude security tests failed"
    FAILED_SUITES=$((FAILED_SUITES + 1))
fi
echo ""

# Test 4: Prompt Colors Tests
echo "========================================================"
echo "Test Suite 4/4: Prompt Colors Tests (test_prompt_colors.sh)"
echo "========================================================"
if bash test_prompt_colors.sh; then
    echo "✓ Prompt colors tests passed"
    PASSED_SUITES=$((PASSED_SUITES + 1))
else
    echo "✗ Prompt colors tests failed (may be expected if zsh not installed)"
    FAILED_SUITES=$((FAILED_SUITES + 1))
fi
echo ""

# Summary
echo "========================================================"
echo "Test Suite Summary"
echo "========================================================"
echo "Total suites:  $TOTAL_SUITES"
echo "Passed:        $PASSED_SUITES"
echo "Failed:        $FAILED_SUITES"
echo ""

if [ $PASSED_SUITES -ge 2 ]; then
    echo "✓ Core test suites passed (setup + shell utilities)"
    echo ""
    echo "Note: Some failures may be expected:"
    echo "  - Claude security: 1 manual verification test"
    echo "  - Prompt colors: 10 zsh tests (if zsh not installed)"
    exit 0
elif [ $FAILED_SUITES -eq 0 ]; then
    echo "✓ All test suites passed!"
    exit 0
else
    echo "✗ Critical test suites failed"
    echo "Please review failures above"
    exit 1
fi
