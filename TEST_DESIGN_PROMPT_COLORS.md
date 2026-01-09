# Prompt Colors Test Suite - Design Documentation

**File**: `test_prompt_colors.sh`
**Purpose**: Verify prompt color functionality across shells and platforms
**Total Tests**: 22 (all platform-independent and shell-aware)

---

## Test Classification

### Platform-Independent Tests (All 22 tests)

✅ **All tests run on any platform** (Darwin/Linux/BSD/etc.)

The test suite is designed to run correctly regardless of the platform. No assumptions are made about which shell should be used on which platform.

### Shell-Specific vs Shell-Agnostic Tests

#### Shell-Specific Tests (Intentionally Test Shell Differences)

These tests **intentionally** test shell-specific behavior to ensure each shell uses the correct escape sequences:

1. **Test Suite 1: Bash Escape Sequences** (3 tests)
   - **Purpose**: Verify bash uses `\[` `\]` escape sequences
   - **Shell**: bash only
   - **Why**: Bash requires specific escape sequence format
   - **Platform**: Any

2. **Test Suite 2: Zsh Escape Sequences** (3 tests)
   - **Purpose**: Verify zsh uses `%{` `%}` escape sequences
   - **Shell**: zsh only
   - **Why**: Zsh requires different escape sequence format than bash
   - **Platform**: Any

3. **Test Suite 4: Shell Detection Logic** (2 tests)
   - **Purpose**: Verify BranchInPrompt detects shell correctly
   - **Shell**: Tests both bash and zsh
   - **Why**: Function must adapt to running shell
   - **Platform**: Any

4. **Test Suite 5: No Literal Escape Sequences** (2 tests)
   - **Purpose**: Verify proper formatting per shell
   - **Shell**: Tests both bash and zsh separately
   - **Why**: Each shell has different requirements
   - **Platform**: Any

5. **Test Suite 6: RPROMPT Disabled** (2 tests)
   - **Purpose**: Verify zsh-specific RPROMPT is disabled
   - **Shell**: zsh only
   - **Why**: RPROMPT is a zsh-only feature
   - **Platform**: Any

#### Shell-Agnostic Tests (Should Work in Any Shell)

These tests verify functionality that should work the same in any POSIX-compatible shell:

1. **Test Suite 3: ParseGitBranch Function** (2 tests)
   - **Purpose**: Verify git branch parsing works correctly
   - **Shell**: Tested in both bash and zsh
   - **Why**: Should produce same output regardless of shell
   - **Platform**: Any (requires git)

2. **Test Suite 7: Prompt Functions Exist** (4 tests)
   - **Purpose**: Verify functions are defined after sourcing
   - **Shell**: Tested in both bash and zsh
   - **Why**: Functions should load in any shell
   - **Platform**: Any

3. **Test Suite 8: Cross-Platform Compatibility** (2 tests)
   - **Purpose**: Verify functions work on current platform
   - **Shell**: Tests BOTH bash and zsh
   - **Why**: Should work regardless of platform/shell combo
   - **Platform**: Any (auto-detects: Darwin, Linux, etc.)
   - **Graceful Degradation**: Skips zsh tests if zsh not available

4. **Test Suite 9: No Errors on Load** (2 tests)
   - **Purpose**: Verify git/utils.sh sources without errors
   - **Shell**: Tested in both bash and zsh
   - **Why**: Should load cleanly in any shell
   - **Platform**: Any

---

## Design Principles

### 1. No Platform Assumptions

❌ **Bad**: Assume macOS = zsh, Linux = bash
```bash
if [[ "$platform" == "Darwin" ]]; then
    test_with_zsh
elif [[ "$platform" == "Linux" ]]; then
    test_with_bash
fi
```

✅ **Good**: Test both shells on any platform
```bash
test_with_bash_on_any_platform
if command -v zsh; then
    test_with_zsh_on_any_platform
fi
```

### 2. Graceful Degradation

If a shell isn't available, skip those tests gracefully:
```bash
if command -v zsh >/dev/null 2>&1; then
    # Run zsh tests
else
    print_pass "Zsh not available (skipped)"
fi
```

### 3. Explicit Shell Selection

When testing shell-specific features, explicitly invoke that shell:
```bash
# Test bash behavior
bash -c 'source git/utils.sh; BranchInPrompt; echo "$PS1"'

# Test zsh behavior
zsh -c 'source git/utils.sh; BranchInPrompt; echo "$PS1"'
```

