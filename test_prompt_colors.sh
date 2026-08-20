#!/usr/bin/env bash
# Test suite for prompt colors and cross-shell compatibility
# Tests BranchInPrompt and ParseGitBranch functions across bash and zsh

# Don't use set -e as individual tests may fail
# set -e

# Color definitions for test output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# zsh is an optional dependency: it ships with macOS, is usually a package
# away on Linux, and is absent from Windows/Git Bash. A missing optional
# interpreter is not a test failure -- reporting 11 red X's there hid real
# regressions in the noise. Detect it once and skip those assertions.
HAVE_ZSH=0
command -v zsh >/dev/null 2>&1 && HAVE_ZSH=1

# Print functions
print_test_header() {
    echo -e "${BLUE}====================================="
    echo "Prompt Colors Test Suite"
    echo -e "=====================================${NC}"
    echo ""
}

print_section() {
    echo -e "${YELLOW}Test Suite: $1${NC}"
}

print_pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "  ${RED}✗${NC} $1"
    ((TESTS_FAILED++))
}

print_skip() {
    echo -e "  ${YELLOW}⊘${NC} $1 (skipped: zsh not installed)"
    ((TESTS_SKIPPED++))
}

# BranchInPrompt's bash path deliberately defers the work to PROMPT_COMMAND
# instead of embedding $(ParseGitBranch) in PS1 (see git/utils.sh for why), so
# the branch only lands in PS1 once that hook runs. Non-interactive bash never
# fires PROMPT_COMMAND and leaves PS1 unset, so seed PS1 and run the hook by
# hand to observe what an interactive prompt would actually render.
render_bash_prompt() {
    bash -c '
        export BASH_VERSION="5.0.0"
        unset ZSH_VERSION
        source git/utils.sh
        PS1="\u@\h \w\$ "
        BranchInPrompt
        eval "$PROMPT_COMMAND"
        echo "$PS1"
    '
}

# Test functions
test_bash_escape_sequences() {
    print_section "Bash Escape Sequences"

    # Test 1: BranchInPrompt uses bash sequences when BASH_VERSION is set
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(render_bash_prompt)

    # Match with -F: as a regex, '\[\033[0;32m\]' would parse the trailing
    # [0;32m\] as a character class and match almost any backslash, which
    # silently passed even when the escapes were malformed.
    if echo "$result" | grep -qF '\[\033[0;32m\]'; then
        print_pass "Bash uses \\[\\033[0;32m\\] for green"
    else
        print_fail "Bash should use \\[\\033[0;32m\\] for green, got: $result"
    fi

    # Test 2: Bash uses closing escape sequence
    TESTS_RUN=$((TESTS_RUN + 1))
    if echo "$result" | grep -qF '\[\033[0m\]'; then
        print_pass "Bash uses \\[\\033[0m\\] for reset"
    else
        print_fail "Bash should use \\[\\033[0m\\] for reset, got: $result"
    fi

    # Test 3: Bash escape sequences are properly wrapped
    TESTS_RUN=$((TESTS_RUN + 1))
    if echo "$result" | grep -qF '\[' && echo "$result" | grep -qF '\]'; then
        print_pass "Bash escape sequences properly wrapped with \\[ \\]"
    else
        print_fail "Bash escape sequences should be wrapped with \\[ \\], got: $result"
    fi
}

