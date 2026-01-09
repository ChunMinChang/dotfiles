# Testing Guide

This document describes the test suites in this repository and when to run them.

## Test Suites

### 1. Setup Script Tests (`test_setup.py`)

**Purpose**: Validates the Python setup script functionality.

**When to run**:
- After modifying `setup.py`
- Before committing changes to setup logic
- When testing on a new platform
- After updating Python dependencies

**How to run**:
```bash
python test_setup.py
```

**Expected results**:
```
Tests run:    22
Tests passed: 22
Tests failed: 0

✓ All tests passed!
```

**What it validates**:
- Platform detection (Linux, macOS)
- macOS version detection
- File path handling and symlink creation
- Configuration file parsing
- Mozilla tools setup logic
- Error handling and edge cases
- Non-interactive mode support (CI/CD compatibility)

**Test coverage**: 22 tests covering all setup.py functions

---

### 2. Shell Utilities Tests (`test_shell_utils.sh`)

**Purpose**: Validates shell utility functions in `utils.sh` and `git/utils.sh`.

**When to run**:
- After modifying `utils.sh` or `git/utils.sh`
- Before committing changes to shell functions
- When testing on a new platform or shell
- After adding new shell utilities

**How to run**:
```bash
bash test_shell_utils.sh
```

**Expected results**:
```
Tests run:    19
Tests passed: 19
Tests failed: 0

✓ All tests passed!
```

**What it validates**:
- Print functions (PrintError, PrintHint, PrintWarning)
- CommandExists function
- RecursivelyRemove function
- Git utility functions (ParseGitBranch, GitAddExcept, etc.)
- Error handling and edge cases
- Cross-platform compatibility

**Test coverage**: 19 tests covering all major utility functions

---

### 3. Prompt Colors Tests (`test_prompt_colors.sh`)

**Purpose**: Validates prompt color functionality across shells and platforms.

**When to run**:
- After modifying `git/utils.sh` (especially BranchInPrompt)
- After modifying `dot.zshrc` prompt configuration
- Before committing changes to prompt customization
- When testing on a new platform or shell
- When adding support for new shells

**How to run**:
```bash
bash test_prompt_colors.sh
```

**Expected results on systems with both bash and zsh**:
```
Tests run:    22
Tests passed: 22
Tests failed: 0

✓ All tests passed!
```

**Expected results on systems with only bash** (e.g., minimal Linux):
```
Tests run:    22
Tests passed: 12
Tests failed: 10

✗ Some tests failed (zsh tests skipped - zsh not installed)
```

**What it validates**:
- Bash escape sequences (`\[` `\]`)
- Zsh escape sequences (`%{` `%}`)
- Shell detection logic (BASH_VERSION vs ZSH_VERSION)
- ParseGitBranch output format
- BranchInPrompt behavior in both shells
- RPROMPT disabled in zsh (no duplicate branch display)
- Cross-platform compatibility (Linux, macOS, BSD)
- No literal escape sequences in output

**Test coverage**: 22 tests covering:
- 3 bash-specific escape sequence tests
- 3 zsh-specific escape sequence tests
- 2 ParseGitBranch tests (bash and zsh)
- 2 shell detection tests
- 2 no-literal-escape tests
- 2 RPROMPT disabled tests (zsh only)
- 4 function existence tests
- 2 cross-platform compatibility tests
- 2 clean loading tests

**Design principles**:
1. **Platform-independent**: Tests run on any platform (Darwin, Linux, BSD)
2. **Shell-agnostic**: Tests both bash and zsh on any platform
3. **Graceful degradation**: If zsh unavailable, zsh tests are skipped
4. **Explicit shell selection**: Uses `bash -c` and `zsh -c` to test specific shells

---

## Running All Tests

To run all test suites in sequence:

```bash
echo "=== Running Setup Tests ===" && \
python test_setup.py && \
echo -e "\n=== Running Shell Utilities Tests ===" && \
bash test_shell_utils.sh && \
echo -e "\n=== Running Prompt Colors Tests ===" && \
bash test_prompt_colors.sh
```

---

## Continuous Integration

All tests are designed to work in CI/CD environments:

- **Non-interactive mode**: `setup.py` detects TTY absence and uses defaults
- **No user input required**: Tests run without prompts
- **Deterministic results**: Same input produces same output
- **Exit codes**: Tests exit 0 on success, non-zero on failure

Example GitHub Actions workflow:
```yaml
- name: Run tests
  run: |
    python test_setup.py
    bash test_shell_utils.sh
    bash test_prompt_colors.sh
```

---

## Adding New Tests

### For Python Tests (`test_setup.py`)

```python
def test_new_feature():
    """Test description"""
    global TESTS_RUN, TESTS_PASSED, TESTS_FAILED
    TESTS_RUN += 1

    try:
        # Test logic here
        result = some_function()
        assert result == expected

        print_pass("Test name")
        TESTS_PASSED += 1
    except AssertionError as e:
        print_fail(f"Test should do X: {e}")
        TESTS_FAILED += 1
```

### For Shell Tests (`test_shell_utils.sh` or `test_prompt_colors.sh`)

```bash
test_new_feature() {
    TESTS_RUN=$((TESTS_RUN + 1))

    # Test logic here
    result=$(some_function)

    if [[ "$result" == "expected" ]]; then
        print_pass "Test description"
    else
        print_fail "Test should do X, got: $result"
    fi
}
```

---

## Test Philosophy

1. **Test before committing**: Run relevant tests before committing changes
2. **Platform coverage**: Test on both Linux and macOS when possible
3. **Shell coverage**: Test in both bash and zsh when modifying shell code
4. **Edge cases**: Include tests for error conditions and edge cases
5. **Clear output**: Tests should clearly indicate what passed or failed
6. **Self-documenting**: Test names and messages should explain what's being tested

---

## Troubleshooting

### Tests fail on macOS but pass on Linux
- Check shell-specific code (bash vs zsh)
- Verify escape sequences are appropriate for the shell
- Check platform detection logic

### Tests fail in CI/CD but pass locally
- Verify non-interactive mode support
- Check for TTY-dependent behavior
- Ensure no user input is required

### Zsh tests fail with "command not found"
- This is expected if zsh is not installed
- Install zsh: `brew install zsh` (macOS) or `apt install zsh` (Linux)
- Or accept that zsh tests will be skipped

### All tests fail immediately
- Check that you're running from the repository root
- Verify the test file has execute permissions: `chmod +x test_*.sh`
- Ensure dependencies are installed (git, python3, bash)

---

**Last Updated**: 2026-01-09
**Test Coverage**: 63 total tests across 3 suites
**Platforms**: Linux (Ubuntu 22.04+), macOS (10.15+)
**Shells**: bash, zsh
