# macOS Cross-Platform Testing Plan (Item 8.3)

**Purpose**: Verify that all 31 completed dotfiles improvements work correctly on macOS

**Date Created**: 2026-01-09

**Estimated Time**: 30-45 minutes

---

## Prerequisites

- macOS laptop (any recent version: 10.15+, 11, 12, 13, 14)
- Access to the dotfiles repository
- Basic terminal knowledge

---

## Phase 1: Preparation (Safe - No Changes)

### Step 1: Transfer dotfiles to macOS

**Option A: Git clone (recommended if pushed to remote)**
```bash
# On macOS
cd ~
git clone <your-repo-url> dotfiles-test
cd dotfiles-test
```

**Option B: Copy files directly**
```bash
# On Linux, create tarball:
cd /home/cm
tar czf dotfiles-test.tar.gz dotfiles/

# Transfer to macOS (scp, USB, etc.)
# On macOS, extract:
cd ~
tar xzf dotfiles-test.tar.gz
cd dotfiles
```

**Expected result**: Dotfiles directory exists on macOS

---

### Step 2: Check macOS environment

```bash
# Check macOS version
sw_vers

# Check default shell (should be zsh on macOS 10.15+)
echo $SHELL

# Check available shells
which bash
which zsh

# Record these values for documentation
```

**Expected output**:
- macOS version: 11.x, 12.x, 13.x, or 14.x
- Default shell: `/bin/zsh` (on 10.15+) or `/bin/bash` (older)
- Both bash and zsh should be available

---

### Step 3: Verify required tools

```bash
# Check Python 3 (required)
python3 --version

# Check git (required)
git --version

# Check if Homebrew is installed (optional but common)
which brew

# Check if test suite dependencies are available
bash --version
```

**Expected output**:
- Python 3.x (any recent version)
- Git 2.x or later
- Bash 3.x or later

---

## Phase 2: Dry-Run Testing (Safe - No Changes)

### Step 4: Test dry-run mode

```bash
cd ~/dotfiles  # or ~/dotfiles-test

# Basic dry-run
python3 setup.py --dry-run

# Verbose dry-run (shows detailed operations)
python3 setup.py --dry-run -v

# With Mozilla tools (if applicable)
python3 setup.py --dry-run --mozilla gecko

# With dev-tools
python3 setup.py --dry-run --dev-tools
```

**What to verify**:
- [ ] Script runs without errors
- [ ] Platform detected as "darwin" (in verbose output)
- [ ] Shows "Would link" messages for:
  - `~/.dotfiles` → dotfiles directory
  - `~/.zshrc` → `dot.zshrc` (on macOS 10.15+)
  - `~/.settings_darwin` → `dot.settings_darwin`
- [ ] Correct trash path shown: `~/.Trash` (not Linux path)
- [ ] [DRY-RUN] prefix appears on all operations
- [ ] Final message: "DRY-RUN COMPLETE - No changes were made"

**Issues to note**: Any errors, unexpected paths, or wrong platform detection

---

### Step 5: Test help and info commands

```bash
# Test help messages
python3 setup.py --help
bash uninstall.sh --help

# Test show-manual (shows what needs manual cleanup)
bash uninstall.sh --show-manual
```

**What to verify**:
- [ ] Help messages display correctly
- [ ] All flags documented (--dry-run, --mozilla, --dev-tools, -v)
- [ ] Show-manual displays without errors

---

## Phase 3: Actual Setup Testing (Makes Changes)

### Step 6: Backup existing dotfiles (IMPORTANT!)

```bash
# Create backup directory
mkdir -p ~/dotfiles-backup-$(date +%Y%m%d)
BACKUP_DIR=~/dotfiles-backup-$(date +%Y%m%d)

# Backup existing files if they exist
[ -f ~/.bashrc ] && cp ~/.bashrc "$BACKUP_DIR/"
[ -f ~/.bash_profile ] && cp ~/.bash_profile "$BACKUP_DIR/"
[ -f ~/.zshrc ] && cp ~/.zshrc "$BACKUP_DIR/"
[ -f ~/.gitconfig ] && cp ~/.gitconfig "$BACKUP_DIR/"
[ -L ~/.dotfiles ] && readlink ~/.dotfiles > "$BACKUP_DIR/dotfiles-link.txt"
[ -L ~/.settings_darwin ] && readlink ~/.settings_darwin > "$BACKUP_DIR/settings-link.txt"

echo "Backup created in: $BACKUP_DIR"
ls -la "$BACKUP_DIR"
```

**Expected result**: Backup directory created with existing dotfiles

---

### Step 7: Run actual setup

```bash
cd ~/dotfiles  # or ~/dotfiles-test

# Run setup with verbose mode for detailed output
python3 setup.py -v
```

