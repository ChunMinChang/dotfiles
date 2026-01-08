# Testing Plan - Add Error Exit Codes

## Item 5.3: Add error exit codes for silent failures

**File**: `setup.py` (multiple locations)
**Impact**: HIGH - Prevents silent failures, provides clear feedback
**Priority**: 5 (Error Handling & Validation)

---

## The Problem

### Current Behavior: Silent Failures

The setup script continues execution and reports "success" even when critical steps fail:

```bash
$ python3 setup.py
# Git not installed - prints error but continues
# Files can't be linked - prints warning but continues
# Mozilla tools fail - prints error but continues
Please run `$ source ~/.bashrc` to turn on the environment settings
$ echo $?
0    # EXIT CODE 0 = SUCCESS (WRONG!)
```

**User Impact**: Users think setup succeeded but dotfiles aren't actually configured.

---

## Silent Failure Points Identified

### 1. bash_link() - "Do nothing" (Line 231)

**Scenario**: Target file exists but isn't bashrc/zshrc

```python
if f == 'dot.bashrc' or f == 'dot.zshrc':
    # Append loader command (good)
    append_nonexistent_lines_to_file(target, [bash_load_command(src)])
else:
    print_warning('Do nothing.')  # SILENT FAILURE!
```

**Problem**: Files like `dot.settings_linux` can't be set up if `~/.settings_linux` already exists.

**Example**:
- User has old `~/.settings_linux` file
- setup.py can't replace it (file exists)
- Prints "Do nothing" and continues
- Old settings remain active (setup incomplete)

---

### 2. git_init() - Git not installed (Line 240)

```python
if not is_tool('git'):
    print_fail('Please install git first!')
    return  # Returns to main(), which continues!
```

**Problem**: main() doesn't know git_init() failed.

---

### 3. git_init() - git/config missing (Line 257)

```python
if not os.path.exists(path):
    print_error('Git config file not found: {}'.format(path))
    print_error('Cannot configure git include.path')
    return  # Silent failure!
```

**Problem**: Git configuration incomplete but setup continues.

---

### 4. Mozilla functions - Multiple failure points

**gecko_init() - dot.bashrc missing (Line 312)**:
```python
if not os.path.isfile(bashrc):
    print_fail('{} does not exist! Abort!'.format(bashrc))
    return  # Says "Abort" but doesn't abort!
```

**hg_init() - Mercurial not installed (Line 325)**:
```python
if not is_tool('hg'):
    error_messages.insert(0, 'Please install hg(mercurial) first!')
    print_fail(''.join(error_messages))
    return  # Silent failure!
```

**rust_init() - Cargo not set up (Line 362)**:
```python
if not os.path.isfile(cargo_env):
    error_messages.insert(0, '{} does not exist! Abort!'.format(cargo_env))
    print_fail(''.join(error_messages))
    return  # Silent failure!
```

**Problem**: Says "Abort" but setup continues as if nothing happened.

---

### 5. Unchecked Return Values

**append_nonexistent_lines_to_file()** returns False on error but callers ignore it:

```python
# Line 228 - bash_link()
append_nonexistent_lines_to_file(target, [bash_load_command(src)])
# No check! If this fails, error is silent.

# Lines 315, 334, 346, 364 - Mozilla functions
append_nonexistent_lines_to_file(bashrc, [bash_load_command(path)])
# No check! Silent failures.
```

**link()** returns False on error but mostly ignored:

```python
# Line 233 - bash_link()
link(src, target)  # No check!

# Line 307 - gecko_init()
link(path, machrc)  # No check!
```

---

### 6. main() - No failure tracking (Lines 367-375)

```python
def main(argv):
    dotfiles_link()     # Might fail
    bash_link()         # Might fail
    git_init()          # Might fail
    mozilla_init()      # Might fail

    # Always prints success message!
    print_hint('Please run `$ source ~/.bashrc` to turn on the environment settings')
    # Always exits with 0 (success)!
```

**Problem**: No tracking of which steps succeeded/failed.

---

## The Solution

### Design Goals

1. **Track failures**: Know which steps succeeded/failed
2. **Clear feedback**: Show summary of results
3. **Proper exit codes**: Exit 0 only if fully successful
4. **User guidance**: Tell user what to fix
5. **Backward compatible**: Don't break existing behavior

---

### Solution Architecture

#### 1. Add Return Values to Functions

All setup functions return boolean:
- `True` = Success
- `False` = Failure

```python
def dotfiles_link():
    # ... existing code ...
    return True  # or False if error

def bash_link():
    failures = []
    # ... track failures ...
    return len(failures) == 0

def git_init():
    # ... existing code ...
    return True  # or False if error
```

#### 2. Track Failures in main()

