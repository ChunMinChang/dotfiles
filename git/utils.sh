# General
# ------------------------------------------------
alias ga='git add'
alias gb='git branch -v'
alias gc='git commit'
alias gcp='git cherry-pick'
alias gcl='git clean'
alias gcp='git cherry-pick'
alias gd='git diff'
alias go='git checkout'
alias gpl='git pull'
alias gps='git push'
alias grb='git rebase'
alias grt='git remote -v'
alias gs='git status'
alias gum='git add -u && git commit -m'
alias gwt='git worktree'

# Typo
# ------------------------------------------------
alias get='git'
alias gkt='git'
alias got='git'
alias gut='git'

# Run commands on all files in the last commit
# ------------------------------------------------
function GitLastCommit() {
  if [ -z "$1" ]; then
    PrintError "Usage: GitLastCommit <command>"
    return 1
  fi

  local cmd="$1"
  # Load edited files into tabs if cmd is vim
  if [ "$cmd" == "vim" ]; then
    cmd="vim -p" # open files in tabs
  fi

  # Get list of files from last commit
  local files
  files=$(git diff-tree --no-commit-id --name-only --diff-filter=d -r HEAD 2>&1)

  if [ $? -ne 0 ]; then
    PrintError "Failed to get files from last commit. Are you in a git repository?"
    return 1
  fi

  if [ -z "$files" ]; then
    PrintWarning "No files in last commit"
    return 0
  fi

  # Pass files to command
  echo "$files" | xargs "$cmd"
}

# Run commands on all uncommit files
# ------------------------------------------------
function GitUncommit() {
  if [ -z "$1" ]; then
    PrintError "Usage: GitUncommit <command>"
    return 1
  fi

  local cmd="$1"
  # Load edited files into tabs if cmd is vim
  if [ "$cmd" == "vim" ]; then
    cmd="vim -p" # open files in tabs
  fi

  # Check if there are any uncommitted files
  local file_count
  file_count=$(git ls-files --modified --deleted --others | wc -l)

  if [ "$file_count" -eq 0 ]; then
    PrintWarning "No uncommitted files"
    return 0
  fi

  # Run command on uncommitted files (using null-terminated list for safety)
  git ls-files --modified --deleted --others -z | xargs -0 "$cmd"
}

