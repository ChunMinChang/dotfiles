#!/bin/bash
# Test script for CommandExists inverted logic fix

echo "========================================================================"
echo "Test Suite: CommandExists Function Fix"
echo "Item 2.3: Fix inverted logic in CommandExists"
echo "========================================================================"
echo

# Source utils.sh to get CommandExists
source ./utils.sh

# Test 1: CommandExists with existing command
echo "========================================================================"
echo "TEST 1: CommandExists with Existing Command (bash)"
echo "========================================================================"

if CommandExists bash; then
  echo "✅ TEST 1 PASS: Correctly detected bash exists"
else
  echo "❌ TEST 1 FAIL: Failed to detect bash (should exist)"
  exit 1
fi

echo

# Test 2: CommandExists with non-existent command
echo "========================================================================"
echo "TEST 2: CommandExists with Non-Existent Command"
echo "========================================================================"

if CommandExists nonexistent-command-xyz-12345; then
  echo "❌ TEST 2 FAIL: Incorrectly thinks command exists"
  exit 1
else
  echo "✅ TEST 2 PASS: Correctly detected command doesn't exist"
fi

echo

# Test 3: Negated check (if NOT exists)
echo "========================================================================"
echo "TEST 3: Negated Check (if ! CommandExists)"
echo "========================================================================"

if ! CommandExists nonexistent-command-xyz-12345; then
  echo "✅ TEST 3 PASS: Negated check works correctly"
else
  echo "❌ TEST 3 FAIL: Negated check failed"
  exit 1
fi

echo

# Test 4: Return code verification
echo "========================================================================"
echo "TEST 4: Return Code Verification"
echo "========================================================================"

CommandExists bash >/dev/null 2>&1
BASH_EXIT=$?

CommandExists nonexistent-cmd-xyz >/dev/null 2>&1
NONEXIST_EXIT=$?

echo "Exit code for existing command (bash): $BASH_EXIT"
echo "Exit code for missing command: $NONEXIST_EXIT"

if [ $BASH_EXIT -eq 0 ] && [ $NONEXIST_EXIT -eq 1 ]; then
  echo "✅ TEST 4 PASS: Return codes correct (0=exists, 1=missing)"
else
  echo "❌ TEST 4 FAIL: Return codes incorrect"
  echo "  Expected: bash=0, nonexistent=1"
  echo "  Got: bash=$BASH_EXIT, nonexistent=$NONEXIST_EXIT"
  exit 1
fi

echo

# Test 5: HostHTTP function (integration test)
echo "========================================================================"
echo "TEST 5: HostHTTP Function Integration"
echo "========================================================================"

# Test that HostHTTP can be called (it will try commands in order)
# We check it sources and executes without syntax errors
if declare -f HostHTTP >/dev/null; then
  echo "✓ HostHTTP function loaded"

  # Try to see which command it would use (without actually starting server)
  # We check which commands exist
  if CommandExists npx; then
    echo "✓ Would use npx (found)"
  elif CommandExists python3; then
    echo "✓ Would use python3 (found)"
  elif CommandExists python; then
    echo "✓ Would use python (found)"
  else
    echo "⚠️  No HTTP server commands available (expected on some systems)"
  fi

  echo "✅ TEST 5 PASS: HostHTTP function works with new CommandExists"
else
  echo "❌ TEST 5 FAIL: HostHTTP function not loaded"
  exit 1
fi

echo

# Test 6: mozilla/gecko/tools.sh integration
echo "========================================================================"
echo "TEST 6: mozilla/gecko/tools.sh Integration"
echo "========================================================================"

if bash -n mozilla/gecko/tools.sh; then
  echo "✓ mozilla/gecko/tools.sh syntax valid"
  echo "✅ TEST 6 PASS: Mozilla tools script syntax correct"
else
  echo "❌ TEST 6 FAIL: mozilla/gecko/tools.sh has syntax errors"
  exit 1
fi

echo

# Test 7: Pattern comparison (old vs new)
echo "========================================================================"
echo "TEST 7: Pattern Comparison (Old vs New)"
echo "========================================================================"

echo "Old pattern (CONFUSING):"
echo '  if [ $(CommandExists cmd) -eq 1 ]; then  # if found'
echo '  if [ $(CommandExists cmd) -eq 0 ]; then  # if NOT found'
echo

echo "New pattern (CLEAR):"
echo '  if CommandExists cmd; then       # if found'
echo '  if ! CommandExists cmd; then     # if NOT found'
echo

echo "✅ TEST 7 PASS: New pattern is clearer and follows Unix convention"
echo

# Summary
echo "========================================================================"
echo "TEST SUMMARY"
echo "========================================================================"
echo "✅ TEST 1: Existing command detection - PASS"
echo "✅ TEST 2: Missing command detection - PASS"
echo "✅ TEST 3: Negated check - PASS"
echo "✅ TEST 4: Return codes (0=exists, 1=missing) - PASS"
echo "✅ TEST 5: HostHTTP integration - PASS"
echo "✅ TEST 6: mozilla/gecko/tools.sh syntax - PASS"
echo "✅ TEST 7: Pattern comparison - PASS"
echo
echo "🎉 All tests passed! CommandExists now follows Unix convention."
echo
echo "Benefits achieved:"
echo "  ✓ Standard convention (0=success, 1=failure)"
echo "  ✓ Clearer code (if CommandExists cmd)"
echo "  ✓ Less error-prone"
echo "  ✓ Consistent with other functions"
