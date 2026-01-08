# Testing Plan - Add File Existence Checks

## Item 5.1: Add file existence checks before operations

**File**: `setup.py`
**Impact**: MEDIUM-HIGH - Prevents crashes, improves error handling
**Priority**: 5 (Error Handling & Validation)

---

## The Problem

### Current Issues:

#### Issue 1: `os.path.samefile()` Without Existence Check (Line 209)

**Current code**:
```python
src = os.path.join(BASE_DIR, f)
if os.path.isfile(target):
    if os.path.samefile(src, target):  # CRASH if src doesn't exist!
        print_warning('{} is already linked!'.format(target))
        continue
```

**Problem**: If source file missing from repo, crashes with `OSError`

**Scenario**:
```python
# User accidentally deleted dot.bashrc from repo
# setup.py tries to check if ~/.bashrc is same as repo's dot.bashrc
# CRASH: OSError: [Errno 2] No such file or directory
```

#### Issue 2: `link()` Function Without Source Validation (Lines 32-38)

**Current code**:
```python
def link(source, target):
    if os.path.islink(target):
        print('unlink {}'.format(target))
        os.unlink(target)

    print('link {} to {}'.format(source, target))
    os.symlink(source, target)  # CRASH if source doesn't exist!
```

**Problem**: Creates symlink without checking source exists

**Scenario**:
```python
# Repository missing a file (e.g., dot.settings_linux)
# setup.py tries to symlink it
# Symlink created pointing to non-existent file (broken symlink)
# Later operations fail when trying to use the broken symlink
```

#### Issue 3: Reading git_config Without Verification (Line 244)

**Current code**:
```python
git_config = os.path.join(HOME_DIR, '.gitconfig')
if not os.path.isfile(git_config):
    # Create it with git config commands
    subprocess.call(['git', 'config', '--global', ...])

subprocess.call(['git', 'config', '--global', 'include.path', path])

# Show the current file:
with open(git_config, 'r') as f:  # CRASH if creation failed!
    content = f.read()
```

**Problem**: Assumes file exists after subprocess calls, doesn't verify

**Scenario**:
```python
# git config command fails (rare but possible)
# File not created
# open() crashes with FileNotFoundError
```

#### Issue 4: No Validation of git/config Path (Line 240)

**Current code**:
```python
path = os.path.join(BASE_DIR, 'git', 'config')
subprocess.call(['git', 'config', '--global', 'include.path', path])
```

**Problem**: Doesn't check if git/config exists before adding to git config

**Scenario**:
```python
# git/config missing from repository
# include.path points to non-existent file
# Git configuration broken
```

---

## The Solution

### Fix 1: Add Source Existence Check Before samefile

**Before**:
```python
if os.path.isfile(target):
    if os.path.samefile(src, target):
        print_warning('{} is already linked!'.format(target))
        continue
```

**After**:
```python
if os.path.isfile(target):
    # Check if source exists before comparing
    if not os.path.exists(src):
        print_error('Source file does not exist: {}'.format(src))
        print_error('Repository may be incomplete or corrupted')
        continue

    if os.path.samefile(src, target):
        print_warning('{} is already linked!'.format(target))
        continue
```

### Fix 2: Add Source Validation in link() Function

**Before**:
```python
def link(source, target):
    if os.path.islink(target):
        print('unlink {}'.format(target))
        os.unlink(target)

    print('link {} to {}'.format(source, target))
    os.symlink(source, target)
```

**After**:
```python
def link(source, target):
    # Validate source exists
    if not os.path.exists(source):
        print_error('Cannot create symlink: source does not exist')
        print_error('Source: {}'.format(source))
        return False

    if os.path.islink(target):
        print('unlink {}'.format(target))
        os.unlink(target)

    print('link {} to {}'.format(source, target))
    os.symlink(source, target)
    return True
```

### Fix 3: Verify git_config Exists Before Reading

**Before**:
```python
# Show the current file:
with open(git_config, 'r') as f:
    content = f.read()
    print_hint('{}:'.format(git_config))
    print(content)
    f.close()
```

**After**:
```python
# Show the current file if it exists:
if os.path.exists(git_config):
    with open(git_config, 'r') as f:
        content = f.read()
        print_hint('{}:'.format(git_config))
        print(content)
        f.close()
else:
    print_warning('Git config file not found: {}'.format(git_config))
    print_warning('Git configuration may not be complete')
```

### Fix 4: Validate git/config Exists

**Before**:
```python
path = os.path.join(BASE_DIR, 'git', 'config')
subprocess.call(['git', 'config', '--global', 'include.path', path])
```

**After**:
```python
path = os.path.join(BASE_DIR, 'git', 'config')
if not os.path.exists(path):
    print_error('Git config file not found: {}'.format(path))
    print_error('Cannot configure git include.path')
    return

subprocess.call(['git', 'config', '--global', 'include.path', path])
```

---

## Changes Required

### Summary:
1. Add source existence check before `os.path.samefile()` (line 209)
2. Add source validation in `link()` function (lines 32-38)
3. Add existence check before reading git_config (line 244)
4. Add validation of git/config path (line 240)

All changes add validation without changing successful code paths.

---

## Test Cases

### Test 1: Syntax Validation ✓
**Command**: `python3 -m py_compile setup.py`
**Expected**: No syntax errors

### Test 2: link() Function - Source Missing ✓
**Test**: Call link() with non-existent source
```python
link('/nonexistent/source', '/tmp/test_target')
```
**Expected**:
- Error message printed
- Function returns False
- No symlink created
- No crash

