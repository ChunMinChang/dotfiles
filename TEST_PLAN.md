# Dotfiles Repository - Test Plan

Generated: 2026-01-07

This document provides test plans for all improvements made to the dotfiles repository, ensuring changes don't break existing functionality.

---

## Table of Contents
1. [Testing Strategy](#testing-strategy)
2. [Test Plan for Completed Fixes](#test-plan-for-completed-fixes)
3. [Test Plan for Future Fixes](#test-plan-for-future-fixes)
4. [Cross-Platform Testing](#cross-platform-testing)
5. [Automated Testing Setup](#automated-testing-setup)

---

## Testing Strategy

### General Approach
- **Test in a safe environment**: Use a test user account or VM
- **Backup first**: Copy critical files (~/.bashrc, ~/.gitconfig, etc.) before testing
- **Test incrementally**: Test each fix individually before moving to the next
- **Test both install and uninstall**: Ensure both directions work correctly
- **Test edge cases**: Spaces in paths, missing files, wrong permissions, etc.

### Test Environment Setup
```bash
# Create a test directory structure
mkdir -p ~/dotfiles-test-env
cd ~/dotfiles-test-env

# Clone or copy the dotfiles repo
git clone /home/cm/dotfiles dotfiles-test
cd dotfiles-test

# Create test files with edge cases
mkdir -p "test path with spaces"
touch "test file with spaces.txt"
```

---

## Test Plan for Completed Fixes

### ✅ Fix 1.2: Fragile File Path Handling in uninstall.sh

**Files Changed**: `uninstall.sh` (lines 32-47, 56-57, 60-69, 75-90, 97-111)

**Changes Made**:
- Replaced `ls -l | awk` with `readlink -f`
- Fixed script directory detection with `$(dirname "$0")`
- Added symlink validation before reading
- Quoted all variable expansions
- Improved error messages

#### Test Case 1.2.1: Normal Symlink Uninstall
**Objective**: Verify uninstall works with standard symlinks

**Setup**:
```bash
# First run setup.py to create symlinks
cd /home/cm/dotfiles
python setup.py

# Verify symlinks were created
ls -la ~/.dotfiles
ls -la ~/.bashrc
ls -la ~/.mozbuild/machrc 2>/dev/null || echo "machrc not present (ok if not using Mozilla)"
```

**Test Steps**:
1. Run `bash uninstall.sh` from the dotfiles directory
2. Check output for "Unlink" messages
3. Verify symlinks are removed: `ls -la ~/.bashrc ~/.dotfiles`
4. Check that original dotfiles repo files still exist

**Expected Results**:
- Script completes without errors
- Symlinks are removed
- Original files in repo are untouched
- Clear status messages for each operation

**Actual Results**: _[To be filled during testing]_

---

#### Test Case 1.2.2: Run from Different Directory
**Objective**: Verify script works when run from outside repo directory

**Setup**:
```bash
cd /home/cm/dotfiles
python setup.py  # Create symlinks
cd ~  # Change to home directory
```

**Test Steps**:
1. Run `bash dotfiles/uninstall.sh` (or wherever repo is located)
2. Verify script correctly locates dot.bashrc and other files

**Expected Results**:
- Script finds files relative to its own location, not pwd
- `SCRIPT_DIR` correctly points to repo location
- All operations succeed

**Actual Results**: _[To be filled during testing]_

---

#### Test Case 1.2.3: Paths with Spaces
**Objective**: Verify handling of filenames/paths with spaces

**Setup**:
```bash
# Create test directory with spaces
mkdir -p ~/test\ dotfiles
cp -r /home/cm/dotfiles/* ~/test\ dotfiles/

# Modify uninstall.sh temporarily to use test paths
# (Or test with actual paths if safe)
```

**Test Steps**:
1. Run uninstall.sh from directory with spaces
2. Check that all path operations work correctly
3. Verify no "No such file or directory" errors from unquoted variables

**Expected Results**:
- All variables are properly quoted
- No word-splitting errors
- Operations complete successfully

**Actual Results**: _[To be filled during testing]_

---

#### Test Case 1.2.4: Non-Existent Files
**Objective**: Verify graceful handling when files don't exist

**Setup**:
```bash
# Ensure machrc doesn't exist
rm -f ~/.mozbuild/machrc
```

**Test Steps**:
1. Run `bash uninstall.sh`
2. Check output when machrc doesn't exist

**Expected Results**:
- Script prints "does not exist" message
- No errors or failures
- Script continues to other operations

**Actual Results**: _[To be filled during testing]_

---

#### Test Case 1.2.5: Regular File Instead of Symlink
**Objective**: Verify handling when file is regular file, not symlink

**Setup**:
```bash
# Remove symlink and create regular file
rm ~/.dotfiles
mkdir ~/.dotfiles
```

**Test Steps**:
1. Run `bash uninstall.sh`
2. Check handling of non-symlink .dotfiles

**Expected Results**:
- Script detects it's not a symlink
- Prints "is not a symlink, stay unchanged"
- Doesn't try to unlink it

**Actual Results**: _[To be filled during testing]_

---

#### Test Case 1.2.6: Symlink to Wrong Target
**Objective**: Verify handling when symlink points elsewhere

**Setup**:
```bash
# Create symlink to different location
rm ~/.dotfiles
ln -s /tmp/fake-dotfiles ~/.dotfiles
```

**Test Steps**:
1. Run `bash uninstall.sh`
2. Check that it detects wrong target

**Expected Results**:
- Script reads symlink with readlink
- Compares to expected path
- Prints "stay unchanged" message
- Doesn't remove the symlink

**Actual Results**: _[To be filled during testing]_

---

#### Test Case 1.2.7: readlink Availability
**Objective**: Verify readlink command exists on target systems

**Test Steps**:
```bash
# Check readlink is available
which readlink
readlink --version

# Test on macOS (if available)
# Test on various Linux distros
```

**Expected Results**:
- readlink available on Linux
- readlink available on macOS
- `readlink -f` supported (note: macOS older versions might not support -f)

**Known Issues**:
- macOS readlink may not support `-f` flag on older versions
- Alternative: Use `readlink` without `-f` or use `greadlink` from coreutils

**Mitigation**: _[To be determined if issue found]_

**Actual Results (2026-01-07)**:
- ✅ readlink available: GNU coreutils 9.4
- ✅ `readlink -f` works correctly
- ✅ Symlink resolution tested: `/tmp/test-readlink/link.txt` → `/tmp/test-readlink/target.txt`
- ✅ `[ -L ]` check works correctly for detecting symlinks
- ⚠️  **macOS testing pending** - May need fallback for older macOS without `-f` support

---

#### Test Case 1.2.8: Syntax Validation
**Objective**: Verify shell script has no syntax errors

**Test Steps**:
```bash
# Check bash syntax
bash -n uninstall.sh

# Check with shellcheck if available
shellcheck uninstall.sh
```

**Expected Results**:
- No syntax errors from bash -n
- Shellcheck passes or only shows style warnings

**Actual Results (2026-01-07)**:
- ✅ bash -n passed (no syntax errors)
- ⚠️  shellcheck not installed on system (can be added later)
- ✅ Script directory detection tested and working
- ✅ File location detection verified: `dot.bashrc` found correctly

---

## Test Plan for Future Fixes

### 🔜 Fix 1.1: Dangerous eval Usage in uninstall.sh

**Risk Level**: HIGH (Security issue)

#### Test Case 1.1.1: Source Working Correctly
**Objective**: Verify if source command actually works or fails

**Test Steps**:
```bash
# Test sourcing dot.bashrc
source /home/cm/dotfiles/dot.bashrc
echo "Exit code: $?"
echo "PLATFORM variable: $PLATFORM"
echo "DOTFILES variable: $DOTFILES"
```

**Expected Results**: Determine if source succeeds or fails and why

#### Test Case 1.1.2: Remove eval, Test Alternatives
**Test Steps**:
1. Comment out eval line
2. Test if PLATFORM variable gets set by source
3. If not, investigate why source appears to fail
4. Fix root cause instead of using eval

---

### 🔜 Fix 1.3: Git Status Parsing in git/utils.sh

**Risk Level**: HIGH (Data loss risk)

#### Test Case 1.3.1: Filenames with Spaces
**Setup**:
```bash
cd /tmp/test-repo
git init
echo "test" > "file with spaces.txt"
git add "file with spaces.txt"
echo "modified" >> "file with spaces.txt"
```

**Test Steps**:
1. Run GitUncommit command
2. Verify it correctly handles the filename

#### Test Case 1.3.2: Renamed Files
**Setup**:
```bash
git mv oldfile newfile
git status --porcelain  # Should show "R  oldfile -> newfile"
```

**Test Steps**:
1. Test GitUncommit with renamed files
2. Verify parsing handles the " -> " format

#### Test Case 1.3.3: Test New Implementation
**Test Steps**:
1. Replace with: `git ls-files --modified --deleted --others -z | xargs -0 $cmd`
2. Test with various file types
3. Compare results with old implementation

---

### 🔜 Fix 1.4: Bare Exception in setup.py

**Risk Level**: HIGH (Hides errors)

#### Test Case 1.4.1: Test with Non-Existent Command
**Test Steps**:
```python
# In setup.py, call CommandExists with fake command
CommandExists("fake-command-12345")
```

**Expected Results**: Should return False with no error message (current behavior)

#### Test Case 1.4.2: Test After Fix
**Test Steps**:
1. Replace bare except with specific exception
2. Add error logging
3. Test with various scenarios:
   - Command not found
   - Command found
   - Keyboard interrupt (Ctrl+C) - should NOT be caught
   - Permission denied

---

### 🔜 Fix 1.5: macOS Version Parsing Bug

**Risk Level**: HIGH (Breaks on modern macOS)

#### Test Case 1.5.1: Test Various macOS Versions
**Test Versions**:
- macOS 10.14 (Mojave) - expects bash_profile
- macOS 10.15 (Catalina) - expects zshrc
- macOS 11.0 (Big Sur) - expects zshrc
- macOS 12.0 (Monterey) - expects zshrc
- macOS 13.0 (Ventura) - expects zshrc
- macOS 14.0 (Sonoma) - expects zshrc
- macOS 15.0 (Sequoia) - expects zshrc

**Test Steps**:
```python
# Test version parsing
import platform
v, _, _ = platform.mac_ver()
print(f"Version string: {v}")

# Current implementation (will fail on some versions)
try:
    v_float = float('.'.join(v.split('.')[:2]))
    print(f"Float version: {v_float}")
except Exception as e:
    print(f"ERROR: {e}")

# Test with tuple comparison (proposed fix)
v_tuple = tuple(map(int, v.split('.')[:2]))
print(f"Tuple version: {v_tuple}")
print(f"Use zsh: {v_tuple >= (10, 15)}")
```

---

### 🔜 Fix 2.1: Consolidate Print Functions

**Risk Level**: LOW (Code quality)

#### Test Case 2.1.1: Verify All Print Functions Work
**Test Steps**:
1. Source utils.sh: `source /home/cm/dotfiles/utils.sh`
2. Test each function:
   ```bash
   PrintError "Test error message"
   PrintWarning "Test warning message"
   PrintHint "Test hint message"
   ```
3. Verify colors display correctly

#### Test Case 2.1.2: Test After Consolidation
**Test Steps**:
1. Modify uninstall.sh to source utils.sh
2. Remove duplicate print functions
3. Test uninstall.sh still displays messages correctly

---

### 🔜 Fix 3.1: Quote All Variable Expansions

**Risk Level**: MEDIUM (Shell fragility)

#### Test Case 3.1.1: Audit Shell Scripts
**Test Steps**:
```bash
# Find all shell scripts
find /home/cm/dotfiles -name "*.sh" -type f

# Search for unquoted variables (manual review)
grep -n '\$[A-Za-z_]' *.sh git/*.sh mozilla/**/*.sh
```

#### Test Case 3.1.2: Test Specific Functions
**Test Steps**:
1. Test RecursivelyFind with paths containing spaces
2. Test git functions with filenames containing spaces
3. Test all Mozilla aliases with edge cases

---

### 🔜 Fix 4.1: Extract Hardcoded Paths

**Risk Level**: MEDIUM (Flexibility)

#### Test Case 4.1.1: Create Configuration File
**Test Steps**:
1. Create config.sh with default paths
2. Source config.sh in scripts
3. Test that defaults work
4. Override a path and verify custom path is used

#### Test Case 4.1.2: Test All Path References
**Paths to Test**:
- `~/.mozbuild/machrc`
- `~/Work/git-cinnabar`
- `~/.local/bin`
- `~/.local/share/Trash/files`
- `~/.cargo/env`

---

## Cross-Platform Testing

### Linux Testing Matrix

| Distribution | Version | Bash Version | Test Status |
|--------------|---------|--------------|-------------|
| Ubuntu       | 22.04   | 5.1+         | [ ] Pending |
| Ubuntu       | 24.04   | 5.2+         | [ ] Pending |
| Fedora       | 39      | 5.2+         | [ ] Pending |
| Arch         | Latest  | 5.2+         | [ ] Pending |
| Debian       | 12      | 5.2+         | [ ] Pending |

**Current System**: Linux 6.14.0-37-generic

### macOS Testing Matrix

| Version | Name | Default Shell | Test Status |
|---------|------|---------------|-------------|
| 10.14   | Mojave | bash | [ ] Pending |
| 10.15   | Catalina | zsh | [ ] Pending |
| 11.x    | Big Sur | zsh | [ ] Pending |
| 12.x    | Monterey | zsh | [ ] Pending |
| 13.x    | Ventura | zsh | [ ] Pending |
| 14.x    | Sonoma | zsh | [ ] Pending |
| 15.x    | Sequoia | zsh | [ ] Pending |

### Platform-Specific Considerations

#### Linux
- Test Trash functionality: `~/.local/share/Trash/files`
- Test OpenWithWayland function
- Test git branch in prompt

#### macOS
- Test zsh vs bash_profile selection
- Test Trash path: `~/.Trash`
- Test with both Intel and Apple Silicon
- Verify readlink behavior (may need greadlink)

---

## Automated Testing Setup

### Prerequisites
```bash
# Install testing tools
pip install pytest
sudo apt install shellcheck  # or brew install shellcheck on macOS

# Install bats (Bash Automated Testing System)
git clone https://github.com/bats-core/bats-core.git
cd bats-core
sudo ./install.sh /usr/local
```

### Shell Script Testing with BATS

**Create**: `tests/test_utils.bats`
```bash
#!/usr/bin/env bats

setup() {
    # Load utils.sh before each test
    source "${BATS_TEST_DIRNAME}/../utils.sh"
}

@test "PrintError displays message" {
    run PrintError "test message"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "ERROR:" ]]
}

@test "RecursivelyFind locates files" {
    # Test implementation
}
```

### Python Testing with pytest

**Create**: `tests/test_setup.py`
```python
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Test setup.py functions
def test_command_exists():
    # Test CommandExists function
    pass

def test_path_handling():
    # Test path construction
    pass
```

### Running Tests
```bash
# Run shell tests
bats tests/test_utils.bats

# Run Python tests
pytest tests/

# Run shellcheck on all scripts
find . -name "*.sh" -type f -exec shellcheck {} \;

# Check bash syntax on all scripts
find . -name "*.sh" -type f -exec bash -n {} \;
```

---

## Manual Testing Checklist

Before marking any fix as complete, verify:

- [ ] Syntax check passes (`bash -n script.sh`)
- [ ] Shellcheck passes (or issues documented)
- [ ] Works from different directories
- [ ] Handles missing files gracefully
- [ ] Handles paths with spaces
- [ ] Handles special characters in filenames
- [ ] Error messages are clear and helpful
- [ ] No data loss risk
- [ ] Backwards compatible (or breaking changes documented)
- [ ] Tested on target platforms (Linux and/or macOS)
- [ ] Documentation updated (CLAUDE.md)
- [ ] TODO.md updated with completion status

---

## Testing Log

### Session 1: 2026-01-07

#### Fix 1.2: Fragile File Path Handling
- **Syntax Check**: ✅ PASSED (bash -n)
- **Automated Tests Completed**:
  - Test Case 1.2.7: ✅ PASSED (readlink -f works on Linux)
  - Test Case 1.2.8: ✅ PASSED (syntax validation)
  - Script directory detection: ✅ PASSED
  - Symlink detection [ -L ]: ✅ PASSED

- **Manual Tests**: ⏳ PENDING (User should run before production use)
  - Test Case 1.2.1: ⏳ Pending (Normal symlink uninstall)
  - Test Case 1.2.2: ⏳ Pending (Run from different directory)
  - Test Case 1.2.3: ⏳ Pending (Paths with spaces)
  - Test Case 1.2.4: ⏳ Pending (Non-existent files)
  - Test Case 1.2.5: ⏳ Pending (Regular file instead of symlink)
  - Test Case 1.2.6: ⏳ Pending (Symlink to wrong target)

**Test Results Summary**:
- ✅ All automated syntax and command availability tests passed
- ✅ readlink -f works correctly on Linux (GNU coreutils 9.4)
- ✅ Script directory detection logic verified
- ⚠️  macOS compatibility needs testing (readlink -f may not work on older versions)
- ⚠️  Full integration tests pending (requires setup.py to be run first)

**Notes**:
- The fix improves robustness significantly over ls parsing
- All variables now properly quoted
- Better error messages for different file states
- **Recommendation**: User should run manual test cases 1.2.1-1.2.6 before using in production
- **macOS Note**: May need to add fallback for systems without `readlink -f` support

---

## Risk Assessment

### High Risk Changes (require extensive testing)
1. Fix 1.1: eval usage (security)
2. Fix 1.3: git status parsing (data loss)
3. Fix 1.4: exception handling (error masking)
4. Fix 1.5: macOS version parsing (platform compatibility)

### Medium Risk Changes
1. Fix 2.2: path construction standardization
2. Fix 3.1: variable quoting
3. Fix 4.1: hardcoded paths

### Low Risk Changes
1. Fix 2.1: consolidate print functions
2. Fix 6.1: typo fixes
3. Fix 7.2: naming conventions

---

## Rollback Plan

If any change breaks functionality:

1. **Immediate Rollback**:
   ```bash
   git checkout HEAD~1 filename.sh
   ```

2. **Document the Issue**:
   - What broke?
   - What was the test case?
   - What platform/environment?

3. **Re-evaluate the Fix**:
   - Was the approach wrong?
   - Was it an edge case not considered?
   - Does it need a different solution?

---

## Next Steps

1. ⏳ Run manual test suite for Fix 1.2
2. ⏳ Set up automated testing with bats
3. ⏳ Run shellcheck on all scripts
4. ⏳ Test on macOS if available
5. ⏳ Move to next fix after Fix 1.2 validation complete