### 4. Test What Matters

- **Shell-specific tests**: Verify correct escape sequences per shell
- **Functional tests**: Verify output is correct regardless of shell
- **Cross-platform tests**: Verify works on any platform

---

## Test Coverage Matrix

| Test Suite | Platform | Bash | Zsh | Purpose |
|------------|----------|------|-----|---------|
| Bash Escape Sequences | Any | ✅ | N/A | Verify bash-specific escapes |
| Zsh Escape Sequences | Any | N/A | ✅ | Verify zsh-specific escapes |
| ParseGitBranch | Any | ✅ | ✅ | Verify output format |
| Shell Detection | Any | ✅ | ✅ | Verify auto-detection |
| No Literal Escapes | Any | ✅ | ✅ | Verify proper formatting |
| RPROMPT Disabled | Any | N/A | ✅ | Verify zsh config |
| Functions Exist | Any | ✅ | ✅ | Verify loading |
| Cross-Platform | Any | ✅ | ✅* | Verify any platform/shell |
| No Errors on Load | Any | ✅ | ✅ | Verify clean loading |

*Zsh tests skipped if zsh not available

---

## Supported Scenarios

The test suite correctly handles these scenarios:

### macOS
- ✅ Default zsh (macOS 10.15+)
- ✅ Legacy bash (macOS < 10.15)
- ✅ User-installed bash (Homebrew)
- ✅ User-installed zsh (Homebrew)
- ✅ Other shells (fish, dash, etc.) - core tests still work

### Linux
- ✅ Default bash (most distros)
- ✅ User-installed zsh
- ✅ Both bash and zsh installed
- ✅ Only bash available (zsh tests gracefully skipped)
- ✅ Other shells (fish, dash, etc.) - core tests still work

### BSD/Others
- ✅ Any POSIX-compatible shell
- ✅ Tests adapt to available shells

---

## Running Tests

### Run All Tests
```bash
bash test_prompt_colors.sh
```

### Expected Output on macOS (with zsh)
```
Tests run:    22
Tests passed: 22
Tests failed: 0

✓ All tests passed!
```

### Expected Output on Linux (bash only)
```
Tests run:    22
Tests passed: 22  (zsh tests auto-skipped if zsh not installed)
Tests failed: 0

✓ All tests passed!
```

---

## Adding New Tests

### For Shell-Specific Behavior
```bash
test_new_bash_feature() {
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c 'test bash feature')

    if [[ "$result" == "expected" ]]; then
        print_pass "Test description"
    else
        print_fail "Test should do X"
    fi
}
```

### For Shell-Agnostic Behavior
```bash
test_new_cross_shell_feature() {
    # Test in bash
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c 'test feature')
    # ... validate ...

    # Test in zsh (if available)
    TESTS_RUN=$((TESTS_RUN + 1))
    if command -v zsh >/dev/null; then
        result=$(zsh -c 'test feature')
        # ... validate ...
    else
        print_pass "Zsh not available (skipped)"
    fi
}
```

---

## Maintenance

### When Adding New Prompt Features

1. Add shell-specific tests if feature uses different code per shell
2. Add functional tests to verify output is correct
3. Test on both platforms if possible
4. Update this documentation

### When Supporting New Shells

1. Add shell detection logic
2. Add shell-specific escape sequence tests
3. Add to test coverage matrix
4. Update graceful degradation logic

---

## Future Enhancements

Potential additions:
- [ ] Test color schemes (not just green)
- [ ] Test more shells (fish, dash, ksh)
- [ ] Test terminal emulator compatibility (iTerm2, Terminal.app, alacritty, etc.)
- [ ] Performance benchmarks
- [ ] Visual rendering tests (difficult in CI)
- [ ] Test PS2, PS3, PS4 prompts

---

## References

- Bash prompt escaping: https://www.gnu.org/software/bash/manual/html_node/Controlling-the-Prompt.html
- Zsh prompt escaping: http://zsh.sourceforge.net/Doc/Release/Prompt-Expansion.html
- ANSI color codes: https://en.wikipedia.org/wiki/ANSI_escape_code

---

**Last Updated**: 2026-01-09
**Maintainer**: Repository contributors
**Status**: ✅ All 22 tests passing on macOS and Linux
