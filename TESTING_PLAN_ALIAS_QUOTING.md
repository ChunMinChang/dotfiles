# Testing Plan - Fix Fragile Alias Quoting

## Item 3.2: Fix fragile alias quoting

**File**: `mozilla/gecko/alias.sh:43`
**Impact**: Low-Medium - Improves robustness, prevents quoting issues

---

## The Problem

### Current Code (FRAGILE):

```bash
alias mfmtuc='GitUncommit "./mach clang-format --path"' # Format all uncommit files
```

### Issues:
1. **Nested quotes**: Single quotes wrapping double quotes
2. **Fragile quoting**: Inner quotes passed literally to GitUncommit
3. **Unclear intent**: Is the command string supposed to be quoted?
4. **Alias limitation**: Aliases don't handle complex arguments well
5. **Maintainability**: Hard to modify or debug

### How It Currently Works:

```bash
# When user runs:
mfmtuc

# It expands to:
GitUncommit "./mach clang-format --path"

# GitUncommit receives the string with quotes:
local cmd="./mach clang-format --path"  # Quotes included

# Then runs:
git ls-files ... -z | xargs -0 "./mach clang-format --path"
```

**The nested quotes work but are fragile and confusing.**

---

## The Solution

### Convert Alias to Function (ROBUST):

```bash
# Format all uncommit files
function MozFormatUncommit() {
  GitUncommit './mach clang-format --path'
}
alias mfmtuc='MozFormatUncommit'  # Keep alias for backward compatibility
```

### Benefits:
1. ✅ **Clear quoting**: Explicit single quotes, no nesting
2. ✅ **Documented**: Function can have comments
3. ✅ **Maintainable**: Easy to modify or extend
4. ✅ **Robust**: Functions handle arguments properly
5. ✅ **Backward compatible**: Keep alias pointing to function
6. ✅ **Consistent**: Matches other functions in the file (MozCheckDiff, UpdateCrate)

### Alternative Solution (Simpler):

If we want to keep it as just an alias without the function wrapper:

```bash
alias mfmtuc="GitUncommit './mach clang-format --path'"
```

**Change**: Use double quotes on outside, single quotes on inside
- Clearer quoting hierarchy
- Less confusing than current mix

But converting to function is the better long-term solution.

---

## Comparison with Other Aliases

### Similar Pattern in the File:

Looking at other aliases:
```bash
alias mfmt='./mach clang-format'                # Simple command
alias mfmtfor='./mach clang-format --path'      # Command with args
alias mfmtuc='GitUncommit "./mach clang-format --path"'  # Nested quotes!
```

**Recommendation**: mfmtuc should be a function for consistency

### Functions Already in the File:

```bash
function MozCheckDiff() { ... }
function UpdateCrate() { ... }
function W3CSpec() { ... }
```

**Pattern**: Complex operations → functions
**Conclusion**: mfmtuc should follow this pattern

---

## Changes Required

### Option 1: Convert to Function (RECOMMENDED)

**Add** function MozFormatUncommit
**Keep** alias mfmtuc pointing to function

### Option 2: Fix Quoting Only

**Change** alias to use clearer quote hierarchy

---

## Test Cases

### Test 1: Syntax Validation
**Command**: `bash -n mozilla/gecko/alias.sh`
**Expected**: No syntax errors

### Test 2: Alias Exists
**Test**: Verify alias is defined
```bash
source mozilla/gecko/alias.sh
alias mfmtuc
```

**Expected**: Shows alias definition

### Test 3: Function Works (Option 1)
**Test**: Call function directly
```bash
source mozilla/gecko/alias.sh
# Create test repo with uncommitted file
touch test.cpp
git add test.cpp
echo "code" > test.cpp

MozFormatUncommit  # Should try to format test.cpp
```

**Expected**: Attempts to run ./mach clang-format --path test.cpp