# Add some files except some certain files
# ------------------------------------------------
function GitAddExcept {
  if [ $# -eq 0 ]; then
    PrintError "Usage: GitAddExcept [-A|-u] <file1> [file2] ..."
    PrintError "  -A, --all     Add all files except specified ones"
    PrintError "  -u, --update  Add updated files except specified ones"
    return 1
  fi

  local option=""
  local files=()
  while [[ $# -gt 0 ]]
  do
    arg="$1"

    case $arg in
      -A|--all)
        option="$arg"
        shift
        ;;
      -u|--update)
        option="$arg"
        shift
        ;;
      *)  # Files to exclude
        files+=("$1")
        shift
        ;;
    esac
  done

  # Validate that we have files to exclude
  if [ ${#files[@]} -eq 0 ]; then
    PrintError "No files specified to exclude"
    return 1
  fi

  # If no option provided, default to -A (add all)
  if [ -z "$option" ]; then
    option="-A"
  fi

  # Add files with the specified option
  git add "$option" || return 1

  # Reset (unstage) the excluded files
  git reset "${files[@]}"
}

# Create a branch for pull request
# ------------------------------------------------
function CreateGitBranchForPullRequest {
  if [ $# -ne 2 ]; then
    PrintError "Usage: CreateGitBranchForPullRequest <remote> <pr-number>"
    PrintError "Example: CreateGitBranchForPullRequest upstream 123"
    return 1
  fi

  local remote="$1"
  local number="$2"

  # Validate that number is actually a number
  if ! [[ "$number" =~ ^[0-9]+$ ]]; then
    PrintError "PR number must be a positive integer: '$number'"
    return 1
  fi

  # Validate that remote exists
  if ! git remote | grep -q "^${remote}$"; then
    PrintError "Remote '$remote' does not exist"
    PrintError "Available remotes:"
    git remote -v
    return 1
  fi

  local branch_name="pr-$number"

  # Check if branch already exists
  if git show-ref --verify --quiet "refs/heads/$branch_name"; then
    PrintWarning "Branch '$branch_name' already exists"
    read -p "Overwrite existing branch? [y/N]: " -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
      echo "Cancelled"
      return 0
    fi
    # Delete existing branch
    git branch -D "$branch_name"
  fi

  # Fetch the pull request
  echo "Fetching pull request #$number from $remote..."
  if git fetch "$remote" "pull/$number/head:$branch_name"; then
    echo "✓ Successfully created branch: $branch_name"
    printf "\nCurrent git branches:\n"
    git branch -v
  else
    PrintError "Failed to fetch pull request #$number from $remote"
    return 1
  fi
}


# Show git branch in prompt.
# ------------------------------------------------
function ParseGitBranch {
  git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}

# Rename a branch locally and on remote
# ------------------------------------------------
function GitRenameBranch {
  if [ $# -lt 2 ] || [ $# -gt 3 ]; then
    PrintError "Usage: GitRenameBranch <old-name> <new-name> [remote]"
    PrintError "  remote defaults to 'origin'"
    return 1
  fi

  local old_name="$1"
  local new_name="$2"
  local remote="${3:-origin}"

  # Validate remote exists
  if ! git remote | grep -q "^${remote}$"; then
    PrintError "Remote '$remote' does not exist"
    PrintError "Available remotes:"
    git remote -v
    return 1
  fi

  # Check if old branch exists locally
  if ! git show-ref --verify --quiet "refs/heads/$old_name"; then
    PrintError "Local branch '$old_name' does not exist"
    return 1
  fi

  # Check if new branch already exists locally
  if git show-ref --verify --quiet "refs/heads/$new_name"; then
    PrintError "Local branch '$new_name' already exists"
    return 1
  fi

  # Check if old branch exists on remote
  local remote_exists=false
  if git ls-remote --exit-code --heads "$remote" "$old_name" &>/dev/null; then
    remote_exists=true
  fi

  # Rename local branch
  echo "Renaming local branch '$old_name' to '$new_name'..."
  if ! git branch -m "$old_name" "$new_name"; then
    PrintError "Failed to rename local branch"
    return 1
  fi

  if [ "$remote_exists" = true ]; then
    # Push new branch to remote
    echo "Pushing '$new_name' to $remote..."
    if ! git push "$remote" -u "$new_name"; then
      PrintError "Failed to push new branch to remote"
      PrintWarning "Local branch was renamed. You may need to manually fix remote."
      return 1
    fi

    # Delete old branch from remote
    echo "Deleting '$old_name' from $remote..."
    if ! git push "$remote" --delete "$old_name"; then
      PrintError "Failed to delete old branch from remote"
      PrintWarning "New branch was pushed. You may need to manually delete '$old_name' from $remote."
      return 1
    fi

    echo "Successfully renamed branch '$old_name' to '$new_name' (local and remote)"
  else
    echo "Successfully renamed local branch '$old_name' to '$new_name'"
    PrintWarning "Branch did not exist on remote '$remote', only renamed locally"
  fi
}

# Delete a branch locally and on remote
# ------------------------------------------------
function GitDeleteBranch {
  local force=false
  local branch=""
  local remote="origin"

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--force)
        force=true
        shift
        ;;
      *)
        if [ -z "$branch" ]; then
          branch="$1"
        else
          remote="$1"
        fi
        shift
        ;;
    esac
  done

  if [ -z "$branch" ]; then
    PrintError "Usage: GitDeleteBranch [-f|--force] <branch> [remote]"
    PrintError "  remote defaults to 'origin'"
    return 1
  fi

  # Validate remote exists
  if ! git remote | grep -q "^${remote}$"; then
    PrintError "Remote '$remote' does not exist"
    PrintError "Available remotes:"
    git remote -v
    return 1
  fi

  # Check if branch exists locally
  if ! git show-ref --verify --quiet "refs/heads/$branch"; then
    PrintError "Local branch '$branch' does not exist"
    return 1
  fi

  # Delete local branch
  local flag="-d"
  if [ "$force" = true ]; then
    flag="-D"
  fi

  echo "Deleting local branch '$branch'..."
  if ! git branch $flag "$branch"; then
    PrintError "Failed to delete local branch"
    PrintError "Use -f to force delete unmerged branch"
    return 1
  fi

  # Check if remote branch exists and delete it
  if git ls-remote --exit-code --heads "$remote" "$branch" &>/dev/null; then
    echo "Deleting '$branch' from $remote..."
    if ! git push "$remote" --delete "$branch"; then
      PrintError "Failed to delete remote branch"
      return 1
    fi
    echo "Successfully deleted branch '$branch' (local and remote)"
  else
    echo "Successfully deleted local branch '$branch'"
    PrintWarning "Branch did not exist on remote '$remote'"
  fi
}

function BranchInPrompt {
  # Detect shell and use appropriate escape sequences
  # bash uses \[ \] for non-printing characters
  # zsh uses %{ %} for non-printing characters
  if [ -n "$ZSH_VERSION" ]; then
    # zsh
    local GREEN="%{$(tput setaf 2)%}"
    local DEFAULT="%{$(tput sgr0)%}"
    PS1="$GREEN\$(ParseGitBranch)$DEFAULT$PS1"
  elif [ -n "$BASH_VERSION" ]; then
    # bash
    local GREEN="\[\033[0;32m\]"
    local DEFAULT="\[\033[0m\]"
    PS1="$GREEN\$(ParseGitBranch)$DEFAULT$PS1"
  fi
}