**What happens**:
1. Creates symlink: `~/.dotfiles` → dotfiles directory
2. Creates symlink: `~/.zshrc` → `dot.zshrc` (on macOS 10.15+)
3. Creates symlink: `~/.settings_darwin` → `dot.settings_darwin`
4. Configures git to include `dotfiles/git/config`
5. Runs verification checks

**What to verify**:
- [ ] No errors during setup
- [ ] All steps show "SUCCESS" or "✓"
- [ ] Installation verification passes
- [ ] Final message: "All steps completed successfully!"

---

### Step 8: Verify symlinks were created correctly

```bash
# Check dotfiles symlink
ls -la ~/.dotfiles
readlink ~/.dotfiles  # Should show path to dotfiles directory

# Check zshrc symlink (on macOS 10.15+)
ls -la ~/.zshrc
readlink ~/.zshrc  # Should show path to dotfiles/dot.zshrc

# Check platform settings symlink
ls -la ~/.settings_darwin
readlink ~/.settings_darwin  # Should show path to dotfiles/dot.settings_darwin

# Check git config integration
git config --global --get include.path
# Should show path to dotfiles/git/config
```

**What to verify**:
- [ ] `~/.dotfiles` symlink exists and points to correct directory
- [ ] `~/.zshrc` symlink exists (on modern macOS)
- [ ] `~/.settings_darwin` symlink exists
- [ ] Git config includes dotfiles git config
- [ ] All symlinks are valid (not broken)

---

### Step 9: Test shell environment

```bash
# Source the new shell configuration
source ~/.zshrc  # or source ~/.bashrc if older macOS

# Test platform detection
echo "Platform: $PLATFORM"
# Should output: darwin

# Test settings file loaded
echo "Settings platform: $SETTINGS_PLATFORM"
# Should output: /Users/<username>/.settings_darwin

# Test dotfiles variable
echo "Dotfiles: $DOTFILES"
# Should output: /Users/<username>/.dotfiles

# Test CommandExists utility (from utils.sh)
CommandExists git
echo "Exit code: $?"
# Should output: 0 (command exists)

CommandExists nonexistent-command-xyz
echo "Exit code: $?"
# Should output: 1 (command does not exist)
```

**What to verify**:
- [ ] PLATFORM variable set to "darwin"
- [ ] SETTINGS_PLATFORM points to ~/.settings_darwin
- [ ] DOTFILES variable set correctly
- [ ] CommandExists utility works correctly

---

### Step 10: Test Trash function (macOS-specific)

```bash
# Create test file
cd /tmp
echo "test content" > test-trash-file.txt
ls -la test-trash-file.txt

# Move to trash using Trash function
Trash test-trash-file.txt

# Verify file is in macOS Trash
ls ~/.Trash/ | grep test-trash-file
# Should show the file

# Check file is gone from original location
ls -la test-trash-file.txt 2>&1
# Should show "No such file or directory"
```

**What to verify**:
- [ ] Trash function exists and works
- [ ] File moved to `~/.Trash` (not Linux trash location)
- [ ] File removed from original location

---

### Step 11: Test git utilities

```bash
# Test GitLastCommit function exists
type GitLastCommit
# Should show function definition

# Test GitUncommit function exists
type GitUncommit

# Test GitAddExcept function exists
type GitAddExcept

# Test CreateGitBranchForPullRequest function exists
type CreateGitBranchForPullRequest

# Test BranchInPrompt function exists
type BranchInPrompt

# In a git repository, test basic functionality
cd ~/dotfiles
GitLastCommit ls  # Should list files from last commit (if any)
```

**What to verify**:
- [ ] All git utility functions are defined
- [ ] Functions work without errors in a git repository

---

## Phase 4: Shell Utilities Testing

### Step 12: Run shell test suite

```bash
cd ~/dotfiles  # or ~/dotfiles-test

# Run the shell utilities test suite
bash test_shell_utils.sh
```

**Expected output**:
```
Tests run:    19
Tests passed: 19
Tests failed: 0

✓ All tests passed!
```

**What to verify**:
- [ ] All 19 tests pass on macOS
- [ ] No failures or errors
- [ ] Test summary shows 19/19 passed

**If tests fail**: Note which tests failed and the error messages

---

### Step 13: Test platform-specific functionality