### Test 3: link() Function - Source Exists ✓
**Test**: Call link() with existing source
```python
link('/tmp/existing_file', '/tmp/test_target')
```
**Expected**:
- Symlink created successfully
- Function returns True
- Target points to source

### Test 4: bash_link() - Source Missing ✓
**Test**: Repository missing a dotfile
```python
# Temporarily rename dot.bashrc
# Run bash_link()
```
**Expected**:
- Error message about missing source
- Setup continues with other files
- No crash

### Test 5: bash_link() - samefile Check ✓
**Test**: Target exists and is already correct symlink
```python
# Create correct symlink first
# Run bash_link() again
```
**Expected**:
- Detects already linked
- Doesn't try to re-link
- No crash from samefile

### Test 6: git_init() - git/config Missing ✓
**Test**: Missing git/config file
```python
# Temporarily rename git/config
# Run git_init()
```
**Expected**:
- Error message about missing file
- Function returns early
- No broken git configuration

### Test 7: git_init() - Read After Create ✓
**Test**: Reading git_config after attempting to create
```python
# Normal flow - file should exist
# Run git_init()
```
**Expected**:
- File read successfully
- Content displayed
- No crash

### Test 8: git_init() - Read Fails ✓
**Test**: git_config doesn't exist after creation attempts
```python
# Mock subprocess to fail
# Run git_init()
```
**Expected**:
- Warning message
- Setup continues
- No crash

### Test 9: Integration Test - Normal Setup ✓
**Test**: Run full setup with all files present
```python
python3 setup.py
```
**Expected**:
- All files linked successfully
- All configurations applied
- No errors

### Test 10: Integration Test - Missing Files ✓
**Test**: Run setup with some files missing
```python
# Remove a non-critical file
python3 setup.py
```
**Expected**:
- Clear error messages
- Setup continues with available files
- No crashes
- User informed of missing files

---

## Success Criteria

- ✅ All syntax validation passes
- ✅ No crashes on missing files
- ✅ Clear error messages when files missing
- ✅ Setup continues gracefully (doesn't abort entirely)
- ✅ Backward compatible (normal operations unchanged)
- ✅ Returns False/early return for errors
- ✅ All tests pass

---

## Risk Assessment

**Risk Level**: LOW-MEDIUM

**Rationale**:
1. Adds validation only (improves robustness)
2. Doesn't change successful code paths
3. Makes errors explicit rather than crashing
4. Easy to test

**Potential Issues**:
1. If callers depend on link() not having return value
   - **Mitigation**: Check all callers, return value optional
2. Early returns might skip some setup steps
   - **Mitigation**: This is correct behavior (fail fast)

**Testing Strategy**:
- Test with missing files
- Test with corrupted repository
- Test normal operations unchanged
- Test error messages clear

---

## Benefits

### 1. Prevents Crashes ✅

**Before**: Cryptic OSError crashes
```python
OSError: [Errno 2] No such file or directory
Traceback (most recent call last):
  File "setup.py", line 209, in bash_link
    if os.path.samefile(src, target):
```

**After**: Clear error messages
```
ERROR: Source file does not exist: /path/to/dot.bashrc
ERROR: Repository may be incomplete or corrupted
```

### 2. Early Problem Detection ✅

**Before**: Broken symlinks created silently
**After**: Errors detected immediately with clear messages

### 3. Better User Experience ✅

**Before**: Setup crashes, user confused
**After**: Clear errors, setup continues where possible

### 4. Debugging Aid ✅

**Before**: Hard to diagnose why setup failed
**After**: Explicit messages about what's missing

### 5. Repository Validation ✅

**Before**: No indication if repository incomplete
**After**: Validates critical files exist

---

## Backward Compatibility

### Function Signatures:
- `link(source, target)`: Returns True/False (was None)
  - Callers can ignore return value (backward compatible)

### Behavior:
- Normal operations unchanged
- Only adds error handling for edge cases
- Makes implicit errors explicit

**Breaking Changes**: NONE ✅

---

## Edge Cases Handled

1. **Missing source file**: Clear error, continue
2. **Missing git/config**: Clear error, skip git config
3. **git config creation fails**: Warning, continue
4. **Broken symlink**: Detected and handled
5. **Repository incomplete**: User informed

---

## Implementation Notes

### Why Not Abort on Error?

**Design choice**: Continue with partial setup where possible

**Rationale**:
- Some files optional (e.g., Mozilla configs)
- User can fix and re-run
- Better than aborting entire setup

**Alternative**: Add `--strict` flag for abort-on-error behavior (future enhancement)

### Why Return Values?

Adding return values to `link()`:
- Enables error detection
- Allows callers to handle failures
- Optional (backward compatible)

---

## Related Items

### Facilitates:
- **Item 5.4**: Installation verification (can now check what failed)
- **Item 8.1**: Test suite (proper error handling testable)

### Blocked By:
- Item 5.2 ✅ (completed - append function now has validation)

---

## Conclusion

Adding file existence checks transforms setup.py from a fragile script that crashes on missing files into a robust installer that validates inputs, provides clear errors, and continues gracefully where possible.

**Key Achievement**: Replace cryptic crashes with clear, actionable error messages while maintaining backward compatibility.

**Pattern Established**: Validate all file operations before executing, fail fast with clear messages.

**Code Quality**: Improved from fragile (crashes on edge cases) to robust (handles errors gracefully).
