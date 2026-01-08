# Testing Plan - Fix CommandExists Inverted Logic

## Item 2.3: Fix inverted logic in CommandExists function

**File**: `utils.sh:8-17`, callers in `utils.sh:87,90,92` and `mozilla/gecko/tools.sh:10,19`
**Impact**: Medium - Improves code clarity, follows Unix conventions

---

## The Problem

### Current Implementation (INVERTED):

```bash
function CommandExists()
{
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    echo 1  # ❌ Returns 1 if command EXISTS
  else
    echo >&2 "$cmd is not installed.";
    echo 0  # ❌ Returns 0 if command DOES NOT EXIST
  fi
}
```

### Issues:
1. ❌ **Inverted logic**: Returns 1 for success (found), 0 for failure (not found)
2. ❌ **Against Unix convention**: Exit code 0 = success, non-zero = failure
3. ❌ **Confusing**: Callers must remember inverted logic
4. ❌ **Error prone**: Easy to use incorrectly
5. ❌ **Inconsistent**: Other functions use standard conventions

### Current Usage:

**mozilla/gecko/tools.sh**:
```bash
if [ $(CommandExists git-cinnabar) -eq 0 ]; then  # 0 = NOT found
  git cinnabar download
fi

if [ $(CommandExists moz-phab) -eq 0 ]; then  # 0 = NOT found
  PrintError 'No moz-phab command!'
fi
```

**utils.sh**:
```bash
if [ $(CommandExists npx) -eq 1 ]; then  # 1 = found
  npx live-server ...
elif [ $(CommandExists python3) -eq 1 ]; then  # 1 = found
  python3 -m http.server ...
elif [ $(CommandExists python) -eq 1 ]; then  # 1 = found
  python -m SimpleHTTPServer ...
fi
```

---

## The Solution

### New Implementation (STANDARD):

```bash
function CommandExists()
{
  local cmd="$1"
  if command -v "$cmd" >/dev/null 2>&1; then
    return 0  # ✅ Returns 0 (success) if command EXISTS
  else
    echo >&2 "$cmd is not installed."
    return 1  # ✅ Returns 1 (failure) if command DOES NOT EXIST
  fi
}
```

### Key Changes:
1. ✅ Use `return` instead of `echo` (proper exit codes)
2. ✅ Return 0 for success (found)
3. ✅ Return 1 for failure (not found)
4. ✅ Follows Unix convention
5. ✅ Can be used in `if` statements directly

### New Usage Pattern:

**mozilla/gecko/tools.sh**:
```bash
if ! CommandExists git-cinnabar; then  # Standard: if NOT found
  git cinnabar download
fi

if ! CommandExists moz-phab; then  # Standard: if NOT found
  PrintError 'No moz-phab command!'
fi
```

**utils.sh**:
```bash
if CommandExists npx; then  # Standard: if found
  npx live-server ...
elif CommandExists python3; then  # Standard: if found
  python3 -m http.server ...
elif CommandExists python; then  # Standard: if found
  python -m SimpleHTTPServer ...
fi
```

### Benefits:
- ✅ **Standard convention**: 0 = success, 1 = failure
- ✅ **Clearer code**: `if CommandExists cmd` reads naturally
- ✅ **Less error-prone**: Follows expectations
- ✅ **Consistent**: Matches other functions and Unix tools

---

## Changes Required

### File 1: utils.sh (function definition)
**Change** lines 8-17:
- Replace `echo 1` with `return 0`
- Replace `echo 0` with `return 1`

### File 2: utils.sh (callers in HostHTTP)
**Change** lines 87, 90, 92:
- Replace `if [ $(CommandExists cmd) -eq 1 ]` with `if CommandExists cmd`

### File 3: mozilla/gecko/tools.sh (callers)
**Change** lines 10, 19:
- Replace `if [ $(CommandExists cmd) -eq 0 ]` with `if ! CommandExists cmd`

---

## Test Cases

### Test 1: Syntax Validation
**Command**: `bash -n utils.sh && bash -n mozilla/gecko/tools.sh`
**Expected**: No syntax errors

### Test 2: CommandExists with Existing Command
**Test**: Check for command that exists (e.g., bash)
```bash
source utils.sh
if CommandExists bash; then
  echo "✓ bash found"
else
  echo "✗ bash not found (WRONG!)"
fi
```

**Expected**: ✅ "✓ bash found"

### Test 3: CommandExists with Non-Existent Command
**Test**: Check for command that doesn't exist
```bash
source utils.sh
if CommandExists nonexistent-command-12345; then
  echo "✗ command found (WRONG!)"
else
  echo "✓ command not found"
fi
```

**Expected**: ✅ "✓ command not found"
**Expected stderr**: "nonexistent-command-12345 is not installed."

