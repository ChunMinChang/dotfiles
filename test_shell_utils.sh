#!/bin/bash
# Test suite for shell utilities

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
declare -a FAILED_TESTS

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source utilities
source "$SCRIPT_DIR/utils.sh" || exit 1
source "$SCRIPT_DIR/git/utils.sh" || exit 1

test_pass() {
    echo -e "${GREEN}✓${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

test_fail() {
    echo -e "${RED}✗ $1${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    FAILED_TESTS+=("$1")
}

echo -e "${BLUE}====================================\n"
echo "Shell Utilities Test Suite\n"
echo -e "====================================${NC}\n"

# Test CommandExists
echo -e "${YELLOW}Test Suite 1: CommandExists${NC}"
TESTS_RUN=$((TESTS_RUN + 1))
echo -n "  CommandExists with bash: "
if CommandExists bash; then test_pass; else test_fail "bash not found"; fi

TESTS_RUN=$((TESTS_RUN + 1))
echo -n "  CommandExists with fake command: "
if CommandExists fake_cmd_12345; then test_fail "false positive"; else test_pass; fi

# Test Print functions exist
echo -e "\n${YELLOW}Test Suite 2: Print Functions${NC}"
for func in PrintError PrintHint PrintWarning PrintTitle PrintSubTitle; do
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "  $func exists: "
    if declare -f $func &>/dev/null; then test_pass; else test_fail "$func missing"; fi
done

# Test RecursivelyFind
echo -e "\n${YELLOW}Test Suite 3: RecursivelyFind${NC}"
TEST_DIR=$(mktemp -d)
mkdir -p "$TEST_DIR/sub"
touch "$TEST_DIR/test.txt" "$TEST_DIR/sub/test.txt" "$TEST_DIR/other.md"

TESTS_RUN=$((TESTS_RUN + 1))
echo -n "  RecursivelyFind *.txt: "
cd "$TEST_DIR"
count=$(RecursivelyFind "*.txt" 2>/dev/null | wc -l)
cd - >/dev/null
if [ "$count" -eq 2 ]; then test_pass; else test_fail "expected 2, got $count"; fi

rm -rf "$TEST_DIR"

# Test Git functions exist
echo -e "\n${YELLOW}Test Suite 4: Git Utilities${NC}"
for func in GitLastCommit GitUncommit GitAddExcept CreateGitBranchForPullRequest ParseGitBranch BranchInPrompt; do
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "  $func exists: "
    if declare -f $func &>/dev/null; then test_pass; else test_fail "$func missing"; fi
done

# Test ParseGitBranch in git repo
if git rev-parse --git-dir &>/dev/null; then
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "  ParseGitBranch returns branch: "
    branch=$(ParseGitBranch 2>/dev/null)
    if [ -n "$branch" ]; then test_pass; else test_fail "empty branch"; fi
fi

# Test Trash and HostHTTP exist
echo -e "\n${YELLOW}Test Suite 5: Other Utilities${NC}"
for func in Trash HostHTTP; do
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -n "  $func exists: "
    if declare -f $func &>/dev/null; then test_pass; else test_fail "$func missing"; fi
done

# Syntax checks
echo -e "\n${YELLOW}Test Suite 6: Syntax Validation${NC}"
TESTS_RUN=$((TESTS_RUN + 1))
echo -n "  utils.sh syntax: "
if bash -n "$SCRIPT_DIR/utils.sh" 2>/dev/null; then test_pass; else test_fail "syntax error"; fi

TESTS_RUN=$((TESTS_RUN + 1))
echo -n "  git/utils.sh syntax: "
if bash -n "$SCRIPT_DIR/git/utils.sh" 2>/dev/null; then test_pass; else test_fail "syntax error"; fi

# Summary
echo -e "\n${BLUE}====================================\nTest Summary\n====================================${NC}\n"
echo "Tests run:    $TESTS_RUN"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}\n"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Failed tests:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "  ${RED}- $test${NC}"
    done
    exit 1
fi