```python
def main(argv):
    results = {
        'dotfiles': dotfiles_link(),
        'bash': bash_link(),
        'git': git_init(),
        'mozilla': mozilla_init()
    }

    # Show summary
    show_setup_summary(results)

    # Exit with proper code
    if all(results.values()):
        print_hint('Please run `$ source ~/.bashrc` to turn on the environment settings')
        return 0
    else:
        return 1
```

#### 3. Check Return Values

```python
# Check append_nonexistent_lines_to_file
if not append_nonexistent_lines_to_file(target, [bash_load_command(src)]):
    errors.append('Failed to append to {}'.format(target))

# Check link
if not link(src, target):
    errors.append('Failed to link {}'.format(src))
```

#### 4. Handle "Do nothing" Case

Provide user with options instead of silent skip:

```python
else:
    # Target exists but isn't bashrc/zshrc
    print_warning('{} already exists!'.format(target))
    print('Options:')
    print('  1. Remove {} and re-run setup'.format(target))
    print('  2. Manually replace with symlink: ln -sf {} {}'.format(src, target))
    print('  3. Keep existing file (skip)')
    # Don't count as failure (user can decide)
```

#### 5. Exit Codes

```python
if __name__ == '__main__':
    try:
        exit_code = main(sys.argv)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print('abort')
        sys.exit(130)  # Standard exit code for Ctrl+C
```

---

## Changes Required

### Summary

1. **dotfiles_link()**: Add return value, return False on link failure
2. **bash_link()**: Track failures, check return values, return success/failure
3. **git_init()**: Return False on errors instead of bare return
4. **mozilla_init()**: Track sub-function failures, return success/failure
5. **gecko_init(), hg_init(), tools_init(), rust_init()**: Add return values
6. **main()**: Track results, show summary, return proper exit code
7. **Line 231**: Replace "Do nothing" with helpful guidance
8. **__main__**: Use sys.exit() with exit code from main()

**Total**: ~8 functions modified, ~50 lines added

---

## Test Cases

### Test 1: Syntax Validation
**Command**: `python3 -m py_compile setup.py`
**Expected**: No syntax errors

### Test 2: Full Success - Normal Operation
**Scenario**: All files present, no conflicts
**Expected**:
- All steps succeed
- Success message printed
- Exit code 0

### Test 3: bash_link() - File Conflict
**Scenario**: `~/.settings_linux` already exists
**Expected**:
- Warning printed with options (not "Do nothing")
- Clear guidance on how to proceed
- Setup continues with other files
- Exit code 0 (user decision, not failure)

### Test 4: git_init() - Git not installed
**Scenario**: git command not available
**Expected**:
- Error message printed
- git_init() returns False
- main() tracks failure
- Summary shows git setup failed
- Exit code 1

### Test 5: git_init() - git/config missing
**Scenario**: Repository missing git/config file
**Expected**:
- Error message printed
- git_init() returns False
- Summary shows git setup failed
- Exit code 1

### Test 6: Mozilla - hg not installed
**Scenario**: Run `python3 setup.py --mozilla hg` without Mercurial
**Expected**:
- Error message printed
- hg_init() returns False
- mozilla_init() returns False
- Summary shows Mozilla setup failed
- Exit code 1

### Test 7: link() Failure Tracked
**Scenario**: Source file missing (caught by Item 5.1)
**Expected**:
- link() returns False
- Caller tracks error
- Summary shows what failed
- Exit code 1

### Test 8: append_nonexistent_lines_to_file() Failure Tracked
**Scenario**: Target file not writable (caught by Item 5.2)
**Expected**:
- Function returns False
- Caller tracks error
- Summary shows what failed
- Exit code 1

### Test 9: Partial Success
**Scenario**: dotfiles and bash succeed, git fails
**Expected**:
- Clear summary: "✓ dotfiles ✓ bash ✗ git"
- Shows what succeeded and what failed
- Guidance on fixing git issue
- Exit code 1 (not fully successful)

### Test 10: Keyboard Interrupt
**Scenario**: Press Ctrl+C during setup
**Expected**:
- Prints "abort"
- Exit code 130 (standard for SIGINT)

### Test 11: Integration - Clean Install
**Test**: Run full setup on clean system
**Expected**:
- All steps complete successfully
- Summary shows all green
- "Please run $ source ~/.bashrc" printed
- Exit code 0

### Test 12: Integration - Broken Repository
**Test**: Run setup with missing files
**Expected**:
- Clear errors for each missing file
- Summary shows what failed
- Guidance on fixing (git pull, etc.)
- Exit code 1

---

## Success Criteria

- ✅ All syntax validation passes
- ✅ Functions return True/False based on success
- ✅ main() tracks all results
- ✅ Clear summary shown at end
- ✅ Exit code 0 only on full success
- ✅ Exit code 1 on any failure
- ✅ Exit code 130 on Ctrl+C
- ✅ "Do nothing" replaced with helpful guidance
- ✅ Return values checked for link() and append functions
- ✅ Backward compatible (normal operations unchanged)
- ✅ All tests pass

---

## Risk Assessment