### Test 4: Negated Check (if NOT exists)
**Test**: Check negated condition
```bash
if ! CommandExists nonexistent-command-12345; then
  echo "✓ correctly detected command missing"
else
  echo "✗ incorrectly thinks command exists"
fi
```

**Expected**: ✅ "✓ correctly detected command missing"

### Test 5: HostHTTP Function
**Test**: Verify HostHTTP uses CommandExists correctly
```bash
source utils.sh
# HostHTTP should try npx, python3, python in order
# We can't fully test this without installing/removing tools
# But we can verify it sources and runs
HostHTTP --help 2>&1 | head -5
```

**Expected**: ✅ Function runs (tries commands in order)

### Test 6: mozilla/gecko/tools.sh Integration
**Test**: Verify mozilla tools script works
```bash
source mozilla/gecko/tools.sh 2>&1
```

**Expected**: ✅ Script runs, checks for git-cinnabar and moz-phab

### Test 7: Return Code Verification
**Test**: Verify actual return codes
```bash
source utils.sh
CommandExists bash
echo "Exit code for existing command: $?"  # Should be 0

CommandExists nonexistent-cmd-xyz
echo "Exit code for missing command: $?"  # Should be 1
```

**Expected**:
- Existing command: 0 ✅
- Missing command: 1 ✅

---

## Success Criteria

- ✅ Syntax validation passes
- ✅ CommandExists returns 0 for existing commands
- ✅ CommandExists returns 1 for missing commands
- ✅ Can use `if CommandExists cmd` directly
- ✅ Can use `if ! CommandExists cmd` for negation
- ✅ HostHTTP works correctly
- ✅ mozilla/gecko/tools.sh works correctly
- ✅ No breaking changes (logic is correct)

---

## Risk Assessment

**Risk Level**: LOW-MEDIUM

**Rationale**:
1. Simple logic change (well-defined)
2. All callers identified and updated
3. Easy to test (command presence)
4. Follows standard patterns
5. Internal function (no external API)

**Potential Issues**:
- If we miss a caller, it will fail (but tests will catch)
- Logic inversion could be confusing during review

**Mitigation**:
- Search for ALL callers before fixing
- Test each caller individually
- Comprehensive test suite

---

## Backward Compatibility

### Function Signature: UNCHANGED ✅
- Same function name: `CommandExists`
- Same parameter: command name
- Same stderr output for missing commands

### Calling Pattern: CHANGED (Improved) ⚠️
**Before** (confusing):
```bash
if [ $(CommandExists cmd) -eq 1 ]; then  # if found
if [ $(CommandExists cmd) -eq 0 ]; then  # if NOT found
```

**After** (standard):
```bash
if CommandExists cmd; then       # if found
if ! CommandExists cmd; then     # if NOT found
```

**Breaking Change**: Yes, but...
- Function is internal to this repo
- All callers updated in same commit
- No external dependencies
- Better pattern (worth the change)

---

## Testing Methodology

1. **Unit test** CommandExists with known commands
2. **Unit test** CommandExists with missing commands
3. **Integration test** HostHTTP function
4. **Integration test** mozilla/gecko/tools.sh
5. **Return code verification** using $?

---

## Benefits

### 1. Clarity ✅
- `if CommandExists cmd` reads naturally
- No need to remember inverted logic
- Self-documenting code

### 2. Standard Convention ✅
- Follows Unix exit code convention
- Consistent with other functions
- Matches expectations

### 3. Less Error-Prone ✅
- Harder to use incorrectly
- Intuitive behavior
- Standard pattern

### 4. Maintainability ✅
- Future developers will understand
- No surprising behavior
- Professional implementation

---

## Implementation Notes

### Why Use `return` Instead of `echo`?

**Old approach** (echoing values):
```bash
result=$(CommandExists cmd)
if [ $result -eq 1 ]; then
```

**Problems**:
- Captures stdout
- Can't use directly in conditionals
- Awkward syntax

**New approach** (return codes):
```bash
if CommandExists cmd; then
```

**Benefits**:
- Standard shell pattern
- Direct use in conditionals
- Clean, readable

### Error Message Handling

The function outputs error message to stderr:
```bash
echo >&2 "$cmd is not installed."
```

This is correct:
- Doesn't interfere with return code
- Allows caller to see why check failed
- Standard practice

---

## All Callers Identified

1. ✅ `utils.sh:87` - HostHTTP function (npx)
2. ✅ `utils.sh:90` - HostHTTP function (python3)
3. ✅ `utils.sh:92` - HostHTTP function (python)
4. ✅ `mozilla/gecko/tools.sh:10` - git-cinnabar check
5. ✅ `mozilla/gecko/tools.sh:19` - moz-phab check

**Total**: 5 call sites to update
