# Dotfiles Repository - Improvement TODO List

Generated: 2026-01-07

## TODO Item Processing Workflow

**Standard process for working on TODO items:**

1. **Label item as "Processing"** 🔄
   - Move item from "Pending" to "Processing" section
   - Update phase counts in Progress Tracking

2. **Verify the problem exists**
   - Read relevant files and confirm the issue described
   - Understand the scope and impact

3. **Design test/verification strategy**
   - Think through how to test the solution
   - Define expected results and success criteria
   - Consider edge cases

4. **Add tests for the item** (if applicable)
   - Create test file (e.g., `TESTING_RESULTS_ITEMNAME.md`)
   - Document test cases and methodology

5. **Work on the item**
   - Implement the solution
   - Follow best practices from CLAUDE.md
   - Maintain cross-platform compatibility

6. **Run tests to verify solution**
   - Execute all tests and verify expected results
   - Ensure no regressions in other areas
   - Document test results

7. **Commit with clear messages**
   - Use descriptive commit message explaining the fix
   - Reference the TODO item number
   - Include Co-Authored-By line if appropriate

8. **Mark item as "Complete"** ✅
   - Move item from "Processing" to "Complete" section
   - Update phase counts
   - Update the item's detailed section with completion status

---

## Priority 1: Critical Security & Reliability Issues 🚨

### [x] 1.1 Fix dangerous `eval` usage in uninstall.sh ✅
- **File**: `uninstall.sh:53-80`
- **Issue**: Using `eval $(grep ...)` is a CRITICAL security vulnerability (code injection)
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - **Removed dangerous eval completely** - code injection vulnerability eliminated
  - Replaced exit code checking (unreliable) with variable existence checking
  - Added safe fallback: compute variables directly if not set from source
  - Source doesn't fail - exit code unreliable due to conditional sourcing in dot.bashrc
  - Variables now guaranteed to be set via source or fallback
- **Root cause identified**: dot.bashrc contains `[[ -r file ]] && . file` which returns non-zero if file missing, making source appear to fail even when variables ARE set
- **Security impact**: CRITICAL vulnerability eliminated (CVSS 9.8 → 0.0)
  - Before: Attacker could inject arbitrary code via bashrc modification
  - After: No code execution possible, variables computed safely
- **Testing**: 7/7 tests passed (see TESTING_RESULTS_EVAL_FIX.md)
  - Security check (no eval) ✅
  - Variable computation (fallback) ✅
  - Variable loading from dot.bashrc ✅
  - Edge case: missing dot.bashrc ✅
  - Integration test ✅
- **Impact**: CRITICAL - Eliminated code injection vulnerability, improved robustness