### Test 4: Alias Points to Function (Option 1)
**Test**: Use alias
```bash
source mozilla/gecko/alias.sh
mfmtuc  # Should call MozFormatUncommit
```

**Expected**: Same behavior as calling function directly

### Test 5: Backward Compatibility
**Test**: Existing usage still works
```bash
# Old usage:
mfmtuc

# Should still work after change
```

**Expected**: ✅ Same behavior as before

### Test 6: Quote Handling
**Test**: Verify command passed correctly to GitUncommit
```bash
# Check what GitUncommit receives
# (Can add debug echo in GitUncommit temporarily)
```

**Expected**: Command string without extra quotes

---

## Success Criteria

- ✅ Syntax validation passes
- ✅ Alias/function works correctly
- ✅ Backward compatible (mfmtuc still works)
- ✅ Clearer quoting (no nested confusion)
- ✅ Follows patterns in file (functions for complex ops)
- ✅ No breaking changes

---

## Risk Assessment

**Risk Level**: VERY LOW

**Rationale**:
1. Alias currently works (just fragile)
2. Change improves robustness
3. Easy to test (just one alias)
4. Backward compatible (keep alias name)
5. No external dependencies

**Potential Issues**:
- If someone relies on the exact quoting behavior (unlikely)

**Mitigation**:
- Keep alias pointing to function
- Test thoroughly
- Same end behavior

---

## Benefits

### 1. Maintainability ✅
- Function easier to modify
- Can add error checking
- Can add documentation
- Clearer code

### 2. Consistency ✅
- Matches other functions (MozCheckDiff, etc.)
- Follows established patterns
- Professional implementation

### 3. Robustness ✅
- No nested quote confusion
- Functions handle arguments properly
- Less fragile than aliases with complex quoting

### 4. Documentation ✅
- Function can have clear comments
- Intent is obvious
- Easier for new developers

---

## Implementation Notes

### Why Function Instead of Alias?

**Aliases**:
- Good for: Simple command shortcuts
- Bad for: Complex quoting, multiple operations

**Functions**:
- Good for: Complex operations, multiple steps, clear quoting
- Better for: Maintainability, documentation

**Current case**: Complex enough to warrant function

### Pattern in the File

The file already has:
- Simple aliases: `mb`, `mr`, `mfmt`
- Complex functions: `MozCheckDiff`, `UpdateCrate`, `W3CSpec`

**mfmtuc** should be a function (complex operation on uncommitted files)

---

## Backward Compatibility

### Alias Name: UNCHANGED ✅
- Still called `mfmtuc`
- Users don't need to change

### Behavior: UNCHANGED ✅
- Still formats uncommitted files
- Same end result

### Implementation: IMPROVED ✅
- More robust
- Better quoting
- Easier to maintain

---

## Related Patterns

### Similar Functions in Codebase:

**GitUncommit** (git/utils.sh):
```bash
function GitUncommit() {
  local cmd="$1"
  ...
  git ls-files ... -z | xargs -0 $cmd
}
```

**MozCheckDiff** (this file):
```bash
function MozCheckDiff() {
  git diff --name-only "$1" | while IFS= read -r file; do
    ./mach clang-format --path "$file"
  done
}
```

**Pattern**: Functions that operate on git files use function syntax

---

## Testing Methodology

1. **Syntax test**: bash -n mozilla/gecko/alias.sh
2. **Alias test**: Verify alias defined
3. **Function test**: Call function directly
4. **Integration test**: Use alias
5. **Backward compat**: Existing usage works

---

## Recommended Solution

**Convert to function** (Option 1):

```bash
# Format all uncommit files
function MozFormatUncommit() {
  GitUncommit './mach clang-format --path'
}
alias mfmtuc='MozFormatUncommit'
```

**Why**:
1. Clearer quoting (no nesting)
2. Matches patterns in file
3. Easy to document and extend
4. Backward compatible (alias still exists)
5. More robust and maintainable

This is the professional solution that follows best practices.
