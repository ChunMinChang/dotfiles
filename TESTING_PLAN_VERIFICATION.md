# Testing Plan - Add Installation Verification

## Item 5.4: Add installation verification step

**File**: `setup.py` (new function + integration)
**Impact**: HIGH - Validates setup actually worked
**Priority**: 5 (Error Handling & Validation)

---

## The Problem

### Current Behavior: No Verification

Setup completes and reports success, but there's no verification that:
- Symlinks were created correctly
- Symlinks point to valid files
- Files are readable
- Configuration can be loaded without errors

**User Impact**: User might think setup succeeded but have broken environment.

**Example**:
```bash
$ python3 setup.py
==================================================
Setup Summary
==================================================
✓ Dotfiles: SUCCESS
✓ Bash: SUCCESS
✓ Git: SUCCESS
⊘ Mozilla: SKIPPED

All steps completed successfully!
Please run `$ source ~/.bashrc` to turn on the environment settings

$ source ~/.bashrc
bash: /home/user/.dotfiles/utils.sh: Permission denied
# Setup said success but environment is broken!
```

---

## Silent Failure Scenarios

### Scenario 1: Broken Symlinks

**Cause**: File deleted after symlink created (race condition)

```bash
# Setup creates symlink
ln -s /home/user/dotfiles/dot.bashrc ~/.bashrc

# File gets deleted somehow
rm /home/user/dotfiles/dot.bashrc

# Symlink exists but is broken!
$ ls -l ~/.bashrc
lrwxrwxrwx ... ~/.bashrc -> /home/user/dotfiles/dot.bashrc (broken)

$ source ~/.bashrc
bash: /home/user/dotfiles/dot.bashrc: No such file or directory
```

### Scenario 2: Permission Issues

**Cause**: Files not readable due to permissions

```bash
# Setup creates symlink
ln -s /home/user/dotfiles/dot.bashrc ~/.bashrc

# Permissions wrong
chmod 000 /home/user/dotfiles/dot.bashrc

# Symlink valid but file unreadable!
$ source ~/.bashrc
bash: /home/user/dotfiles/dot.bashrc: Permission denied
```

### Scenario 3: Syntax Errors in Config Files

**Cause**: User edited file, introduced syntax error

```bash
# dot.bashrc has syntax error
$ source ~/.bashrc
bash: /home/user/dotfiles/dot.bashrc: line 42: syntax error near unexpected token `fi'
```

### Scenario 4: Missing Dependencies

**Cause**: Config files reference files that don't exist

```bash
# dot.bashrc tries to source utils.sh
source ~/.dotfiles/utils.sh

# But utils.sh is missing
bash: /home/user/.dotfiles/utils.sh: No such file or directory
```

### Scenario 5: Circular Symlinks

**Cause**: Symlink points to itself or circular chain

```bash
ln -s ~/.bashrc ~/.bashrc  # Points to itself!
$ source ~/.bashrc
bash: /home/user/.bashrc: Too many levels of symbolic links
```

---

## The Solution

### Design Goals

1. **Verify symlinks**: Check all created symlinks are valid
2. **Check readability**: Ensure files can be read
3. **Test sourcing**: Verify configs load without errors
4. **Report issues**: Clear feedback on what's broken
5. **Optional verification**: Don't fail on optional components
6. **Fast execution**: Complete in < 1 second

---

## Verification Strategy

### Phase 1: Symlink Validation

Verify all symlinks created by setup:

```python
def verify_symlinks():
    """Verify all symlinks created during setup."""
    symlinks_to_check = [
        ('~/.dotfiles', BASE_DIR),
        ('~/.bashrc', 'dot.bashrc'),  # Or appended loader
        ('~/.settings_linux', 'dot.settings_linux'),  # Platform specific
        # ... more symlinks
    ]

    issues = []
    for target, expected_source in symlinks_to_check:
        target_path = os.path.expanduser(target)

        # Check symlink exists
        if not os.path.lexists(target_path):
            issues.append(f'{target} does not exist')
            continue

        # Check it's a symlink (or regular file with loader for bashrc)
        if os.path.islink(target_path):
            # Verify symlink points to correct source
            actual_source = os.readlink(target_path)
            # Check if broken
            if not os.path.exists(target_path):
                issues.append(f'{target} is a broken symlink (points to {actual_source})')
            # Check if readable
            elif not os.access(target_path, os.R_OK):
                issues.append(f'{target} exists but is not readable')

    return issues
