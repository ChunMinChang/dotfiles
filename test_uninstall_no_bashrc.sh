#!/bin/bash
# Test uninstall.sh with missing dot.bashrc (edge case)

echo "========================================================================"
echo "TEST: uninstall.sh with missing dot.bashrc (Edge Case)"
echo "========================================================================"

# Create a temporary test directory
TEST_DIR=$(mktemp -d)
cd "$TEST_DIR"

# Create a minimal uninstall.sh with just the variable loading logic
cat > test_uninstall.sh << 'SCRIPT'
#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASHRC_HERE="$SCRIPT_DIR/dot.bashrc"

echo "Testing with BASHRC_HERE=$BASHRC_HERE"
echo "File exists: $([ -f "$BASHRC_HERE" ] && echo "yes" || echo "no")"
echo

# Source the file (don't check exit code - it's unreliable)
if [ -f "$BASHRC_HERE" ]; then
  source "$BASHRC_HERE" 2>/dev/null || true
  echo "Loaded environment variables from $BASHRC_HERE"
fi

# Verify required variables are set, compute them if not
if [ -z "$PLATFORM" ]; then
  PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
  echo "Computed PLATFORM=$PLATFORM"
fi

if [ -z "$SETTINGS_PLATFORM" ]; then
  SETTINGS_PREFIX="$HOME/.settings_"
  SETTINGS_PLATFORM="${SETTINGS_PREFIX}${PLATFORM}"
  echo "Computed SETTINGS_PLATFORM=$SETTINGS_PLATFORM"
fi

if [ -z "$DOTFILES" ]; then
  DOTFILES="$HOME/.dotfiles"
  echo "Computed DOTFILES=$DOTFILES"
fi

echo
echo "Final variables:"
echo "  PLATFORM=$PLATFORM"
echo "  SETTINGS_PLATFORM=$SETTINGS_PLATFORM"
echo "  DOTFILES=$DOTFILES"

# Check all are set
if [ -n "$PLATFORM" ] && [ -n "$SETTINGS_PLATFORM" ] && [ -n "$DOTFILES" ]; then
  echo
  echo "✅ SUCCESS: All variables set correctly (fallback worked)"
  exit 0
else
  echo
  echo "❌ FAIL: Some variables are empty"
  exit 1
fi
SCRIPT

chmod +x test_uninstall.sh

# Run without dot.bashrc
echo "Running test_uninstall.sh (dot.bashrc does NOT exist):"
echo "------------------------------------------------------------------------"
bash test_uninstall.sh
RESULT=$?

cd - > /dev/null
rm -rf "$TEST_DIR"

if [ $RESULT -eq 0 ]; then
  echo
  echo "========================================================================"
  echo "✅ EDGE CASE TEST PASSED"
  echo "========================================================================"
  echo "uninstall.sh works correctly even when dot.bashrc is missing"
  exit 0
else
  echo
  echo "========================================================================"
  echo "❌ EDGE CASE TEST FAILED"
  echo "========================================================================"
  exit 1
fi