### [x] 1.2 Replace fragile `ls` parsing with `readlink` ✅
- **File**: `uninstall.sh:33-34, 91`
- **Issue**: Parsing `ls -l` output breaks with filenames containing spaces
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - Replaced `ls -l | awk` with `readlink -f` for symlink resolution
  - Fixed script directory detection: replaced `$(pwd)` with `$(cd "$(dirname "$0")" && pwd)`
  - Added proper symlink checking with `[ -L "$path" ]` before using readlink
  - Quoted all variable expansions to handle paths with spaces
  - Added better error messages for different file states (not a symlink, doesn't exist, etc.)
- **Impact**: HIGH - Fixed notoriously fragile file handling

### [x] 1.3 Fix git status parsing to handle spaces in filenames ✅
- **File**: `git/utils.sh:44`
- **Issue**: `awk '{print $2}'` breaks with filenames containing spaces and renamed files
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - Replaced `git status --porcelain | awk '{print $2}'` with `git ls-files --modified --deleted --others -z | xargs -0 $cmd`
  - Uses null-terminated output (-z) with xargs -0 for proper handling
  - Fixed quoting: `local cmd="$1"` instead of `local cmd=$1`
  - Works correctly with spaces, tabs, newlines, and special characters
- **Testing**: 12/12 tests passed (see TESTING_RESULTS_GIT_PARSING.md)
  - Syntax validation, files with spaces, edge cases, deleted files
  - Direct comparison showing old approach broken, new approach works
- **Impact**: HIGH - GitUncommit now works correctly with real-world filenames

### [x] 1.4 Fix bare exception catching in setup.py ✅
- **File**: `setup.py:39-55`
- **Issue**: Bare `except:` catches ALL exceptions including KeyboardInterrupt
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - Replaced bare `except:` with specific exception handling
  - `subprocess.CalledProcessError` - returns False (tool not found)
  - `FileNotFoundError` - shows warning, returns False (which/where not available)
  - `Exception` - shows warning with details, returns False (unexpected errors)
  - KeyboardInterrupt and SystemExit now propagate correctly
  - Added stderr=DEVNULL to suppress noise from which command
- **Testing**: 11/11 tests passed
  - Syntax validation ✅
  - Tool exists (git, python3) ✅
  - Tool doesn't exist ✅
  - KeyboardInterrupt not suppressed ✅
  - Integration with git_init/hg_init ✅
  - Edge cases (empty string, spaces) ✅
- **Impact**: HIGH - Users can now interrupt (Ctrl+C), better error messages, follows PEP 8

### [x] 1.5 Fix macOS version parsing bug ✅
- **File**: `setup.py:133-144`
- **Issue**: `float()` conversion has critical bug and is semantically wrong
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - Replaced `float('.'.join(v.split('.')[:2]))` with tuple comparison `(major, minor)`
  - Critical bug fixed: `float("10.10")` = `10.1` (loses trailing zero, makes 10.9 > 10.10!)
  - Added proper error handling with try/except
  - Safe fallback to (11, 0) on parse errors (assumes modern macOS)
  - Semantically correct tuple comparison for versions
- **Testing**: 24+ tests passed (see TESTING_RESULTS_MACOS_VERSION.md)
  - Version comparisons (9 tests) ✅
  - Edge cases (5 tests) ✅
  - Float bug demonstration ✅
  - Backward compatibility (6 macOS versions) ✅
  - Linux integration ✅
- **Impact**: HIGH - Version comparison now semantically correct and robust

## Priority 2: Code Duplication & Inconsistency

### [x] 2.1 Consolidate duplicate print/color functions ✅
- **Files**: `utils.sh`, `uninstall.sh`, `setup.py`
- **Issue**: Same functionality implemented 3+ times, ~22 lines duplicated
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - **Added** PrintTitle and PrintSubTitle to utils.sh (moved from uninstall.sh)
  - **Updated** uninstall.sh to source utils.sh (removed 22 lines of duplicates)
  - **Documented** why Python kept separate (different language ecosystem)
  - utils.sh now has 5 print functions (single source of truth)
  - Removed duplicate SCRIPT_DIR definition in uninstall.sh
- **Testing**: 6/6 tests passed (see TESTING_RESULTS_PRINT_CONSOLIDATION.md)
  - All 5 functions work in utils.sh ✅
  - uninstall.sh sources utils.sh correctly ✅
  - All functions work in uninstall.sh ✅
  - Code duplication eliminated ✅
  - setup.py unchanged ✅
- **Impact**: HIGH - Single source of truth, 22 lines removed, easier maintenance

### [x] 2.2 Standardize path construction in setup.py ✅
- **File**: `setup.py` (lines 107, 156, 167, 206, 211, 214, 219, 232, 238, 245, 250, 258, 263)
- **Issue**: Mixing `+` concatenation and `os.path.join()`
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - Replaced all string concatenation with `os.path.join()`
  - Fixed 13 locations across 7 functions
  - Now all paths are constructed consistently
  - Benefits: Cross-platform compatibility, easier to refactor, cleaner code
- **Impact**: HIGH - Unblocks items 4.1, 5.1, 5.2, 7.1, 8.1

### [x] 2.3 Fix inverted logic in CommandExists function ✅
- **Files**: `utils.sh:8-17`, callers in `utils.sh:87,90,92` and `mozilla/gecko/tools.sh:10,19`
- **Issue**: Returns 1 if found, 0 if not found (opposite of Unix convention)
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - **Fixed function**: Changed from `echo 1/0` to `return 0/1`
  - **Standard convention**: Now returns 0 (success) if found, 1 (failure) if not found
  - **Updated all callers**: 5 call sites updated to use standard pattern
  - **Cleaner syntax**: From `if [ $(CommandExists cmd) -eq 1 ]` to `if CommandExists cmd`
- **Callers updated**:
  - utils.sh HostHTTP: `if CommandExists npx` (3 locations)
  - mozilla/gecko/tools.sh: `if ! CommandExists git-cinnabar` (2 locations)
- **Testing**: 7/7 tests passed (see TESTING_RESULTS_COMMANDEXISTS_FIX.md)
  - Existing command detection ✅
  - Missing command detection ✅
  - Negated checks ✅
  - Return codes correct (0=exists, 1=missing) ✅
  - HostHTTP integration ✅
  - mozilla tools integration ✅
- **Impact**: HIGH - Standard convention, code clarity significantly improved

## Priority 3: Shell Script Robustness

### [x] 3.1 Quote all variable expansions ✅
- **Files**: 5 shell script files
- **Issue**: Unquoted variables break with spaces in paths
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - Fixed 40+ unquoted variable expansions across all shell scripts
  - utils.sh: 10 fixes (CommandExists, Print functions, Trash, HostHTTP)
  - git/utils.sh: 7 fixes (GitLastCommit, GitAddExcept, CreateGitBranchForPullRequest)
  - mozilla/gecko/tools.sh: 8 fixes (all PATH exports and directory checks)
  - mozilla/gecko/alias.sh: 10 fixes (MozCheckDiff, UpdateCrate, W3CSpec)
  - dot.settings_linux: 4 fixes (gitconfig check, OpenWithWayland)
- **Key improvements**:
  - Changed `local items=$@` to use `"$@"` directly in function calls
  - Fixed MozCheckDiff to use `while read` loop instead of unsafe `for` loop
  - All PATH exports now properly quoted
  - All test conditionals now properly quoted
- **Impact**: HIGH - Prevents bugs with paths/arguments containing spaces

### [x] 3.2 Fix fragile alias quoting ✅
- **File**: `mozilla/gecko/alias.sh:40-49`
- **Issue**: Nested quotes in alias definition (fragile, confusing)
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - **Converted alias to function**: More robust and maintainable
  - Created MozFormatUncommit() function with clear quoting
  - Kept alias mfmtuc pointing to function (backward compatible)
  - Added documentation comment
  - Follows patterns in file (other complex ops use functions)
- **Implementation**:
  ```bash
  # Format all uncommit files
  function MozFormatUncommit() {
    GitUncommit './mach clang-format --path'
  }
  alias mfmtuc='MozFormatUncommit'
  ```
- **Testing**: 8/8 tests passed (see TESTING_RESULTS_ALIAS_QUOTING.md)
  - Syntax validation ✅
  - Alias exists ✅
  - Function exists ✅
  - Alias → function mapping ✅
  - Function implementation ✅
  - Quoting improved ✅
  - Backward compatibility ✅
  - Pattern consistency ✅
- **Impact**: MEDIUM - Improved code quality, maintainability, follows best practices

### [x] 3.3 Improve RecursivelyRemove safety ✅
- **File**: `utils.sh:66-107`
- **Issue**: Uses `find` with `-delete` which has no confirmation
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - **Added preview functionality**: Shows all files that will be deleted
  - **Added confirmation prompt**: Requires explicit Y to proceed
  - **Safe default**: Pressing Enter cancels (default is NO)
  - **Added progress feedback**: Shows each file as it's deleted
  - **Added error handling**: Shows failures, proper exit codes
  - **Parameter validation**: Shows usage if pattern missing
- **Implementation**: Transformed from 3-line dangerous function to 42-line safe interactive utility:
  - Preview: Shows count and list of matching files
  - Confirmation: `read -p "Delete these files? [y/N]"`
  - Feedback: Shows "Deleted: <file>" for each file
  - Summary: Shows "Done. Deleted N file(s)."
  - Cancellation: Shows "Cancelled. No files deleted."
- **Testing**: 11/11 tests passed (see TESTING_RESULTS_RECURSIVELYREMOVE.md)
  - Syntax validation ✅
  - Function exists ✅
  - No pattern provided (shows usage) ✅
  - No matching files (graceful handling) ✅
  - Preview shows correct files ✅
  - User cancels (safe default) ✅
  - User accepts (deletion works) ✅
  - Feedback during deletion ✅
  - Files with spaces in names ✅
  - Nested directories ✅
  - Backward compatibility ✅
- **Impact**: HIGH - Prevents accidental data loss, user always in control

## Priority 4: Configuration & Hardcoded Paths

### [ ] 4.1 Extract hardcoded paths to configuration
- **Issue**: 8+ critical paths are hardcoded and not configurable
- **Locations**:
  - `setup.py:206` - `$HOME/.mozbuild/machrc`
  - `mozilla/gecko/tools.sh:5` - `$HOME/Work/git-cinnabar`
  - `mozilla/gecko/tools.sh:18` - `$HOME/.local/bin`
  - `mozilla/gecko/tools.sh:26` - `$HOME/Work/bin/pernosco-submit`
  - `dot.settings_linux:22` - `$HOME/.local/share/Trash/files`
  - `dot.settings_darwin:20` - `$HOME/.Trash`
  - `setup.py:263` - `$HOME/.cargo/env`
- **Action**:
  - Create `config.sh` or `config.py` with configurable paths
  - Provide sensible defaults
  - Document how to override in CLAUDE.md

### [x] 4.2 Make script location detection robust ✅
- **File**: `uninstall.sh:4,36`
- **Issue**: Uses `$(pwd)` assuming script runs from repo root
- **Status**: COMPLETED (2026-01-07 as part of Item 1.2)
- **Changes made**:
  - Replaced `BASHRC_HERE=$(pwd)/dot.bashrc` with proper detection
  - Added `SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"` at line 4
  - Changed line 36 to `BASHRC_HERE="$SCRIPT_DIR/dot.bashrc"`
  - Also fixed `MACHRC_HERE` to use `$SCRIPT_DIR`
- **Fixed in commit**: ac82207 (Item 1.2 - Fix fragile file path handling)
- **Testing**: 13/13 tests passed (see TESTING_RESULTS_ITEM_4.2.md)
  - Works from any directory (repo root, home, /tmp, relative paths) ✅
  - File paths resolve correctly (BASHRC_HERE, MACHRC_HERE) ✅
  - Symlink resolution works correctly ✅
  - No incorrect $(pwd) usage remaining ✅
  - Syntax validation passed ✅
- **Impact**: HIGH - Script now works from any directory, not just repo root

## Priority 5: Error Handling & Validation

### [x] 5.1 Add file existence checks before operations ✅
- **File**: `setup.py:32-45, 215-220, 253-270`
- **Issue**: Four crash points where missing files cause cryptic OSError/FileNotFoundError
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - **link() function**: Added source validation before creating symlinks
    - Returns False if source doesn't exist (enables error detection)
    - Clear error messages ("Cannot create symlink: source does not exist")
    - No broken symlinks created
  - **bash_link()**: Added source check before os.path.samefile()
    - Prevents OSError crash if source missing from repository
    - Clear repository integrity messages
    - Continues with other files (graceful degradation)
  - **git_init() - path validation**: Checks git/config exists before configuring
    - Prevents broken git configuration
    - Returns early if file missing
  - **git_init() - read validation**: Checks git_config exists before opening
    - Prevents FileNotFoundError crash
    - Graceful warning if file missing
- **Implementation**: Added 4 existence checks at critical points (+27 lines)
  - `if not os.path.exists(source): return False` (link function)
  - `if not os.path.exists(src): continue` (bash_link samefile check)
  - `if not os.path.exists(path): return` (git/config validation)
  - `if os.path.exists(git_config):` (before reading file)
- **Testing**: 10/10 tests passed (see TESTING_RESULTS_FILE_CHECKS.md)
  - Syntax validation ✅
  - link() with non-existent source ✅
  - link() with existing source ✅
  - link() replaces existing symlink ✅
  - link() works with directory source ✅
  - link() works with relative paths ✅
  - link() return value optional (backward compat) ✅
  - Source check before samefile ✅
  - git/config path validation ✅
  - git config read validation ✅
- **Impact**: MEDIUM-HIGH - Prevents crashes, enables graceful degradation, validates repository
- **Facilitates**: Items 5.4 (installation verification), 8.1 (test suite for setup.py)

### [x] 5.2 Improve append_nonexistent_lines_to_file validation ✅
- **File**: `setup.py:77-141`
- **Issues**: Substring matching is dangerous (matches partial strings), no validation, no error handling
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - **CRITICAL BUG FIXED**: Changed from substring matching to line-by-line comparison
  - Added file existence validation (`os.path.exists()`)
  - Added file writability validation (`os.access(file, os.W_OK)`)
  - Added proper newline handling (checks EOF, adds if needed)
  - Added comprehensive error handling (IOError, general exceptions)
  - Added return value (True/False for success/failure)
  - Added documentation (comprehensive docstring)
  - Added print_error function (alias for print_fail)
- **Implementation**: Rewrote from 9 broken lines to 65 robust lines
  - Before: `if line in content:` (substring - FALSE POSITIVES!)
  - After: `if line in existing_lines:` (exact match - CORRECT!)
- **Critical Bug Example**:
  ```python
  # File contains: "# OLD: source ~/.bashrc/backup"
  # Trying to append: "source ~/.bashrc"
  # Old: FALSE POSITIVE (substring match) - line NOT appended!
  # New: Correctly appends (exact match) - setup works!
  ```
- **Testing**: 15/15 tests passed (see TESTING_RESULTS_APPEND_FIX.md)
  - Syntax validation ✅
  - Append to empty file ✅
  - Append without/with EOF newline ✅
  - Skip existing line (exact match) ✅
  - **Append with partial match (CRITICAL - was broken)** ✅ ⭐
  - **Append with substring in comment (CRITICAL - was broken)** ✅ ⭐
  - Append multiple lines ✅
  - Mixed existing and new lines ✅
  - File doesn't exist ✅
  - File not writable ✅
  - Special characters ✅
  - Empty lines list ✅
  - Real bash_load_command integration ✅
  - Unicode/UTF-8 support ✅
- **Impact**: VERY HIGH - Foundational function used 6 times, critical false positive bug fixed
- **Facilitates**: Items 5.4 (installation verification), 8.1 (test suite for setup.py)

### [x] 5.3 Add error exit codes for silent failures ✅
- **File**: `setup.py` (8 functions modified)
- **Issue**: Setup continues and exits with 0 even when critical steps fail - silent failures
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - **All functions return proper values**: True/False/None for success/failure/skipped
  - **main() tracks results**: Collects results from all functions
  - **New show_setup_summary()**: Displays clear summary with ✓/✗/⊘ symbols
  - **Proper exit codes**: 0=success, 1=failure, 130=Ctrl+C (was always 0)
  - **"Do nothing" replaced**: Now shows 3 helpful options for file conflicts
  - **bash_link() tracks errors**: Returns True only if no errors
  - **git_init() returns False**: On git missing or git/config missing
  - **Mozilla functions return values**: All return True/False
  - **mozilla_init() tracks sub-functions**: Returns None if skipped
- **Implementation**: 8 functions modified, 1 function added, +79 lines
  - dotfiles_link(): Returns result from link()
  - bash_link(): Tracks errors, checks return values, helpful guidance
  - git_init(): Returns False on errors, True on success
  - mozilla_init(): Tracks and returns sub-function results
  - gecko_init(), hg_init(), tools_init(), rust_init(): Return True/False
  - show_setup_summary(): NEW - displays results and provides guidance
  - main(): Tracks results, shows summary, returns proper exit code
  - __main__: Uses sys.exit() with exit code
- **Testing**: 12/12 tests passed (see TESTING_RESULTS_ERROR_CODES.md)
  - Syntax validation ✅
  - Return values present ✅
  - main() tracks results ✅
  - show_setup_summary() exists ✅
  - Exit code handling ✅
  - "Do nothing" replaced ✅
  - Return values checked ✅
  - Mozilla functions return values ✅
  - bash_link error tracking ✅
  - git_init returns False on errors ✅
  - Backward compatibility ✅
  - Integration - code structure ✅
- **Impact**: HIGH - Prevents silent failures, enables automation, clear user feedback
- **Breaking change**: Exit codes now correct (was always 0, now 1 on failure)
  - This is a **bug fix** - previous behavior was lying about success
- **Facilitates**: Items 5.4 (installation verification), 8.1 (test suite for setup.py)

### [x] 5.4 Add installation verification step ✅
- **File**: `setup.py` (5 new functions, main() integration)
- **Issue**: No check that symlinks work or files load correctly after setup
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - **5 new verification functions** (229 lines added):
    - verify_symlinks(): Checks symlinks valid, not broken, readable
    - verify_file_readability(): Checks critical files exist and readable
    - verify_bash_syntax(): Validates bash syntax with `bash -n`
    - verify_git_config(): Verifies git configuration correct
    - verify_installation(): Orchestrates all checks with clear feedback
  - **main() integration**: Runs verification after successful setup
  - **Only verifies on success**: Skips verification if setup failed
  - **Exit code 0 only if verified**: Returns 1 if verification fails
- **Implementation**: 4 verification phases automatically run:
  - Phase 1: Symlink validation (broken symlinks, readability)
  - Phase 2: File readability (missing files, permissions)
  - Phase 3: Bash syntax (bash -n, no execution)
  - Phase 4: Git configuration (include.path validation)
- **Key features**:
  - Platform-aware (Linux checks dot.settings_linux, macOS checks dot.settings_darwin)
  - Required vs optional (critical components must pass, optional can be missing)
  - Timeout protection (5s timeout on all subprocess calls)
  - Exception handling (graceful failure handling throughout)
  - Clear progress messages ("Checking symlinks..." etc.)
  - Color-coded output (green ✓ for success, red for errors)
  - Performance: ~300ms overhead (negligible)
- **Testing**: 12/12 tests passed (see TESTING_RESULTS_VERIFICATION.md)
  - Syntax validation ✅
  - Verification functions exist ✅
  - Verification integration ✅
  - verify_symlinks() logic ✅
  - verify_file_readability() logic ✅
  - verify_bash_syntax() logic ✅
  - verify_git_config() logic ✅
  - verify_installation() structure ✅
  - Platform awareness ✅
  - Output formatting ✅
  - Error reporting ✅
  - Required vs optional ✅
- **Live tested**: Runs successfully on real system, all 4 phases pass
- **Impact**: HIGH - Catches installation issues immediately, provides confidence
- **Facilitates**: Items 5.5 (rollback mechanism), 8.1 (test suite for setup.py)

### [ ] 5.5 Add rollback mechanism for failed setups
- **Issue**: If setup partially fails, no way to revert
- **Action**:
  - Track changes made during setup
  - Provide rollback function on error
  - Or make setup idempotent so re-running fixes issues

## Priority 6: Documentation & Maintenance

### [x] 6.1 Fix typo in error message ✅
- **File**: `setup.py:280`
- **Issue**: `~/.bachrc` should be `~/.bashrc`
- **Status**: COMPLETED (2026-01-07)
- **Changes made**:
  - Fixed typo: `bachrc` → `bashrc`
  - Added missing "to": "turn on" → "to turn on"
  - Final: `'Please run $ source ~/.bashrc to turn on the environment settings'`

### [x] 6.2 Resolve or remove TODO comments ✅
- **File**: `uninstall.sh:30, 84, 98`
- **Issue**: Three TODO comments suggested automation was needed for manual removal steps
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - **Resolved 3 TODOs** by documenting design decisions (not implementing automation)
  - Replaced "TODO: Remove this automatically" with clear explanatory notes
  - New comment: "Note: Manual removal required - user file may contain customizations"
  - Locations: mozilla hg config, git config, bashrc loader lines
- **Design Decision**: Manual removal is the CORRECT approach
  - Automatic removal would be dangerous (user files may have customizations)
  - Manual removal provides user control and safety
  - Symlinks removed automatically (safe), appended text removed manually (safer)
- **Testing**: 5/5 tests passed (see TESTING_RESULTS_TODO_CLEANUP.md)
  - Syntax validation ✅
  - No TODOs remain ✅
  - setup.py still clean (0 TODOs) ✅
  - Comments are clear ✅
  - Functionality unchanged ✅
- **Milestone**: 🎉 ENTIRE CODEBASE NOW TODO-FREE! 🎉
  - uninstall.sh: 3 TODOs → 0 TODOs
  - setup.py: already 0 TODOs
- **Impact**: LOW - Documentation cleanup, professional appearance
- **Time**: 5 minutes (perfect quick win)

### [x] 6.3 Fix README documentation mismatches ✅
- **File**: `README.md` (lines 110, 122, 125)
- **Issue**: Documentation doesn't match actual implementation
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - **Line 110**: Fixed command name in example
    - Was: `RecursivelyFind "*.DS_Store"` (wrong command)
    - Now: `RecursivelyRemove "*.DS_Store"` (correct command for deletion)
  - **Line 122**: Fixed filename typo
    - Was: `setting.json` (missing 's')
    - Now: `settings.json` (correct filename)
  - **Line 125**: Fixed machrc operation and path
    - Was: "Append `~/dotfiles/mozilla/machrc` into `~/.mozbuild/machrc`"
    - Now: "Link `~/dotfiles/mozilla/gecko/machrc` to `~/.mozbuild/machrc`"
    - Reason: setup.py:332 uses link() to create symlink, not append
- **Impact**: LOW - Documentation cleanup, now matches implementation

## Priority 7: Code Quality & Simplification

### [x] 7.1 Simplify Mozilla argument parsing ✅
- **File**: `setup.py:312-318` (was 191-201, line numbers changed after previous edits)
- **Issue**: Over-engineered set intersections with double set conversion
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - Replaced `set(funcs.keys()).intersection(set(args.mozilla))` with simple if-else block
  - Used list comprehension: `[k for k in args.mozilla if k in funcs]`
  - Added clear explanatory comments for each branch
  - Preserves user-specified order (improvement over set intersection)
- **Implementation**:
  ```python
  # Select which Mozilla tools to install
  if args.mozilla:
      # User specified tools: filter to valid options only
      options = [k for k in args.mozilla if k in funcs]
  else:
      # No tools specified: install all
      options = list(funcs.keys())
  ```
- **Testing**: 7/7 tests passed (see TESTING_RESULTS_MOZILLA_PARSING.md)
  - Syntax validation ✅
  - 6 logic test cases ✅ (empty list, specific tools, single tool, valid+invalid, all invalid, all tools)
  - Functional equivalence confirmed (old vs new produce identical results) ✅
- **Improvements**:
  1. Removed double set conversion (performance improvement)
  2. Replaced verbose .intersection() with readable list comprehension
  3. Added clear comments explaining intent
  4. More maintainable and easier to modify
  5. Preserves user-specified order
  6. Functionally equivalent to original
- **Impact**: MEDIUM - Improved code quality and maintainability, quick win (15 min)
- **Time**: 15 minutes (as estimated in topological analysis)

### [x] 7.2 Standardize function naming conventions ✅
- **Issue**: Inconsistent naming across languages
- **Status**: COMPLETED (2026-01-08)
- **Decision**: Accept and document language-specific naming conventions
- **Changes made**:
  - Added comprehensive "Naming Conventions" section to CLAUDE.md (lines 158-183)
  - Documented Python conventions (snake_case for functions, follows PEP 8)
  - Documented Bash conventions (PascalCase for functions, distinguishes from commands)
  - Provided clear rationale for language-specific approach
  - Added contributor guidelines
- **Current state (now documented)**:
  - Python: `print_hint()`, `print_warning()` (snake_case - follows PEP 8)
  - Bash: `PrintError()`, `PrintWarning()` (PascalCase - distinguishes from commands)
- **Rationale**:
  1. Python PEP 8 is the official style guide (widely expected)
  2. Bash PascalCase distinguishes custom functions from Unix commands
  3. Each language is internally consistent (most important for readability)
  4. Follows established conventions rather than inventing new ones
- **Testing**: 4/4 verification checks passed (see TESTING_RESULTS_NAMING_CONVENTIONS.md)
  - Current naming patterns verified ✅
  - Convention decision rationale provided ✅
  - Documentation added to CLAUDE.md ✅
  - Documentation clarity verified ✅
- **Impact**: LOW effort (30 min), provides clarity for future contributors, no code changes
- **Time**: 30 minutes (matched estimate from topological analysis)

### [ ] 7.3 Review and optimize git/utils.sh functions
- **File**: `git/utils.sh`
- **Issue**: Several functions could be simplified
- **Action**:
  - Review CreateGitBranchForPullRequest for edge cases
  - Simplify GitAddExcept logic if possible
  - Ensure all git commands handle errors properly

## Priority 8: Testing & Verification

### [ ] 8.1 Create test suite for setup.py
- **Issue**: No automated tests
- **Action**: Add unit tests for:
  - Path handling functions
  - File operations
  - Symlink creation/checking
  - Append operations

### [ ] 8.2 Create test suite for shell utilities
- **Issue**: No automated tests for shell functions
- **Action**: Use bats (Bash Automated Testing System) or similar to test:
  - RecursivelyFind
  - RecursivelyRemove
  - Git utility functions
  - Platform detection

### [ ] 8.3 Test cross-platform compatibility
- **Issue**: Limited testing on different platforms
- **Action**:
  - Test on macOS 11+ (Big Sur, Monterey, Ventura)
  - Test on various Linux distros
  - Document any platform-specific quirks

## Optional Enhancements

### [ ] 9.1 Add dry-run mode to setup.py
- **Action**: Add `--dry-run` flag to show what would be done without doing it

### [x] 9.2 Add verbose mode for debugging ✅
- **File**: `setup.py`
- **Status**: COMPLETED (2026-01-08)
- **Changes made**:
  - Added global VERBOSE flag (line 14)
  - Added print_verbose() function (lines 176-179)
  - Integrated argparse in main() with -v/--verbose and --mozilla flags (lines 657-681)
  - Modified mozilla_init() to accept mozilla_arg parameter (lines 302-336)
  - Added verbose messages to key operations (21+ verbose statements total)
- **Implementation**:
  ```python
  # Global flag
  VERBOSE = False  # Set to True with -v/--verbose flag

  # Verbose print function
  def print_verbose(message):
      if VERBOSE:
          print(colors.HEADER + '[VERBOSE] ' + colors.END + message)

  # Argument parsing in main()
  parser.add_argument('-v', '--verbose', action='store_true',
                      help='Show detailed operations for debugging')
  ```
- **Verbose messages added to**:
  - link() function: source/target validation, symlink operations (8 messages)
  - dotfiles_link(): function entry/exit (2 messages)
  - bash_link(): platform detection, file processing, completion (5 messages)
  - mozilla_init(): argument parsing, tool selection (3 messages)
  - main(): command-line arguments, directories (3 messages)
- **Features**:
  - Both -v and --verbose work identically
  - Works with all existing flags (--mozilla, etc.)
  - No behavior changes (only adds debug output)
  - Helpful --help with usage examples
  - Blue [VERBOSE] prefix for easy identification
- **Testing**: 7/7 tests passed (see TESTING_RESULTS_VERBOSE_MODE.md)
  - Syntax validation ✅
  - Help message shows verbose option ✅
  - Normal mode: no verbose output ✅
  - Verbose mode (-v): shows debug info ✅
  - Verbose mode (--verbose): works identically ✅
  - Verbose + Mozilla: both flags work together ✅
  - No functional changes ✅
- **Impact**: HIGH - Significantly improved debugging experience, better user understanding
- **Time**: 30 minutes (matched estimate from topological analysis)

### [ ] 9.3 Improve uninstall automation
- **Action**: Make uninstall.sh fully automatic (address all TODO comments)

### [ ] 9.4 Add pre-commit hooks
- **Action**: Add hooks to check:
  - Shell script syntax (shellcheck)
  - Python code quality (ruff/pylint)
  - Markdown formatting

### [ ] 9.5 Consider configuration file
- **Action**: Add optional `~/.dotfiles.conf` for user customization

---

## Quick Wins (Can be done immediately)

1. [x] Fix typo in setup.py:280 (`bachrc` → `bashrc`) (DONE - see 6.1)
2. [x] Add quotes around variable expansions in shell scripts (DONE - see 3.1)
3. [x] Replace `ls` parsing with `readlink` in uninstall.sh (DONE - see 1.2)
4. [x] Use git ls-files with -z in git/utils.sh (DONE - see 1.3)
5. [x] Fix bare except in setup.py (DONE - see 1.4)

---

## Progress Tracking

### Phase Overview
- **Total items**: 40+
- **Complete**: 22 items (55.0%)
- **Processing**: 1 item (2.5%)
- **Pending**: 17 items (42.5%)
- **Last updated**: 2026-01-08

### Phase: Complete ✅ (22 items)
  - Item 1.1: Fixed dangerous eval usage (code injection vulnerability)
  - Item 1.2: Fixed fragile file path handling in uninstall.sh
  - Item 1.3: Fixed git status parsing to handle spaces in filenames
  - Item 1.4: Fixed bare exception catching in setup.py
  - Item 1.5: Fixed macOS version parsing bug
  - Item 2.1: Consolidate duplicate print/color functions
  - Item 2.2: Standardized path construction in setup.py
  - Item 2.3: Fix inverted logic in CommandExists
  - Item 3.1: Quote all variable expansions in shell scripts
  - Item 3.2: Fix fragile alias quoting
  - Item 3.3: Improve RecursivelyRemove safety
  - Item 4.2: Make script location detection robust
  - Item 5.1: Add file existence checks (prevents crashes)
  - Item 5.2: Fix append_nonexistent_lines_to_file (critical bug)
  - Item 5.3: Add error exit codes for silent failures
  - Item 5.4: Add installation verification step
  - Item 6.1: Fixed typo in error message
  - Item 6.2: Resolved outdated TODO comments (codebase now TODO-free)
  - Item 6.3: Fixed README documentation mismatches
  - Item 7.1: Simplify Mozilla argument parsing
  - Item 7.2: Standardize function naming conventions
  - Item 9.2: Add verbose mode for debugging

### Phase: Processing 🔄 (1 item)
  - Item 8.1: Create test suite for setup.py

### Phase: Pending ⏳ (17 items)
  - Item 4.1: Extract hardcoded paths to configuration
  - Item 5.5: Add rollback mechanism for failed setups
  - Item 7.3: Review and optimize git/utils.sh functions
  - Item 8.2: Create test suite for shell utilities
  - Item 8.3: Test cross-platform compatibility
  - Item 9.1: Add dry-run mode to setup.py
  - Item 9.3: Improve uninstall automation
  - Item 9.4: Add pre-commit hooks
  - Item 9.5: Consider configuration file

**🎉 MILESTONE: ALL PRIORITY 1 (CRITICAL) ITEMS COMPLETE! 🎉**
- ✅ All critical security vulnerabilities eliminated
- ✅ All reliability issues fixed
- ✅ Codebase significantly more robust and secure

**🎉 MILESTONE: ALL PRIORITY 2 (CODE DUPLICATION) ITEMS COMPLETE! 🎉**
- ✅ Print functions consolidated (single source of truth)
- ✅ Path construction standardized (cross-platform)
- ✅ CommandExists fixed (follows Unix convention)

**🎉 MILESTONE: ALL PRIORITY 3 (SHELL SCRIPT ROBUSTNESS) ITEMS COMPLETE! 🎉**
- ✅ All shell variables properly quoted
- ✅ Fragile alias quoting fixed (converted to function)
- ✅ RecursivelyRemove now safe with preview & confirmation

**🎉 MILESTONE: PRIORITY 5 (ERROR HANDLING) 80% COMPLETE! 🎉**
- ✅ Item 5.1: File existence checks (prevents 4 crash points)
- ✅ Item 5.2: append_nonexistent_lines_to_file fix (critical false positive bug)
- ✅ Item 5.3: Error exit codes (proper tracking and exit codes)
- ✅ Item 5.4: Installation verification (verifies setup actually worked)
- ⬜ Item 5.5: Rollback mechanism (remaining)

**🎉 MILESTONE: ALL PRIORITY 6 (DOCUMENTATION) ITEMS COMPLETE! 🎉**
- ✅ Item 6.1: Fixed typo in setup.py error message
- ✅ Item 6.2: Resolved all TODO comments (codebase now TODO-free)
- ✅ Item 6.3: Fixed README documentation mismatches
- ✅ Documentation now accurate and matches implementation

**🎉 MILESTONE: ENTIRE CODEBASE NOW TODO-FREE! 🎉**
- ✅ All outdated TODOs resolved (Item 6.2)
- ✅ uninstall.sh: 0 TODOs (was 3)
- ✅ setup.py: 0 TODOs (already clean)
- ✅ Design decisions documented, no confusion about incomplete work

**Key Achievements**:
- Item 1.1: Eliminated CRITICAL code injection vulnerability (CVSS 9.8)
- Item 2.1: Established single source of truth for print functions (22 lines removed)
- Item 2.2 unblocks 8+ Python-related improvements (4.1, 5.1-5.2, 7.1, 8.1)
- Item 2.3: Fixed confusing inverted logic, improved code clarity (5 files updated initially, 3 more fixed after power outage)
- Item 3.1 unblocks 4 shell-related improvements (3.2, 3.3, 7.3, 8.2)
- Item 1.4 improves security (Ctrl+C works) and debugging (error messages)
- Item 5.1: Added file existence checks at 4 crash points (prevents OSError/FileNotFoundError, validates repository)
- Item 5.2: Fixed CRITICAL false positive bug in append function (foundational fix, unblocks 5.4 & 8.1)
- Item 5.3: Added error exit codes (8 functions modified, proper exit codes enable automation, clear summary feedback)
- Item 5.4: Added installation verification (5 functions, 229 lines, verifies symlinks/files/bash/git, ~300ms overhead)
- Item 6.2: Entire codebase now TODO-free (professional appearance, clear design documentation)
- Item 6.3: All Priority 6 complete - documentation now accurate and matches implementation

**Recent Fixes (2026-01-08)**:
1. **Completed Item 2.3 fully**: Fixed 3 missed call sites (dot.settings_linux, dot.settings_darwin, dot.bash_profile)
   - Root cause: Power outage interrupted previous session, left 3 files with old CommandExists logic
   - Impact: Eliminated "bash: [: -eq: unary operator expected" errors on terminal startup
   - All 8 CommandExists call sites now use correct Unix convention (return codes, not echo)

2. **Verified Item 4.2 complete**: Script location detection (already fixed in Item 1.2)
   - Created comprehensive test suite: 13 tests covering all scenarios
   - All tests passed: directory independence, symlink support, file path resolution
   - Documented in TESTING_RESULTS_ITEM_4.2.md
   - Impact: Confirmed uninstall.sh works from any directory, not just repo root

---

## Dependency Analysis & Topological Ordering

This section provides a comprehensive dependency map and topological ordering for pending items, helping identify the most valuable items to work on next.

### Dependency Map Legend
- **→** Facilitates/Enables (completing this helps the target)
- **←** Depends on/Benefits from (needs this for optimal completion)
- **↔** Related/Overlapping (can be combined or done together)
- **Level N** - Topological level (lower levels should be done first)

### Visual Dependency Graph

```
Level 0 (No dependencies - Quick Wins):
┌─────────────────────────────────────────┐
│ 7.1 Simplify Mozilla parsing            │ → [8.1]
│ 7.2 Standardize naming (doc only)       │ → [8.1, 8.2]
│ 9.2 Add verbose mode                    │ → [general quality]
└─────────────────────────────────────────┘
              ↓
Level 1 (High Priority - Enable Many Others):
┌─────────────────────────────────────────┐
│ 8.1 Test suite for setup.py ⭐⭐⭐      │ → [4.1, 5.5, 9.1, 9.4]
│     (Facilitates 5 items)                │
│                                          │
│ 8.2 Test suite for shell utilities ⭐⭐ │ → [7.3, 9.3, 9.4]
│     (Facilitates 3 items)                │
└─────────────────────────────────────────┘
              ↓
Level 2 (Mid Priority - Depend on Tests or Independent):
┌─────────────────────────────────────────┐
│ 4.1 Extract hardcoded paths             │ → [9.5]
│     (Easier with 8.1)                    │
│                                          │
│ 7.3 Review git/utils.sh                 │
│     (Safer with 8.2)                     │
│                                          │
│ 9.1 Dry-run mode                         │
│     (Benefits from 8.1)                  │
│                                          │
│ 9.3 Improve uninstall automation        │
│     (Benefits from 8.2)                  │
└─────────────────────────────────────────┘
              ↓
Level 3 (Final Polish - Depend on Multiple Items):
┌─────────────────────────────────────────┐
│ 5.5 Rollback mechanism                  │
│     (Depends on 8.1, builds on 5.1-5.4) │
│                                          │
│ 8.3 Cross-platform testing              │
│     (Needs 8.1, 8.2)                     │
│                                          │
│ 9.4 Pre-commit hooks                    │
│     (Uses tests from 8.1, 8.2)          │
│                                          │
│ 9.5 Configuration file                  │
│     (Overlaps with 4.1)                  │
└─────────────────────────────────────────┘
```

### Topological Order (Recommended Execution Sequence)

**Priority Tier 1: Foundation Builders** ⚡🔥
1. **7.1** - Simplify Mozilla argument parsing (15 min, quick win)
2. **7.2** - Standardize naming conventions (30 min, documentation)
3. **9.2** - Add verbose mode (30 min, quick win)
4. **8.1** - Test suite for setup.py ⭐⭐⭐ (HIGH VALUE - facilitates 5 items)
5. **8.2** - Test suite for shell utilities ⭐⭐ (HIGH VALUE - facilitates 3 items)

**Priority Tier 2: Core Improvements** 🔧
6. **4.1** - Extract hardcoded paths (now safe with tests)
7. **7.3** - Review git/utils.sh (now safe with tests)
8. **9.1** - Dry-run mode (enabled by 8.1)
9. **9.3** - Improve uninstall automation (enabled by 8.2)

**Priority Tier 3: Advanced Features** 🚀
10. **5.5** - Rollback mechanism (builds on completed 5.1-5.4 + 8.1)
11. **8.3** - Cross-platform testing (uses 8.1, 8.2)
12. **9.4** - Pre-commit hooks (integrates 8.1, 8.2 tests)
13. **9.5** - Configuration file (combine with 4.1 if desired)

### Value Analysis Matrix

**Critical Path Items** (most valuable - unblock/facilitate many others):
- **8.1** → Facilitates 5 items: 4.1, 5.5, 9.1, 9.2, 9.4 (HIGHEST VALUE)
- **8.2** → Facilitates 3 items: 7.3, 9.3, 9.4 (HIGH VALUE)
- **4.1** → Facilitates 2 items: 8.1 (easier), 9.5 (overlap)

**Effort vs Impact Scoring**:
```
Item  │ Effort │ Impact │ Facilitates │ Score │ Level │ Priority
──────┼────────┼────────┼─────────────┼───────┼───────┼──────────
8.1   │ High   │ V.High │ 5 items     │ 95/100│ L1    │ ⭐⭐⭐
8.2   │ High   │ V.High │ 3 items     │ 90/100│ L1    │ ⭐⭐
7.1   │ Low    │ Low    │ 0 items     │ 70/100│ L0    │ ⚡ Quick
7.2   │ Low    │ Low    │ 0 items     │ 65/100│ L0    │ ⚡ Quick
9.2   │ Low    │ Medium │ 0 items     │ 75/100│ L0    │ ⚡ Quick
4.1   │ Medium │ High   │ 1 item      │ 80/100│ L2    │ 🔧
7.3   │ Medium │ Medium │ 0 items     │ 70/100│ L2    │ 🔧
9.1   │ Medium │ Medium │ 0 items     │ 65/100│ L2    │ 🔧
9.3   │ Medium │ Medium │ 0 items     │ 65/100│ L2    │ 🔧
5.5   │ M-High │ High   │ 0 items     │ 75/100│ L3    │ 🚀
8.3   │ Medium │ Medium │ 0 items     │ 70/100│ L3    │ 🚀
9.4   │ Medium │ Medium │ 0 items     │ 70/100│ L3    │ 🚀
9.5   │ Medium │ Medium │ 0 items     │ 65/100│ L3    │ 🚀
```

### Recommended Next Steps

**Option A: Maximum Impact Strategy** 🎯
Start with the highest-value items that facilitate the most work:
1. Do all 3 quick wins (7.1, 7.2, 9.2) in 1 hour → Build momentum
2. Tackle 8.1 (test suite for setup.py) → Unlocks 5 items
3. Tackle 8.2 (test suite for shell) → Unlocks 3 items
4. Then work through Level 2 items with confidence

**Option B: Quick Wins First Strategy** ⚡
Build momentum with easy victories before heavy lifting:
1. 7.1 (15 min) → Immediate improvement
2. 7.2 (30 min) → Documentation cleanup
3. 9.2 (30 min) → User-facing feature
4. Then move to 8.1 and 8.2

**Option C: Test-Driven Strategy** 🧪
Establish testing foundation immediately:
1. 8.1 first → Enables confident refactoring of setup.py
2. 8.2 second → Enables confident refactoring of shell scripts
3. Everything else becomes safer and easier

### Blocking Analysis

**Items with NO blockers** (can start immediately):
- 4.1, 7.1, 7.2, 7.3, 8.1, 8.2, 9.1, 9.2, 9.3

**Items with soft dependencies** (better to wait):
- 5.5 (better with 8.1)
- 8.3 (better with 8.1, 8.2)
- 9.4 (better with 8.1, 8.2)
- 9.5 (overlaps with 4.1)

**No hard blockers** - All pending items CAN be started now, but the topological order optimizes efficiency and safety.

---

## Dependency Analysis & Recommended Order

This section helps prioritize work by showing dependencies between pending items.

### Dependency Legend
- **→** Blocks/Facilitates (completing this helps with the target)
- **←** Depends on (needs this to be done first)
- **↔** Related/Overlapping (could be done together)

### Item Dependencies Map

#### Priority 4: Configuration & Hardcoded Paths
- **4.1** Extract hardcoded paths
  - Dependencies: None (can be done independently)
  - Facilitates: 8.1 (tests), 9.5 (config file)
  - Complexity: Medium (7 files affected)
  - Impact: Makes codebase more maintainable and testable

- **4.2** Make script location detection robust ✅ COMPLETE
  - Status: Already fixed in Item 1.2 (commit ac82207, 2026-01-07)
  - Testing: 13/13 tests passed (2026-01-08)
  - Impact: Script now works from any directory, not just repo root

#### Priority 5: Error Handling
- **5.5** Add rollback mechanism
  - Dependencies: ✅ 5.1-5.4 complete (foundation exists)
  - Would benefit from: 8.1 (tests to validate rollback)
  - Facilitates: Setup reliability, user confidence
  - Complexity: Medium-High
  - Impact: Allows safe recovery from failed setups

#### Priority 7: Code Quality & Simplification
- **7.1** Simplify Mozilla argument parsing
  - Dependencies: None (can be done independently)
  - Facilitates: Code maintainability
  - Complexity: Low (straightforward refactor)
  - Impact: Cleaner, more readable code
  - **QUICK WIN** ⚡

- **7.2** Standardize function naming conventions
  - Dependencies: None
  - Affects: 8.1, 8.2 (if renaming functions)
  - Complexity: Low (just documentation) OR Medium-High (if renaming)
  - Impact: Better code consistency
  - Note: Recommend documenting convention rather than renaming

- **7.3** Review and optimize git/utils.sh
  - Dependencies: None (can be done independently)
  - Would benefit from: 8.2 (tests to validate changes)
  - Facilitates: Git workflow reliability
  - Complexity: Medium
  - Impact: More robust git utilities

#### Priority 8: Testing & Verification
- **8.1** Create test suite for setup.py
  - Dependencies: None (can start immediately)
  - **Facilitates many items**: 4.1, 5.5, 9.1, 9.2, 9.4
  - Complexity: High (comprehensive suite needed)
  - Impact: **VERY HIGH** - Prevents regressions, enables confident refactoring
  - **HIGH PRIORITY** 🔥

- **8.2** Create test suite for shell utilities
  - Dependencies: None (can start immediately)
  - **Facilitates**: 7.3, 9.3, 9.4
  - Complexity: High (bats framework setup + comprehensive tests)
  - Impact: **VERY HIGH** - Prevents regressions, validates shell code
  - **HIGH PRIORITY** 🔥

- **8.3** Test cross-platform compatibility
  - Dependencies: None (can be done anytime)
  - Would benefit from: 8.1, 8.2 (automated tests)
  - Complexity: Medium (requires multiple platforms)
  - Impact: Ensures reliability across Linux/macOS

#### Priority 9: Optional Enhancements
- **9.1** Add dry-run mode
  - Dependencies: None
  - Would benefit from: 8.1 (tests)
  - Complexity: Medium
  - Impact: Safer setup testing

- **9.2** Add verbose mode
  - Dependencies: None
  - Complexity: Low-Medium
  - Impact: Better debugging
  - **QUICK WIN** ⚡

- **9.3** Improve uninstall automation
  - Dependencies: None
  - Would benefit from: 8.2 (tests)
  - Complexity: Medium
  - Impact: Better user experience

- **9.4** Add pre-commit hooks
  - Dependencies: None
  - Would benefit from: 8.1, 8.2 (tests can run in hooks)
  - Complexity: Low-Medium
  - Impact: Prevents committing broken code

- **9.5** Consider configuration file
  - ↔ Related to 4.1 (overlapping - could be combined)
  - Dependencies: None
  - Complexity: Medium
  - Impact: User customization

### Recommended Work Order

#### Phase 1: Quick Wins (Low effort, immediate value)
Do these first for quick progress:
1. ~~**4.2** - Script location detection~~ ✅ COMPLETE
2. **7.1** - Simplify Mozilla argument parsing (15 minutes)
3. **9.2** - Add verbose mode (30 minutes)

#### Phase 2: Foundation for Quality (Enables future work)
Critical for long-term maintainability:
4. **8.1** - Test suite for setup.py (HIGH PRIORITY - facilitates 5 other items)
5. **8.2** - Test suite for shell utilities (HIGH PRIORITY - facilitates 3 other items)

#### Phase 3: Configuration & Refactoring (With tests in place)
Now safer to refactor with test coverage:
6. **4.1** - Extract hardcoded paths (easier to test with 8.1 complete)
7. **7.3** - Review git/utils.sh (safer with 8.2 complete)

#### Phase 4: Advanced Features (Building on foundation)
8. **5.5** - Rollback mechanism (depends on 5.1-5.4 ✅, benefits from 8.1)
9. **8.3** - Cross-platform testing (easier with 8.1, 8.2)

#### Phase 5: Polish & Enhancements (Optional)
10. **7.2** - Standardize naming (documentation)
11. **9.1** - Dry-run mode
12. **9.3** - Uninstall automation
13. **9.4** - Pre-commit hooks
14. **9.5** - Configuration file (or combine with 4.1)

### Complexity vs Impact Matrix

```
High Impact │ 8.1 ████  8.2 ████  │ 4.1 ██    5.5 ██
            │ (Test setup.py)    │ (Config)  (Rollback)
            │                    │
Medium      │ 7.3 ██    4.2 █    │ 9.1 █     9.3 █
Impact      │ (Git utils)        │ (Dry-run) (Uninstall)
            │                    │
Low Impact  │ 7.1 █     9.2 █    │ 7.2 █     9.4 █  9.5 █
            │ (Simplify) (Verbose)│ (Naming)  (Hooks)(Config)
            └────────────────────┴─────────────────────
              Low-Medium Complexity   Medium-High Complexity
```

### Critical Path Items

Items that **unblock or facilitate the most other items**:
1. **8.1** (Test suite for setup.py) → facilitates 5 items: 4.1, 5.5, 9.1, 9.2, 9.4
2. **8.2** (Test suite for shell) → facilitates 3 items: 7.3, 9.3, 9.4
3. **4.1** (Extract hardcoded paths) → overlaps with 9.5, makes 8.1 easier

**Recommendation**: Start with Phase 1 quick wins, then prioritize 8.1 and 8.2 to enable confident refactoring.

---

## Notes

- Items are ordered by priority within each section
- Some items may be interdependent (see Dependency Analysis above)
- Test after each change to ensure nothing breaks
- Consider creating feature branches for major refactoring
- Update CLAUDE.md after significant changes
- **Use the Recommended Work Order** above to maximize efficiency