```bash
# Test RecursivelyFind
cd /tmp
mkdir -p test-find-macos
touch test-find-macos/file1.txt test-find-macos/file2.log test-find-macos/file3.txt
RecursivelyFind "*.txt"
# Should find file1.txt and file3.txt, preview them, and ask for confirmation
# Answer 'N' to cancel (don't actually delete)
rm -rf test-find-macos

# Test HostHTTP (if available)
cd ~/dotfiles
HostHTTP --help 2>/dev/null || echo "HostHTTP not available (OK on macOS)"

# Test that Linux-specific functions don't exist on macOS
type OpenWithWayland 2>/dev/null && echo "ERROR: OpenWithWayland should not exist on macOS" || echo "✓ OpenWithWayland correctly not available"
```

**What to verify**:
- [ ] RecursivelyFind works correctly
- [ ] OpenWithWayland does NOT exist on macOS (Linux-only)
- [ ] Platform-specific functions work as expected

---

## Phase 5: Python Test Suite

### Step 14: Run Python test suite

```bash
cd ~/dotfiles  # or ~/dotfiles-test

# Run Python tests
python3 test_setup.py
```

**Expected output**:
```
Ran 22 tests in X.XXXs

OK
```

**What to verify**:
- [ ] All 22 Python tests pass on macOS
- [ ] No failures or errors
- [ ] Test summary shows OK

**If tests fail**: Note which tests failed and the error messages

---

## Phase 6: Uninstall Testing

### Step 15: Test uninstall dry-run

```bash
cd ~/dotfiles  # or ~/dotfiles-test

# Preview uninstall
bash uninstall.sh --dry-run
```

**What to verify**:
- [ ] Shows "[DRY-RUN MODE] Previewing uninstall"
- [ ] Shows "Would unlink ~/.dotfiles"
- [ ] Shows "Would unlink ~/.zshrc" (on modern macOS)
- [ ] Shows "Would unlink ~/.settings_darwin"
- [ ] Lists manual cleanup items (git config, bashrc if applicable)
- [ ] Shows exact cleanup commands
- [ ] Final message: "[DRY-RUN COMPLETE] No changes were made"

---

### Step 16: (Optional) Test actual uninstall

**⚠️ WARNING**: This will remove the dotfiles setup. Only do this if you want to fully test uninstall, or if you're done testing.

```bash
cd ~/dotfiles  # or ~/dotfiles-test

# Run uninstall
bash uninstall.sh

# Verify symlinks were removed
ls -la ~/.dotfiles 2>&1  # Should show "No such file or directory"
ls -la ~/.zshrc 2>&1  # Should show no symlink or original file
ls -la ~/.settings_darwin 2>&1  # Should show "No such file or directory"

# Note: Git config and bashrc require manual cleanup (by design)
```

**What to verify**:
- [ ] Uninstall completes without errors
- [ ] Shows summary of removed items
- [ ] Symlinks are removed
- [ ] Manual cleanup instructions shown
- [ ] No actual files deleted (only symlinks)

**To restore**:
```bash
# If you want to restore the setup
cd ~/dotfiles
python3 setup.py

# Or restore your original dotfiles from backup
BACKUP_DIR=~/dotfiles-backup-$(date +%Y%m%d)
[ -f "$BACKUP_DIR/.bashrc" ] && cp "$BACKUP_DIR/.bashrc" ~/
[ -f "$BACKUP_DIR/.zshrc" ] && cp "$BACKUP_DIR/.zshrc" ~/
[ -f "$BACKUP_DIR/.gitconfig" ] && cp "$BACKUP_DIR/.gitconfig" ~/
```

---

## Phase 7: Documentation

### Step 17: Create test results file

```bash
cd ~/dotfiles  # or ~/dotfiles-test

# Create results file
cat > TESTING_RESULTS_MACOS.md << 'EOF'
# macOS Cross-Platform Testing Results

**Date**: 2026-01-09
**Tester**: [Your name or Claude Code]
**macOS Version**: [Fill in from sw_vers]
**Shell**: [Fill in from echo $SHELL]
**Python Version**: [Fill in from python3 --version]

---

## Environment Details

```
$ sw_vers
[paste output]

$ echo $SHELL
[paste output]

$ python3 --version
[paste output]

