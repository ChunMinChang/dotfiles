# Testing Plan - Fix Dangerous eval Usage

## Item 1.1: Fix dangerous eval usage in uninstall.sh

**File**: `uninstall.sh:57-69`
**Impact**: CRITICAL - Security vulnerability

---

## The Problem

### Current Code (DANGEROUS):
```bash
# Load environment variables to this script
BASHRC_HERE="$SCRIPT_DIR/dot.bashrc"
source "$BASHRC_HERE"

# TODO: Not sure why `source $BASHRC_HERE` succeeds but `$?` return 1
if [ $? -eq 0 ] || [ ! -z "$PLATFORM" ]; then
  echo "Load environment variables in $BASHRC_HERE"
else
  PrintWarning "$BASHRC_HERE is not loadable"
  PrintWarning "Apply environment variables by parsing $BASHRC_HERE:"
  # Show the parsed environment variables in $BASHRC_HERE
  grep "^[^#;^export;].*=" "$BASHRC_HERE"
  # Force loading environment variables in $BASHRC_HERE
  eval $(grep "^[^#;^export;].*=" "$BASHRC_HERE")  # ❌ DANGEROUS!
fi
```

### Security Issues:
1. **Code Injection**: `eval` executes arbitrary code from grep output
2. **No Validation**: No check of what's being executed
3. **Fragile Pattern**: Grep pattern can match unintended lines
4. **Attack Vector**: If bashrc is modified maliciously, code will execute

### Example Attack:
```bash
# If dot.bashrc contained (by accident or maliciously):
PLATFORM=linux; rm -rf ~/*

# The eval would execute it! ☠️
```

---

## Root Cause Analysis

### Why is $? non-zero after successful source?

Looking at dot.bashrc:
```bash
DOTFILES=~/.dotfiles
...
[[ -r $DOTFILES/utils.sh ]] && . $DOTFILES/utils.sh
[[ -r $DOTFILES/git/utils.sh ]] && . $DOTFILES/git/utils.sh
...
[ -r $SETTINGS_PLATFORM ] && . $SETTINGS_PLATFORM
```

**Issue**: The `&&` conditions return non-zero if files don't exist!
- If `$DOTFILES/utils.sh` doesn't exist, `[[ -r ... ]]` returns 1
- This makes `source` appear to "fail" even though variables are set

**The Real Problem**: Checking `$?` after `source` is unreliable

---

## The Solution

### New Code (SAFE):
```bash
# Load environment variables from dot.bashrc
BASHRC_HERE="$SCRIPT_DIR/dot.bashrc"

# Source the file (don't check exit code, it's unreliable)
if [ -f "$BASHRC_HERE" ]; then
  source "$BASHRC_HERE" 2>/dev/null || true
fi

# Verify required variables are set, compute them if not
if [ -z "$PLATFORM" ]; then
  PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
fi

if [ -z "$SETTINGS_PLATFORM" ]; then
  SETTINGS_PREFIX="$HOME/.settings_"
  SETTINGS_PLATFORM="${SETTINGS_PREFIX}${PLATFORM}"
fi

if [ -z "$DOTFILES" ]; then
  DOTFILES="$HOME/.dotfiles"
fi

echo "Environment loaded: PLATFORM=$PLATFORM"
```

### Why This Is Better:
1. ✅ **No eval**: No code execution vulnerability
2. ✅ **Safe fallback**: Computes variables if not set
3. ✅ **Clear logic**: Obvious what's happening
4. ✅ **Robust**: Works even if sourcing fails
5. ✅ **Maintainable**: Future developers will understand

---

## Variables Needed by uninstall.sh

From analyzing the script, these variables are required:

| Variable | Used At | Purpose | Fallback Value |
|----------|---------|---------|----------------|
| PLATFORM | Line 72, 81, 106 | Detect OS | `uname -s \| tr '[:upper:]' '[:lower:]'` |
| SETTINGS_PLATFORM | Line 75 | Platform settings path | `$HOME/.settings_$PLATFORM` |
| DOTFILES | Line 87 | Dotfiles symlink | `$HOME/.dotfiles` |

All three can be computed directly without eval.

---

## Test Cases

### Test 1: Syntax Validation
**Command**: `bash -n uninstall.sh`
**Expected**: No syntax errors

### Test 2: Normal Operation (dot.bashrc exists and loads)
**Setup**:
- dot.bashrc exists
- Can be sourced successfully
- Sets all variables

**Expected**:
- Variables loaded from dot.bashrc
- Script proceeds normally
- No eval executed

### Test 3: dot.bashrc source "fails" (non-zero exit)
**Setup**:
- dot.bashrc exists but sourcing returns non-zero
- This simulates the original problem

**Expected**:
- Variables still set from source
- Or computed as fallback
- No eval executed
- Script proceeds normally

### Test 4: dot.bashrc missing
**Setup**:
- Temporarily rename dot.bashrc

**Expected**:
- Fallback variables computed
- PLATFORM = linux (on Linux)
- SETTINGS_PLATFORM = $HOME/.settings_linux
- DOTFILES = $HOME/.dotfiles
- Script proceeds without errors

### Test 5: Variables Not Set (Fallback Test)
**Setup**:
- Mock scenario where source doesn't set variables

**Expected**:
- Fallback computation works
- All required variables set correctly

### Test 6: Security Test (Prove eval is gone)
**Test**: Verify eval line removed
```bash
grep -n "eval" uninstall.sh
```

**Expected**: No eval found (or only in comments)

### Test 7: Integration Test
**Command**: `bash uninstall.sh` (dry-run style check)
**Expected**:
- Script runs without errors
- Shows correct variable values
- No security warnings

---

## Testing Methodology

We'll test on Linux:
1. **Syntax check** with bash -n
2. **Variable computation** by running script parts
3. **Integration test** by running full script
4. **Security audit** by searching for eval
5. **Edge cases** with missing files

---

## Success Criteria

- ✅ Syntax validation passes
- ✅ eval removed completely
- ✅ Variables correctly set in all scenarios
- ✅ Fallback computation works
- ✅ No breaking changes to functionality
- ✅ Script runs successfully
- ✅ More secure than before

---

## Risk Assessment

**Risk Level**: VERY LOW

**Rationale**:
1. Simple variable assignment (no complex logic)
2. eval removal is pure security improvement
3. Fallback values match original intent
4. Can't make security worse (eval is already dangerous)
5. Easy to test and verify

**Testing Limitation**:
- Cannot test macOS-specific paths (on Linux)
- But logic is platform-agnostic
- Variables computed correctly for any platform

---

## Security Improvement

### Before (eval approach):
- **Severity**: CRITICAL
- **Attack Vector**: Code injection via bashrc modification
- **Exploitability**: High (if attacker controls bashrc)
- **Impact**: Arbitrary code execution

### After (safe approach):
- **Severity**: None
- **Attack Vector**: None
- **Exploitability**: N/A
- **Impact**: N/A

**Security Gain**: Eliminates critical code injection vulnerability
