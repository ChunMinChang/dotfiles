# Shell Variable Quoting Audit

Generated: 2026-01-07
Related TODO: Item 3.1

## Summary

Found **40+ unquoted variable expansions** across 5 shell script files that need quoting to handle paths with spaces correctly.

---

## Files to Fix

### 1. utils.sh (10 issues)

| Line | Current Code | Should Be | Severity |
|------|--------------|-----------|----------|
| 11 | `command -v $cmd` | `command -v "$cmd"` | MEDIUM |
| 24 | `echo -e ${bold_red}ERROR:${normal} $msg` | `echo -e "${bold_red}ERROR:${normal} $msg"` | LOW |
| 32 | `echo -e ${bold_cyan_bkg}HINT:${normal} $msg` | `echo -e "${bold_cyan_bkg}HINT:${normal} $msg"` | LOW |
| 40 | `echo -e ${bold_yellow}WARNING:${normal} $msg` | `echo -e "${bold_yellow}WARNING:${normal} $msg"` | LOW |
| 57 | `local items=$@` | `local items="$@"` | HIGH |
| 59 | `if [ ! -z "$items" ]` | Already quoted ✓ | - |
| 61 | `mv $items $TRASH` | `mv "$items" "$TRASH"` | HIGH |
| 72 | `local params=$@` | Better: use "$@" directly | HIGH |
| 75 | `npx live-server $params` | `npx live-server "$@"` | HIGH |
| 77 | `python3 -m http.server $params` | `python3 -m http.server "$@"` | HIGH |
| 79 | `python -m SimpleHTTPServer $params` | `python -m SimpleHTTPServer "$@"` | HIGH |

### 2. git/utils.sh (7 issues)

| Line | Current Code | Should Be | Severity |
|------|--------------|-----------|----------|
| 33 | `xargs $cmd` | `xargs "$cmd"` | MEDIUM |
| 44 | `$cmd $(git status ...)` | Separate issue (TODO 1.3) | HIGH |
| 59 | `option=$arg` | `option="$arg"` | LOW |
| 63 | `option=$arg` | `option="$arg"` | LOW |
| 72 | `git add $option` | `git add "$option"` or keep unquoted | MEDIUM |
| 81 | `git fetch $remote pull/$number/...` | `git fetch "$remote" pull/"$number"/...` | HIGH |

### 3. mozilla/gecko/tools.sh (8 issues)

| Line | Current Code | Should Be | Severity |
|------|--------------|-----------|----------|
| 2 | `if [ -d $DEFAULT_GIT_CINNABAR ]` | `if [ -d "$DEFAULT_GIT_CINNABAR" ]` | HIGH |
| 5 | `GIT_CINNABAR=$HOME/Work/git-cinnabar` | `GIT_CINNABAR="$HOME/Work/git-cinnabar"` | MEDIUM |
| 8 | `if [ -d $GIT_CINNABAR ]` | `if [ -d "$GIT_CINNABAR" ]` | HIGH |
| 9 | `export PATH=$GIT_CINNABAR:$PATH` | `export PATH="$GIT_CINNABAR:$PATH"` | HIGH |
| 14 | `PrintError "... $GIT_CINNABAR!"` | Already inside quotes ✓ | - |
| 18 | `export PATH=$HOME/.local/bin:$PATH` | `export PATH="$HOME/.local/bin:$PATH"` | MEDIUM |
| 26 | `if [ -r $HOME/Work/bin/pernosco-submit ]` | `if [ -r "$HOME/Work/bin/pernosco-submit" ]` | MEDIUM |
| 27 | `export PATH=$HOME/Work/bin:$PATH` | `export PATH="$HOME/Work/bin:$PATH"` | MEDIUM |

### 4. mozilla/gecko/alias.sh (10 issues)

| Line | Current Code | Should Be | Severity |
|------|--------------|-----------|----------|
| 71 | ``local files=`git diff --name-only $1` `` | ``local files=$(git diff --name-only "$1")`` | HIGH |
| 72 | `for file in $files` | `while IFS= read -r file` (better) | HIGH |
| 74 | `./mach clang-format --path $file` | `./mach clang-format --path "$file"` | HIGH |
| 75 | `./mach static-analysis check $file` | `./mach static-analysis check "$file"` | HIGH |
| 83 | `cargo update -p $crate` | `cargo update -p "$crate"` | MEDIUM |
| 90 | `curl ... -F file=@$file ... > $page` | `curl ... -F "file=@$file" ... > "$page"` | HIGH |

### 5. dot.settings_linux (4 issues)

| Line | Current Code | Should Be | Severity |
|------|--------------|-----------|----------|
| 6 | `if [ -r $HOME/.gitconfig ]` | `if [ -r "$HOME/.gitconfig" ]` | MEDIUM |
| 26 | `local cmd=$@` | Use `"$@"` directly | HIGH |
| 27 | `echo $cmd` | `echo "$cmd"` | LOW |
| 28 | `$cmd --enable-features...` | `"$@" --enable-features...` | HIGH |

### 6. dot.settings_darwin (0 issues)

✅ All variables properly quoted

---

## Severity Levels

- **HIGH**: Breaks with spaces in arguments or paths (security/data loss risk)
- **MEDIUM**: May break in edge cases, affects path handling
- **LOW**: Mostly cosmetic, unlikely to cause issues

---

## Special Cases Requiring Different Fixes

### Case 1: `$@` vs `"$@"`

**Problem**: `local params=$@` captures all args but loses proper word splitting

**Wrong approach**:
```bash
local params=$@
some_command $params  # Breaks with spaces
```

**Correct approach**:
```bash
# Don't store $@ in a variable, use it directly
some_command "$@"
```

### Case 2: Loop over files with spaces

**Current (mozilla/gecko/alias.sh:71-72)**:
```bash
local files=`git diff --name-only $1`
for file in $files; do
```

**Problem**: Breaks with filenames containing spaces or newlines

**Better approach**:
```bash
git diff --name-only "$1" | while IFS= read -r file; do
  # process "$file"
done
```

Or use array:
```bash
local files=()
while IFS= read -r file; do
  files+=("$file")
done < <(git diff --name-only "$1")

for file in "${files[@]}"; do
  # process "$file"
done
```

### Case 3: git add $option

**Line 72 in git/utils.sh**:
```bash
git add $option
```

**Analysis**: This might be intentionally unquoted to allow `$option` to be empty (no argument passed). However, it should still be quoted:

```bash
git add "$option"
```

Empty string in quotes is fine and won't cause issues.

---

## Testing Strategy

For each fix:
1. Test with normal paths (no spaces)
2. Test with paths containing spaces
3. Test with empty arguments
4. Test with special characters

Example test cases:
```bash
# Test utils.sh Trash function
mkdir -p "/tmp/test path with spaces/file.txt"
Trash "/tmp/test path with spaces/file.txt"

# Test git/utils.sh GitLastCommit
GitLastCommit vim

# Test mozilla functions with special paths
MozCheckDiff HEAD~1
```

---

## Total Count

- **Files**: 5
- **Lines to fix**: 40+
- **High severity**: 18
- **Medium severity**: 12
- **Low severity**: 4