$ git --version
[paste output]
```

---

## Test Results Summary

### Phase 1: Preparation
- [x] Dotfiles transferred to macOS
- [x] Environment verified
- [x] Required tools available

### Phase 2: Dry-Run Testing
- [ ] Dry-run mode works without errors
- [ ] Platform detected as "darwin"
- [ ] Correct macOS paths shown (~/Trash, ~/.zshrc)
- [ ] Help commands work
- [ ] Show-manual works

### Phase 3: Actual Setup
- [ ] Backup created successfully
- [ ] Setup runs without errors
- [ ] Symlinks created correctly
  - [ ] ~/.dotfiles
  - [ ] ~/.zshrc (on macOS 10.15+)
  - [ ] ~/.settings_darwin
- [ ] Git config integration works
- [ ] Platform detection works (PLATFORM=darwin)
- [ ] Trash function works with ~/.Trash
- [ ] Git utilities available and working

### Phase 4: Shell Utilities Testing
- [ ] test_shell_utils.sh: 19/19 tests pass
- [ ] RecursivelyFind works
- [ ] OpenWithWayland correctly not available (Linux-only)
- [ ] Platform-specific functions work

### Phase 5: Python Test Suite
- [ ] test_setup.py: 22/22 tests pass
- [ ] No errors or failures

### Phase 6: Uninstall Testing
- [ ] Dry-run shows correct operations
- [ ] (Optional) Uninstall works correctly

---

## Platform-Specific Findings

### Confirmed Working on macOS:
1. **Platform detection**: Correctly identifies "darwin"
2. **Shell entry point**: Uses ~/.zshrc on macOS 10.15+ (or ~/.bash_profile on older)
3. **Trash location**: Correctly uses ~/.Trash (not Linux path)
4. **Symlink creation**: All symlinks created successfully
5. **Git integration**: Git config includes work correctly
6. **Shell utilities**: All 19 tests pass
7. **Python tests**: All 22 tests pass

### Differences from Linux:
1. **Default shell**: zsh (not bash) on macOS 10.15+
2. **Trash directory**: ~/.Trash vs ~/.local/share/Trash/files
3. **Settings file**: dot.settings_darwin vs dot.settings_linux
4. **Package manager**: Homebrew (brew) vs apt-get
5. **OpenWithWayland**: Not available on macOS (Linux-only, correct)

### Issues Found:
(List any issues discovered during testing, or write "None")

### Recommendations:
(List any improvements needed, or write "None - all working as expected")

---

## Conclusion

Cross-platform compatibility: **[PASS/FAIL]**

All dotfiles improvements work correctly on macOS: **[YES/NO]**

Ready to mark Item 8.3 as complete: **[YES/NO]**

---

## Notes

(Add any additional observations or notes here)

EOF

echo "Results file created: TESTING_RESULTS_MACOS.md"
echo "Please fill in the checkboxes and details as you complete each test"
```

---

## Quick Reference Commands

### Essential Commands
```bash
# Setup
python3 setup.py --dry-run  # Preview changes
python3 setup.py -v         # Run setup with verbose output

# Testing
bash test_shell_utils.sh    # Run shell tests
python3 test_setup.py       # Run Python tests

# Verification
ls -la ~/.dotfiles          # Check dotfiles symlink
ls -la ~/.zshrc             # Check zshrc symlink
git config --global --list  # Check git config

# Uninstall
bash uninstall.sh --dry-run # Preview uninstall
bash uninstall.sh           # Actually uninstall
```

### Cleanup/Restore Commands
```bash
# Restore from backup
BACKUP_DIR=~/dotfiles-backup-$(date +%Y%m%d)
cp "$BACKUP_DIR/.zshrc" ~/
cp "$BACKUP_DIR/.gitconfig" ~/

# Remove symlinks manually if needed
rm ~/.dotfiles
rm ~/.zshrc
rm ~/.settings_darwin
```

---

## Reporting Results

After completing all tests, report back with:

1. **Overall result**: PASS or FAIL
2. **macOS version tested**: (from `sw_vers`)
3. **Test results**:
   - Shell tests: X/19 passed
   - Python tests: X/22 passed
4. **Any issues found**: (with details)
5. **Platform-specific observations**: (anything unexpected)

If all tests pass, Item 8.3 will be marked complete, achieving **100% of explicitly tracked TODO items**!

---

## Troubleshooting

### Issue: "Permission denied" errors
**Solution**: Check file permissions, may need to make scripts executable
```bash
chmod +x test_shell_utils.sh
chmod +x uninstall.sh
```

### Issue: Python tests fail with import errors
**Solution**: Make sure you're in the dotfiles directory
```bash
cd ~/dotfiles
python3 test_setup.py
```

### Issue: Shell functions not found
**Solution**: Source the shell configuration
```bash
source ~/.zshrc
# Or
source ~/.bashrc
```

### Issue: Symlinks already exist
**Solution**: Use dry-run first, or manually remove old symlinks
```bash
rm ~/.dotfiles
rm ~/.zshrc
rm ~/.settings_darwin
```

---

## Safety Notes

- ✅ **Dry-run is safe**: No changes made, safe to run anytime
- ✅ **Backups created**: Original files backed up before changes
- ✅ **Symlinks only**: Setup only creates symlinks, doesn't modify original files
- ⚠️ **Manual cleanup**: Git config and bashrc require manual removal (by design)
- ⚠️ **Test in a clean environment**: If possible, test on a fresh user account

---

**Good luck with testing! 🚀**
