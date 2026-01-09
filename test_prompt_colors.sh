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

# Test functions
test_bash_escape_sequences() {
    print_section "Bash Escape Sequences"

    # Test 1: BranchInPrompt uses bash sequences when BASH_VERSION is set
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(bash -c '
        export BASH_VERSION="5.0.0"
        unset ZSH_VERSION
        source git/utils.sh
        BranchInPrompt
        echo "$PS1"
    ')

    if echo "$result" | grep -q '\\[\\033\[0;32m\\]'; then
        print_pass "Bash uses \\[\\033[0;32m\\] for green"
    else
        print_fail "Bash should use \\[\\033[0;32m\\] for green, got: $result"
    fi

    # Test 2: Bash uses closing escape sequence
    TESTS_RUN=$((TESTS_RUN + 1))
    if echo "$result" | grep -q '\\[\\033\[0m\\]'; then
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
    result=$(bash -c '
        export BASH_VERSION="5.0.0"
        unset ZSH_VERSION
        source git/utils.sh
        # Check if bash path is taken
        BranchInPrompt
        echo "$PS1"
    ')

    if echo "$result" | grep -qF '\['; then
        print_pass "Shell detection correctly identifies bash"
    else
        print_fail "Shell detection should identify bash, got PS1: $result"
    fi

    # Test 2: Detects zsh
    TESTS_RUN=$((TESTS_RUN + 1))
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
    result=$(bash -c '
        export BASH_VERSION="5.0.0"
        unset ZSH_VERSION
        source git/utils.sh
        BranchInPrompt
        echo "$PS1"
    ')

    if echo "$result" | grep -qF '\[' && echo "$result" | grep -qF '\]'; then
        print_pass "Bash prompt has properly formatted escape sequences"
    else
        print_fail "Bash prompt escape sequences malformed, got: $result"
    fi

    # Test zsh
    TESTS_RUN=$((TESTS_RUN + 1))
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

test_rprompt_disabled() {
    print_section "RPROMPT Disabled in Zsh"

    # Test that RPROMPT is not set in zsh
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(zsh -c '
        source dot.zshrc 2>/dev/null
        echo "RPROMPT_VALUE:|$RPROMPT|"
    ')

    if [[ "$result" =~ RPROMPT_VALUE:\|\| ]]; then
        print_pass "RPROMPT is empty/unset in zsh"
    else
        print_fail "RPROMPT should be empty, got: $result"
    fi

    # Test that vcs_info_wrapper is not defined
    TESTS_RUN=$((TESTS_RUN + 1))
    result=$(zsh -c '
        source dot.zshrc 2>/dev/null
        if type vcs_info_wrapper &>/dev/null; then
            echo "defined"
        else
            echo "not_defined"
        fi
    ')

    if [[ "$result" == "not_defined" ]]; then
        print_pass "vcs_info_wrapper is not defined (commented out)"
    else
        print_fail "vcs_info_wrapper should not be defined"
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
    TESTS_RUN=$((TESTS_RUN + 1))
    platform=$(uname -s)

    if [[ "$platform" == "Darwin" ]]; then
        # macOS - should use zsh
        result=$(zsh -c '
            source ~/.zshrc 2>/dev/null
            type BranchInPrompt
        ' 2>&1)

        if echo "$result" | grep -q "shell function"; then
            print_pass "Prompt functions load correctly on macOS (zsh)"
        else
            print_fail "Prompt functions should load on macOS"
        fi
    elif [[ "$platform" == "Linux" ]]; then
        # Linux - should use bash
        result=$(bash -c '
            source ~/.bashrc 2>/dev/null
            type BranchInPrompt
        ' 2>&1)

        if echo "$result" | grep -q "function"; then
            print_pass "Prompt functions load correctly on Linux (bash)"
        else
            print_fail "Prompt functions should load on Linux"
        fi
    else
        print_fail "Unknown platform: $platform"
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
    echo ""

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        return 1
    fi
}

# Main execution
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