test_zsh_escape_sequences() {
    print_section "Zsh Escape Sequences"

    if [ "$HAVE_ZSH" -eq 0 ]; then
        TESTS_RUN=$((TESTS_RUN + 3))
        print_skip "Zsh uses %{ for opening escape"
        print_skip "Zsh uses %} for closing escape"
        print_skip "Zsh prompt is set (uses tput for colors)"
        return
    fi

    # Test 1: BranchInPrompt uses zsh sequences when ZSH_VERSION is set
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(zsh -c '
        export ZSH_VERSION="5.8"
        unset BASH_VERSION
        source git/utils.sh
        BranchInPrompt
        echo "$PS1"
    ' 2>/dev/null)

    if echo "$result" | grep -q '%{'; then
        print_pass "Zsh uses %{ for opening escape"
    else
        print_fail "Zsh should use %{ for opening escape, got: $result"
    fi

    # Test 2: Zsh uses closing escape sequence
    TESTS_RUN=$((TESTS_RUN + 1))
    if echo "$result" | grep -q '%}'; then
        print_pass "Zsh uses %} for closing escape"
    else
        print_fail "Zsh should use %} for closing escape, got: $result"
    fi

    # Test 3: Zsh uses tput for colors
    TESTS_RUN=$((TESTS_RUN + 1))
    # Check if the function at least tries to use tput (the output will contain escape codes)
    if [[ -n "$result" ]]; then
        print_pass "Zsh prompt is set (uses tput for colors)"
    else
        print_fail "Zsh prompt should be set"
    fi
}

test_parse_git_branch() {
    print_section "ParseGitBranch Function"

    # Test in bash
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c '
        source git/utils.sh
        cd . # Make sure we are in git repo
        ParseGitBranch
    ')

    if [[ "$result" =~ ^\([a-zA-Z0-9_-]+\)$ ]]; then
        print_pass "ParseGitBranch outputs correct format in bash: $result"
    else
        print_fail "ParseGitBranch should output (branch-name) format in bash, got: $result"
    fi

    # Test in zsh
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$HAVE_ZSH" -eq 0 ]; then
        print_skip "ParseGitBranch outputs correct format in zsh"
        return
    fi
    result=$(zsh -c '
        source git/utils.sh
        cd . # Make sure we are in git repo
        ParseGitBranch
    ' 2>/dev/null)

    if [[ "$result" =~ ^\([a-zA-Z0-9_-]+\)$ ]]; then
        print_pass "ParseGitBranch outputs correct format in zsh: $result"
    else
        print_fail "ParseGitBranch should output (branch-name) format in zsh, got: $result"
    fi
}

test_shell_detection() {
    print_section "Shell Detection Logic"

    # Test 1: Detects bash
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(render_bash_prompt)

    if echo "$result" | grep -qF '\['; then
        print_pass "Shell detection correctly identifies bash"
    else
        print_fail "Shell detection should identify bash, got PS1: $result"
    fi

    # Test 2: Detects zsh
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$HAVE_ZSH" -eq 0 ]; then
        print_skip "Shell detection correctly identifies zsh"
        return
    fi
    result=$(zsh -c '
        export ZSH_VERSION="5.8"
        unset BASH_VERSION
        source git/utils.sh
        # Check if zsh path is taken
        BranchInPrompt
        if [[ "$PS1" =~ %\\{ ]]; then
            echo "zsh_detected"
        fi
    ' 2>/dev/null)

    if [[ "$result" == "zsh_detected" ]]; then
        print_pass "Shell detection correctly identifies zsh"
    else
        print_fail "Shell detection should identify zsh"
    fi
}

test_no_literal_escapes() {
    print_section "No Literal Escape Sequences in Output"

    # This test verifies that escape sequences don't appear literally
    # when the prompt is actually used (though we can't fully test rendering)

    # Test bash
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(render_bash_prompt)

    if echo "$result" | grep -qF '\[' && echo "$result" | grep -qF '\]'; then
        print_pass "Bash prompt has properly formatted escape sequences"
    else
        print_fail "Bash prompt escape sequences malformed, got: $result"
    fi

    # Test zsh
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$HAVE_ZSH" -eq 0 ]; then
        print_skip "Zsh prompt has properly formatted escape sequences"
        return
    fi
    result=$(zsh -c '
        export ZSH_VERSION="5.8"
        unset BASH_VERSION
        source git/utils.sh
        BranchInPrompt
        # Check that PS1 contains the escape sequences in proper format
        if [[ "$PS1" =~ %\\{ ]]; then
            echo "zsh_ok"
        fi
    ' 2>/dev/null)

    if [[ "$result" == "zsh_ok" ]]; then
        print_pass "Zsh prompt has properly formatted escape sequences"
    else
        print_fail "Zsh prompt escape sequences malformed"
    fi
}

test_prompt_subst_enabled() {
    print_section "PROMPT_SUBST Enabled in Zsh"

    # Test that PROMPT_SUBST is enabled for dynamic prompt substitution
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$HAVE_ZSH" -eq 0 ]; then
        print_skip "PROMPT_SUBST is enabled (required for \$(ParseGitBranch))"
        return
    fi
    result=$(zsh -c '
        source dot.zshrc 2>/dev/null
        if [[ -o prompt_subst ]]; then
            echo "enabled"
        else
            echo "disabled"
        fi
    ')

    if [[ "$result" == "enabled" ]]; then
        print_pass "PROMPT_SUBST is enabled (required for \$(ParseGitBranch))"
    else
        print_fail "PROMPT_SUBST should be enabled for dynamic prompts"
    fi
}

test_rprompt_disabled() {
    print_section "RPROMPT Disabled in Zsh"

    # Test that RPROMPT is not set in zsh
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$HAVE_ZSH" -eq 0 ]; then
        print_skip "RPROMPT is empty/unset in zsh"
        return
    fi
    result=$(zsh -c '
        source dot.zshrc 2>/dev/null
        echo "RPROMPT_VALUE:|$RPROMPT|"
    ')

    if [[ "$result" =~ RPROMPT_VALUE:\|\| ]]; then
        print_pass "RPROMPT is empty/unset in zsh"
    else
        print_fail "RPROMPT should be empty, got: $result"
    fi
}

test_prompt_functions_exist() {
    print_section "Prompt Functions Exist"

    # Test in bash
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c '
        source git/utils.sh
        if type BranchInPrompt &>/dev/null; then
            echo "exists"
        fi
    ')

    if [[ "$result" == "exists" ]]; then
        print_pass "BranchInPrompt exists in bash"
    else
        print_fail "BranchInPrompt should exist in bash"
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c '
        source git/utils.sh
        if type ParseGitBranch &>/dev/null; then
            echo "exists"
        fi
    ')

    if [[ "$result" == "exists" ]]; then
        print_pass "ParseGitBranch exists in bash"
    else
        print_fail "ParseGitBranch should exist in bash"
    fi

    # Test in zsh
    if [ "$HAVE_ZSH" -eq 0 ]; then
        TESTS_RUN=$((TESTS_RUN + 2))
        print_skip "BranchInPrompt exists in zsh"
        print_skip "ParseGitBranch exists in zsh"
        return
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(zsh -c '
        source git/utils.sh 2>/dev/null
        if type BranchInPrompt &>/dev/null; then
            echo "exists"
        fi
    ')

    if [[ "$result" == "exists" ]]; then
        print_pass "BranchInPrompt exists in zsh"
    else
        print_fail "BranchInPrompt should exist in zsh"
    fi

    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(zsh -c '
        source git/utils.sh 2>/dev/null
        if type ParseGitBranch &>/dev/null; then
            echo "exists"
        fi
    ')

    if [[ "$result" == "exists" ]]; then
        print_pass "ParseGitBranch exists in zsh"
    else
        print_fail "ParseGitBranch should exist in zsh"
    fi
}

test_cross_platform_compatibility() {
    print_section "Cross-Platform Compatibility"

    # Test that the functions work on current platform
    # Don't assume shell based on platform - test both shells on any platform
    platform=$(uname -s)

    # Test 1: Functions work in bash (regardless of platform)
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c '
        source git/utils.sh 2>/dev/null
        type BranchInPrompt
    ' 2>&1)

    if echo "$result" | grep -q "function"; then
        print_pass "Prompt functions load correctly in bash on $platform"
    else
        print_fail "Prompt functions should load in bash on $platform"
    fi

    # Test 2: Functions work in zsh (regardless of platform)
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$HAVE_ZSH" -eq 0 ]; then
        # Was counted as a pass, which inflated the pass count and hid the
        # fact that nothing was verified. Report it as the skip it is.
        print_skip "Prompt functions load correctly in zsh on $platform"
        return
    fi

    result=$(zsh -c '
        source git/utils.sh 2>/dev/null
        type BranchInPrompt
    ' 2>&1)

    if echo "$result" | grep -q "function"; then
        print_pass "Prompt functions load correctly in zsh on $platform"
    else
        print_fail "Prompt functions should load in zsh on $platform"
    fi
}

test_no_errors_on_load() {
    print_section "No Errors on Load"

    # Test bash loading
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c 'source git/utils.sh 2>&1')

    if [[ -z "$result" ]]; then
        print_pass "git/utils.sh loads without errors in bash"
    else
        print_fail "git/utils.sh should load without errors in bash, got: $result"
    fi

    # Test zsh loading
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$HAVE_ZSH" -eq 0 ]; then
        print_skip "git/utils.sh loads without errors in zsh"
        return
    fi
    result=$(zsh -c 'source git/utils.sh 2>&1')

    if [[ -z "$result" ]]; then
        print_pass "git/utils.sh loads without errors in zsh"
    else
        print_fail "git/utils.sh should load without errors in zsh, got: $result"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo -e "${BLUE}====================================="
    echo "Test Summary"
    echo -e "=====================================${NC}"
    echo ""
    echo "Tests run:    $TESTS_RUN"
    echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
    if [ "$TESTS_SKIPPED" -gt 0 ]; then
        echo -e "Tests skipped: ${YELLOW}$TESTS_SKIPPED${NC} (zsh not installed)"
    fi
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        if [ "$TESTS_SKIPPED" -gt 0 ]; then
            echo -e "${GREEN}✓ All tests passed${NC} (${YELLOW}$TESTS_SKIPPED skipped${NC})"
            echo -e "${YELLOW}  Install zsh to cover the zsh prompt paths.${NC}"
        else
            echo -e "${GREEN}✓ All tests passed!${NC}"
        fi
        return 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        return 1
    fi
}

# Main execution
test_bash_ps1_stays_editable() {
    print_section "Bash PS1 Remains Editable"

    # Regression: BranchInPrompt used to snapshot PS1 at setup time and have
    # PROMPT_COMMAND rebuild PS1 from that snapshot, so an edit made later --
    # a virtualenv prefix, say -- was dropped on the next prompt. Only the
    # bash path is covered here: zsh keeps the literal $(ParseGitBranch) in
    # PS1 and was never affected.
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c '
        export BASH_VERSION="5.0.0"
        unset ZSH_VERSION
        source git/utils.sh
        PS1="\u@\h \w\$ "
        BranchInPrompt
        PS1="(myvenv) $PS1"
        eval "$PROMPT_COMMAND"
        printf "%s" "$PS1"
    ')

    if echo "$result" | grep -qF '(myvenv)'; then
        print_pass "Bash prompt keeps a PS1 edit made after BranchInPrompt"
    else
        print_fail "Bash prompt dropped a later PS1 edit, got: $result"
    fi

    # PS1 holds a reference to the branch rather than the branch itself, so
    # expand it the way bash does at display time to see the real prompt.
    TESTS_RUN=$((TESTS_RUN + 1))
    expected=$(bash -c 'source git/utils.sh; ParseGitBranch')
    result=$(bash -c '
        export BASH_VERSION="5.0.0"
        unset ZSH_VERSION
        source git/utils.sh
        PS1="\u@\h \w\$ "
        BranchInPrompt
        eval "$PROMPT_COMMAND"
        eval "printf \"%s\" \"$PS1\""
    ')

    if [ -n "$expected" ] && echo "$result" | grep -qF "$expected"; then
        print_pass "Bash prompt expands to the current branch $expected"
    else
        print_fail "Bash prompt did not expand to branch $expected, got: $result"
    fi

    # With no branch the separator has to disappear with it, or every prompt
    # outside a repository carries a stray leading space.
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c '
        export BASH_VERSION="5.0.0"
        unset ZSH_VERSION
        source git/utils.sh
        PS1="END"
        BranchInPrompt
        _dotfiles_branch=""
        eval "printf \"%s\" \"$PS1\""
    ')

    if echo "$result" | grep -qF 'END' && [ "${result% END}" = "$result" ]; then
        print_pass "Bash prompt drops the separator when there is no branch"
    else
        print_fail "Bash prompt left a separator with no branch, got: $result"
    fi
}

main() {
    print_test_header

    # Run all test suites
    test_bash_escape_sequences
    echo ""
    test_zsh_escape_sequences
    echo ""
    test_parse_git_branch
    echo ""
    test_shell_detection
    echo ""
    test_no_literal_escapes
    echo ""
    test_bash_ps1_stays_editable
    echo ""
    test_prompt_subst_enabled
    echo ""
    test_rprompt_disabled
    echo ""
    test_prompt_functions_exist
    echo ""
    test_cross_platform_compatibility
    echo ""
    test_no_errors_on_load

    # Print summary
    print_summary
}

# Run main
main
exit $?