**Risk Level**: MEDIUM

**Rationale**:
1. Adds return values (low risk - callers optional)
2. Changes exit codes (medium risk - scripts might depend on always-0)
3. Changes user-visible output (low risk - improvements)
4. Adds tracking logic (low risk - no change to operations)

**Potential Issues**:
1. Scripts that depend on exit code 0 will now see exit code 1 on failure
   - **Mitigation**: This is CORRECT behavior (currently lying about success)
2. Summary output might surprise users
   - **Mitigation**: More information is better
3. More verbose output
   - **Mitigation**: Can add --quiet flag later if needed

**Testing Strategy**:
- Test normal success case (should be unchanged)
- Test each failure mode individually
- Test partial failures
- Test with automated scripts

---

## Benefits

### 1. No More Silent Failures ✅

**Before**: "Setup complete!" (but git failed)
**After**: "Setup completed with errors: git setup failed"

### 2. Proper Exit Codes ✅

**Before**:
```bash
$ python3 setup.py && echo "Success!"
# Prints "Success!" even if setup failed
```

**After**:
```bash
$ python3 setup.py && echo "Success!"
# Only prints "Success!" if setup actually succeeded
```

### 3. Clear Feedback ✅

**Before**: Errors scattered in output, hard to know what failed
**After**: Summary at end shows exactly what succeeded/failed

### 4. Automation-Friendly ✅

Scripts can now check exit code:
```bash
if python3 setup.py; then
    source ~/.bashrc
    echo "Dotfiles activated!"
else
    echo "Setup failed - check errors above"
    exit 1
fi
```

### 5. Better User Guidance ✅

**Before**: "Do nothing." (What should I do?)
**After**: Clear options for resolving conflicts

---

## Implementation Plan

### Phase 1: Add Return Values (15 functions)
1. dotfiles_link() - return True/False
2. bash_link() - track errors, return True/False
3. git_init() - return True/False
4. mozilla_init() - track sub-function results
5. gecko_init(), hg_init(), tools_init(), rust_init() - return True/False

### Phase 2: Track Failures (1 function)
6. main() - collect results from all functions

### Phase 3: Show Summary (1 new function)
7. show_setup_summary() - display results, provide guidance

### Phase 4: Fix Exit Codes (1 location)
8. __main__ - sys.exit() with proper code

### Phase 5: Fix "Do nothing" (1 location)
9. Line 231 - Replace with helpful guidance

### Phase 6: Check Return Values (6 locations)
10. Lines 228, 233, 307, 315, 334, 346, 364 - Check and track errors

---

## Backward Compatibility

### Function Signatures
- All functions now return True/False
- Callers can ignore return value (optional)
- Existing behavior unchanged (operations still happen)

### Exit Codes
- **Breaking change**: Now exits with 1 on failure (was 0)
- **Justification**: Previous behavior was a bug (lying about success)
- **Impact**: Scripts that depend on always-0 will now correctly detect failures

### Output
- Additional summary at end
- More informative (not breaking)

---

## Related Items

### Unblocks
- **Item 5.4**: Installation verification (can now detect what failed)
- **Item 8.1**: Test suite (proper error codes enable better testing)

### Depends On
- Item 5.1 ✅ (file existence checks - provides foundation)
- Item 5.2 ✅ (append function fix - return values work correctly)

---

## Example Output

### Before (Current)
```bash
$ python3 setup.py
bash startup scripts
--------------------
WARNING: /home/user/.settings_linux already exists!
WARNING: Do nothing.
git settings
--------------------
ERROR: Please install git first!
Please run `$ source ~/.bashrc` to turn on the environment settings
$ echo $?
0
```

### After (Fixed)
```bash
$ python3 setup.py
bash startup scripts
--------------------
WARNING: /home/user/.settings_linux already exists!
Options:
  1. Remove /home/user/.settings_linux and re-run setup
  2. Manually replace with symlink: ln -sf /home/user/dotfiles/dot.settings_linux /home/user/.settings_linux
  3. Keep existing file (skip)

git settings
--------------------
ERROR: Please install git first!

===========================================
Setup Summary
===========================================
✓ Dotfiles link: SUCCESS
✓ Bash configuration: SUCCESS (1 file skipped - user choice)
✗ Git configuration: FAILED - git not installed
⊘ Mozilla toolkit: SKIPPED

Action Required:
  - Install git and re-run setup.py

Setup completed with errors. Fix the issues above and re-run.
$ echo $?
1
```

---

## Conclusion

Adding error exit codes transforms setup.py from a script that silently fails into a robust installer that:
- Tracks all operations
- Reports clear results
- Exits with proper codes
- Guides users to fix issues
- Enables automation

**Key Achievement**: Replace silent failures with explicit tracking and proper exit codes.

**Pattern Established**: Every operation tracked, every failure reported, every error code meaningful.

**Code Quality**: Improved from misleading (always exits 0) to honest (proper error reporting).