```

### Phase 2: File Readability Check

```python
def verify_file_readability():
    """Verify critical files are readable."""
    files_to_check = [
        os.path.join(BASE_DIR, 'dot.bashrc'),
        os.path.join(BASE_DIR, 'utils.sh'),
        os.path.join(BASE_DIR, 'git', 'utils.sh'),
        os.path.join(BASE_DIR, 'git', 'config'),
        # Platform-specific files
    ]

    issues = []
    for filepath in files_to_check:
        if not os.path.exists(filepath):
            issues.append(f'{filepath} is missing')
        elif not os.access(filepath, os.R_OK):
            issues.append(f'{filepath} is not readable')

    return issues
```

### Phase 3: Basic Syntax Check (Bash Files)

```python
def verify_bash_syntax():
    """Verify bash files have valid syntax."""
    bash_files = [
        os.path.join(BASE_DIR, 'dot.bashrc'),
        os.path.join(BASE_DIR, 'utils.sh'),
        os.path.join(BASE_DIR, 'git', 'utils.sh'),
        os.path.join(BASE_DIR, 'dot.settings_linux'),
    ]

    issues = []
    for filepath in bash_files:
        if not os.path.exists(filepath):
            continue  # Already reported in readability check

        # Use bash -n to check syntax without executing
        result = subprocess.run(
            ['bash', '-n', filepath],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            issues.append(f'{filepath} has syntax errors: {result.stderr.strip()}')

    return issues
```

### Phase 4: Git Configuration Check

```python
def verify_git_config():
    """Verify git configuration is valid."""
    issues = []

    # Check git config file exists and is included
    git_config_path = os.path.join(BASE_DIR, 'git', 'config')
    if not os.path.exists(git_config_path):
        issues.append('git/config file missing')
        return issues

    # Check if included in global config
    result = subprocess.run(
        ['git', 'config', '--global', '--get', 'include.path'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        issues.append('git include.path not configured')
    elif git_config_path not in result.stdout:
        issues.append(f'git include.path not pointing to {git_config_path}')

    return issues
```

### Phase 5: Integration Function

```python
def verify_installation():
    """
    Verify installation completed successfully.

    Returns:
        (bool, list): (success, list of issues)
    """
    print_installing_title('Verifying Installation')

    all_issues = []

    # Phase 1: Symlinks
    print('Checking symlinks...')
    issues = verify_symlinks()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_warning(issue)
    else:
        print(colors.OK + '✓ All symlinks valid' + colors.END)

    # Phase 2: File readability
    print('Checking file readability...')
    issues = verify_file_readability()
    if issues:
        all_issues.extend(issues)
        for issue in issues:
            print_error(issue)
    else:
        print(colors.OK + '✓ All files readable' + colors.END)

    # Phase 3: Bash syntax
    if is_tool('bash'):
        print('Checking bash syntax...')
        issues = verify_bash_syntax()
        if issues:
            all_issues.extend(issues)
            for issue in issues:
                print_error(issue)
        else:
            print(colors.OK + '✓ Bash files syntax valid' + colors.END)

    # Phase 4: Git config
    if is_tool('git'):
        print('Checking git configuration...')
        issues = verify_git_config()
        if issues:
            all_issues.extend(issues)
            for issue in issues:
                print_warning(issue)
        else:
            print(colors.OK + '✓ Git configuration valid' + colors.END)

    # Summary
    if all_issues:
        print('\n' + colors.FAIL + 'Verification found {} issue(s):'.format(len(all_issues)) + colors.END)
        for issue in all_issues:
            print('  - ' + issue)
        return False, all_issues
    else:
        print('\n' + colors.OK + '✓ Installation verification passed!' + colors.END)
        return True, []
```

### Integration with main()

```python
def main(argv):
    results = {
        'dotfiles': dotfiles_link(),
        'bash': bash_link(),
        'git': git_init(),
        'mozilla': mozilla_init()
    }

    show_setup_summary(results)

    # Only verify if setup succeeded
    if all(r is not False for r in results.values()):
        # Run verification
        verification_passed, issues = verify_installation()

        if verification_passed:
            print_hint('Please run `$ source ~/.bashrc` to turn on the environment settings')
            return 0
        else:
            print_error('Installation verification failed!')
            print_error('Fix the issues above and re-run setup.py')
            return 1
    else:
        # Setup failed, skip verification
        return 1
```

---

## Changes Required

### Summary

1. **verify_symlinks()**: New function - check all symlinks valid
2. **verify_file_readability()**: New function - check files readable
3. **verify_bash_syntax()**: New function - check bash syntax with `bash -n`
4. **verify_git_config()**: New function - check git configuration
5. **verify_installation()**: New function - orchestrate all checks
6. **main()**: Call verify_installation() after setup if successful

**Total**: 5 new functions, ~150 lines

---

## Test Cases

### Test 1: Syntax Validation
**Command**: `python3 -m py_compile setup.py`
**Expected**: No syntax errors

### Test 2: Verification Functions Exist
**Test**: Check all verification functions defined
**Expected**:
- verify_symlinks() exists
- verify_file_readability() exists
- verify_bash_syntax() exists
- verify_git_config() exists
- verify_installation() exists

### Test 3: Normal Setup - All Valid
**Scenario**: Clean setup, everything works
**Expected**:
- All symlinks valid ✓
- All files readable ✓
- Bash files syntax valid ✓
- Git configuration valid ✓
- Verification passed
- Exit code 0

### Test 4: Broken Symlink Detection
**Scenario**: Create broken symlink
**Expected**:
- Detects broken symlink
- Reports issue clearly
- Verification fails
- Exit code 1

### Test 5: Missing File Detection
**Scenario**: Delete a critical file after setup
**Expected**:
- Detects missing file
- Reports which file
- Verification fails
- Exit code 1

### Test 6: Permission Issue Detection
**Scenario**: Make file unreadable
**Expected**:
- Detects permission issue
- Reports which file
- Verification fails
- Exit code 1

### Test 7: Bash Syntax Error Detection
**Scenario**: Introduce syntax error in bash file
**Expected**:
- Detects syntax error
- Shows bash error message
- Verification fails
- Exit code 1

### Test 8: Git Config Missing
**Scenario**: Git include.path not set
**Expected**:
- Detects missing git config
- Reports issue
- Verification fails
- Exit code 1

### Test 9: Setup Failed - Skip Verification
**Scenario**: Setup fails (e.g., git not installed)
**Expected**:
- Shows setup summary (git failed)
- Skips verification (no point if setup failed)
- Exit code 1

### Test 10: Partial Issues - Non-Critical
**Scenario**: Optional component issue (e.g., Mozilla tools)
**Expected**:
- Reports issue as warning
- Verification warns but doesn't fail
- Exit code 0 (if only optional components)

### Test 11: Platform-Specific Files
**Scenario**: On Linux, check dot.settings_linux
**Expected**:
- Checks correct platform files
- Skips macOS-specific files
- Verification accurate

### Test 12: Integration - Full Flow
**Test**: Run setup.py from scratch
**Expected**:
- Setup runs
- Summary shows results
- Verification runs automatically
- Clear pass/fail indication
- Proper exit code

---

## Success Criteria

- ✅ All syntax validation passes
- ✅ 5 verification functions implemented
- ✅ main() calls verify_installation()
- ✅ Detects broken symlinks
- ✅ Detects missing files
- ✅ Detects permission issues
- ✅ Checks bash syntax with `bash -n`
- ✅ Verifies git configuration
- ✅ Clear pass/fail feedback
- ✅ Proper exit codes
- ✅ All tests pass

---

## Risk Assessment

**Risk Level**: LOW-MEDIUM

**Rationale**:
1. Verification is read-only (no destructive operations)
2. Only runs after setup succeeds
3. Uses safe subprocess calls
4. No change to setup logic (only adds verification)

**Potential Issues**:
1. bash -n might fail on complex scripts
   - **Mitigation**: Only checks syntax, not execution
2. Platform-specific checks might be tricky
   - **Mitigation**: Use platform.system() to filter
3. Might slow down setup
   - **Mitigation**: Fast checks, < 1 second total
4. False positives on edge cases
   - **Mitigation**: Careful testing, clear error messages

**Testing Strategy**:
- Test with valid setup (all checks pass)
- Test with each failure mode individually
- Test platform-specific behavior
- Test performance (should be fast)

---

## Benefits

### 1. Catches Installation Issues ✅

**Before**: Setup says success but environment broken

**After**: Verification catches issues immediately

### 2. Clear Feedback ✅

**Before**: User discovers problems when trying to use environment

**After**: User knows immediately if something is wrong

### 3. Better Debugging ✅

**Before**: Hard to diagnose why environment doesn't work

**After**: Verification pinpoints exact issue

### 4. Confidence ✅

**Before**: User unsure if setup actually worked

**After**: Explicit verification confirms everything works

### 5. Catches Race Conditions ✅

**Before**: File deleted between setup steps - silent failure

**After**: Verification detects missing files

---

## Implementation Plan

### Phase 1: Verification Functions (4 functions)
1. verify_symlinks() - check symlinks valid
2. verify_file_readability() - check files readable
3. verify_bash_syntax() - check bash files with bash -n
4. verify_git_config() - check git configuration

### Phase 2: Orchestration (1 function)
5. verify_installation() - run all checks, report results

### Phase 3: Integration (1 modification)
6. main() - call verify_installation() after setup

### Phase 4: Platform Detection
7. Add platform-specific file lists for verification

---

## Backward Compatibility

### Exit Codes
- No change to setup exit codes
- Verification adds another failure point
- Only runs if setup succeeded

### Behavior
- Verification is new feature (no old behavior)
- No breaking changes
- Only adds confidence to setup process

**Breaking Changes**: NONE ✅

---

## Example Output

### Success Case
```bash
$ python3 setup.py
dotfile path
--------------------
link /home/user/dotfiles to /home/user/.dotfiles

bash startup scripts
--------------------
link /home/user/dotfiles/dot.bashrc to /home/user/.bashrc
link /home/user/dotfiles/dot.settings_linux to /home/user/.settings_linux

git settings
--------------------
Git config included successfully

==================================================
Setup Summary
==================================================
✓ Dotfiles: SUCCESS
✓ Bash: SUCCESS
✓ Git: SUCCESS
⊘ Mozilla: SKIPPED

All steps completed successfully!

Verifying Installation
--------------------
Checking symlinks...
✓ All symlinks valid
Checking file readability...
✓ All files readable
Checking bash syntax...
✓ Bash files syntax valid
Checking git configuration...
✓ Git configuration valid

✓ Installation verification passed!

Please run `$ source ~/.bashrc` to turn on the environment settings
$ echo $?
0
```

### Failure Case
```bash
$ python3 setup.py
[... setup output ...]

==================================================
Setup Summary
==================================================
✓ Dotfiles: SUCCESS
✓ Bash: SUCCESS
✓ Git: SUCCESS
⊘ Mozilla: SKIPPED

All steps completed successfully!

Verifying Installation
--------------------
Checking symlinks...
WARNING: /home/user/.settings_linux is a broken symlink (points to /home/user/dotfiles/dot.settings_linux)
Checking file readability...
ERROR: /home/user/dotfiles/utils.sh is not readable
Checking bash syntax...
ERROR: /home/user/dotfiles/dot.bashrc has syntax errors: line 42: syntax error near unexpected token `fi'
Checking git configuration...
✓ Git configuration valid

Verification found 3 issue(s):
  - /home/user/.settings_linux is a broken symlink (points to /home/user/dotfiles/dot.settings_linux)
  - /home/user/dotfiles/utils.sh is not readable
  - /home/user/dotfiles/dot.bashrc has syntax errors: line 42: syntax error near unexpected token `fi'

ERROR: Installation verification failed!
ERROR: Fix the issues above and re-run setup.py
$ echo $?
1
```

---

## Related Items

### Unblocks
- **Item 5.5**: Rollback mechanism (verification helps track what to rollback)
- **Item 8.1**: Test suite (can test verification logic)

### Depends On
- Item 5.1 ✅ (file existence checks)
- Item 5.2 ✅ (append function working correctly)
- Item 5.3 ✅ (error exit codes for tracking)

---

## Conclusion

Adding installation verification transforms setup.py from "hope it worked" to "know it worked":
- Explicit validation of all critical components
- Clear feedback on what's broken
- Catches issues immediately
- Provides confidence in setup process

**Key Achievement**: Replace assumptions with explicit verification.

**Pattern Established**: Trust but verify - always check critical operations succeeded.

**Code Quality**: Improved from "best effort" to "verified correct".
