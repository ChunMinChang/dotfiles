---
name: vendor-local
description: Vendor code from a local repository into Firefox's third_party/rust directory.
---

## Related Skills

If you want to update a Rust crate to the **latest upstream release** (not local changes), use `/update-media-lib` instead. This skill (`/vendor-local`) is for testing **local changes** from a repository on your machine before they're merged upstream.

## Workflow

When the user invokes this skill, follow these steps in order:

### Step 1: Get local repo path

First, ask the user how they want to specify their repository location:

Use `AskUserQuestion` with options:
- **Type path directly** - User will provide the full path
- **Navigate from current directory** - Interactive folder navigation starting from `$PWD`

#### If user chooses "Type path directly":
- The "Other" option in AskUserQuestion lets them type the path
- Validate the path exists, contains `.git`, and contains `Cargo.toml`

#### If user chooses "Navigate from current directory":
1. Start at the current working directory (`$PWD`)
2. Run `ls -d */` to list subdirectories, and check if current directory is a git repo with `test -d .git`
3. Use `AskUserQuestion` to present navigation options:
   - If current directory is a git repo with Cargo.toml: offer "**Select this directory**" as first option
   - List up to 3 subdirectories as options
   - Always include "**Go up (..)**" option to navigate to parent
   - "Other" option lets user type an absolute path directly

4. Repeat navigation until user either:
   - Selects a directory that contains `.git` and `Cargo.toml`
   - Types an absolute path directly

5. Validate the selected path:
   - Check it exists and contains `.git`
   - Check it contains `Cargo.toml` (for Rust crates)
   - If invalid, show error and restart

### Step 2: List branches and let user select

1. Run `git branch -a` in the user's local repo to get all branches (local and remote)
2. Parse the output to extract branch names
3. Use `AskUserQuestion` to present the branches as options, with:
   - The current branch marked as "(current)"
   - Recent/common branches like `main`, `master` at the top if they exist
   - Up to 4 most relevant branches as quick-select options
   - "Other" option for branches not in the quick-select list

### Step 2b: Ask if they want single or multiple commits

After the user selects a branch, ask how many commits to vendor:

Use `AskUserQuestion` with options:
- **Single commit (recommended)** - Vendor one commit (branch HEAD or specific)
- **Multiple commits** - Vendor several commits in sequence

#### If user chooses "Single commit":

Ask what to vendor:
- **Branch HEAD** - Vendor the latest commit on this branch
- **Specific commit** - Choose a specific commit from the branch history

If "Branch HEAD": Proceed to Step 3 using the branch name for checkout

If "Specific commit":
1. Run `git log <branch> --oneline -n 10` to show recent commits
2. Parse the output (format: `<hash> <commit message>`)
3. Use `AskUserQuestion` to present commits as options:
   - Show up to 4 most recent commits with format: `<short-hash>: <message>`
   - "Other" option lets user type a commit hash directly
4. Store the selected commit hash to use for checkout in Step 4

Then proceed to Step 3.

#### If user chooses "Multiple commits":

Go to Step 2c to specify which commits.

### Step 2c: Specify multiple commits (only if user chose "Multiple commits")

Ask the user how they want to specify the commits:

Use `AskUserQuestion` with options:
- **List commit hashes** - Provide comma-separated commit hashes (e.g., "abc123, def456, ghi789")
- **Commit range** - Specify a range (e.g., "abc123..def456" or "HEAD~3..HEAD")
- **Last N commits from branch** - Vendor the most recent N commits (e.g., "last 3 commits")

#### Parse the commits based on selection:

**If "List commit hashes":**
- User provides comma-separated list via "Other" option
- Split by commas and trim whitespace
- Store as array of commit hashes

**If "Commit range":**
- User provides range via "Other" option (e.g., "abc123..def456" or "HEAD~3..HEAD")
- Run `cd <local-repo> && git log <range> --format=%H --reverse` to get commits in order
- Store as array of commit hashes
- Note: `--reverse` ensures oldest commits are processed first

**If "Last N commits":**
- Ask user for N via "Other" option
- Run `cd <local-repo> && git log -n <N> <branch> --format=%H --reverse` to get last N commits
- Store as array of commit hashes

#### Show commits for confirmation:

1. For each commit hash in the array, get commit info:
   ```bash
   cd <local-repo> && git log -1 --format="%H %s" <commit-hash>
   ```

2. Display all commits that will be vendored:
   ```
   The following commits will be vendored in sequence:
   1. abc123: Fix memory leak in audio callback
   2. def456: Add support for spatial audio
   3. ghi789: Update documentation
   ```

3. Use `AskUserQuestion` to confirm:
   - **Proceed with these commits** (recommended)
   - **Cancel and start over**

If user cancels, return to Step 2b.

#### Set up for multi-commit loop:

Store the array of commit hashes and proceed to Step 2d to save the current HEAD.

### Step 2d: Save the current HEAD (for restoration after vendoring)

Before checking out commits, save the current branch or commit so we can restore it later:

```bash
cd <local-repo> && git symbolic-ref -q HEAD || git rev-parse HEAD
```

This command:
- Returns the branch name (e.g., `refs/heads/coreaudio-behavior`) if on a branch
- Returns the commit hash if in detached HEAD state

Store this value as `original_head` to restore at the end.

### Step 3: Identify the crate and its Firefox dependency

1. Read the `Cargo.toml` in the user's local repo to get the crate name
2. Search Firefox's `toolkit/library/rust/shared/Cargo.toml` to find where this crate is referenced as a git dependency
3. Identify the git URL used in Firefox (e.g., `https://github.com/mozilla/cubeb-coreaudio-rs`)
4. Show the user what you found:
   - Crate name
   - Current git URL in Firefox
   - Current revision
   - Vendored location in `third_party/rust/`
   - Selected branch/commit to vendor (from Step 2/2b)

### Step 4: Vendor the code

**CRITICAL REMINDERS:**
1. **Always use explicit paths or cd commands** - After running commands that change directories (especially when checking the local repo), ensure subsequent commands like `./mach build` are run from the Firefox root directory.
2. **Root Cargo.lock must be updated** - After making dependency changes, you MUST run `cargo update` from the Firefox root directory before building. The build system uses `--frozen` and will fail if Cargo.lock is out of sync.

**For Multiple Commits:** If the user chose to vendor multiple commits in Step 2b, you will loop through the commit array. For each commit, follow the steps below, then pause for user to commit before continuing to the next.

**Steps (repeat for each commit if multiple):**

**At the start of each commit iteration (for multiple commits only):**
- Display: "📦 Vendoring commit X of Y: <commit-hash> - <commit-message>"

1. Get the commit hash:
   - If user selected "Branch HEAD": Run `cd <local-repo> && git rev-parse <branch>`
   - If user selected "Single specific commit": Use the commit hash they selected in Step 2b
   - If user selected "Multiple commits": Use the current commit from the array

2. Check if the commit exists on `origin` remote (the main upstream repo):
   ```bash
   cd <local-repo> && git branch -r --contains <commit-hash> | grep "^  origin/"
   ```

3. **If commit IS on origin:** Use standard vendoring
   - Update the `rev` field in Firefox's `toolkit/library/rust/shared/Cargo.toml`
   - Run `cd <firefox> && cargo update -p <crate-name>` (from Firefox root directory)
   - Run `cd <firefox> && ./mach vendor rust --force` (from Firefox root directory)

4. **If commit is NOT on origin:** Ask user how to proceed

   **For multiple commits:** Only ask this question once at the beginning. Use the same approach (fork or path dependency) for all commits in the sequence.

   Use `AskUserQuestion` with options:
   - **Push to fork** - Push to user's fork and vendor from there. Works on try server.
   - **Path dependency (recommended for private/security work)** - Convert to path dependency. Works on try server without pushing anywhere.

   **IMPORTANT:** If the user mentions this is a security-sensitive fix or they don't want to expose code publicly, recommend the **Path dependency** option. This embeds the code in Firefox without any external references - only the try server and Phabricator reviewers will see the changes.

#### Option A: Push to fork (recommended for try testing)

This is the recommended approach because it works on Mozilla's try server.

**For multiple commits:** All commits must be pushed to the fork before vendoring begins. Either push the branch containing all commits, or push each commit individually and vendor from fork.

1. Ask user for their fork's remote name (e.g., `myfork`)

2. Ask user for the branch name to push (default: current branch name)

3. Push the commits to the fork:
   ```bash
   cd <local-repo> && git push <remote> <branch>:<target-branch-name>
   ```
   For multiple commits, this pushes the entire branch. Alternatively, if using specific commit hashes, ensure they're all pushed.

4. Get the fork's URL:
   ```bash
   cd <local-repo> && git remote get-url <remote>
   ```
   Convert SSH URLs to HTTPS if needed (e.g., `git@github.com:user/repo.git` → `https://github.com/user/repo`)

5. Update Firefox's `toolkit/library/rust/shared/Cargo.toml`:
   - Change the `git` URL to point to the fork
   - Update the `rev` to the new commit hash

6. Update root Cargo.lock (from Firefox root directory):
   ```bash
   cd <firefox> && cargo update -p <crate-name>
   ```

7. Vendor the crates (from Firefox root directory):
   ```bash
   cd <firefox> && ./mach vendor rust --force
   ```

8. Build to verify (from Firefox root directory):
   ```bash
   cd <firefox> && ./mach build
   ```

#### Option B: Path dependency (recommended for private/security work)

This approach embeds the code directly in Firefox using path dependencies. **No code is pushed to any public repository** - only the try server and Phabricator reviewers will see the changes.

**Best for:**
- Security-sensitive fixes that shouldn't be public until landed
- Any local changes you don't want to push to remote repos
- Testing changes before creating a public PR

**How it works:**
- Changes the dependency from `git = "..."` to `path = "..."`
- All code is committed directly into the Firefox tree
- Works on try server because paths are relative to the source tree

**Steps:**

**IMPORTANT:** All commands below (unless explicitly noted) should be run from the Firefox root directory. Use absolute paths to avoid working directory issues.

1. Checkout the selected branch or commit in the local repo:
   ```bash
   cd <local-repo> && git checkout <branch-or-commit-hash>
   ```
   - If user selected "Branch HEAD": use the branch name
   - If user selected "Specific commit": use the commit hash

   Verify the checkout was successful before proceeding.

2. Copy source files from local repo to vendored location:
   ```bash
   rsync -av --delete \
     --exclude='.git' \
     --exclude='target' \
     --exclude='.gitignore' \
     --exclude='<nested-crate-dirs>' \
     <local-repo>/ <firefox>/third_party/rust/<crate-name>/
   ```
   **Note:** Use absolute paths for both source and destination to avoid directory confusion.

3. Handle nested crates/workspaces if present:
   - Check if the crate has subdirectories with their own Cargo.toml
   - Copy those to their respective locations in `third_party/rust/` using absolute paths
   - **Important:** Update the vendored crate's `Cargo.toml` to fix internal path references:
     ```toml
     # Change from:
     nested-crate = { path = "nested-crate" }
     # To:
     nested-crate = { path = "../nested-crate" }
     ```

4. Update Firefox's `toolkit/library/rust/shared/Cargo.toml` to use path dependency:
   ```toml
   # Change from:
   my-crate = { git = "https://github.com/...", rev = "...", ... }
   # To:
   my-crate = { path = "../../../../third_party/rust/my-crate", ... }
   ```
   Note: The path is relative to the Cargo.toml location (`toolkit/library/rust/shared/`)

5. **CRITICAL**: Remove vendored Cargo.lock files and generate `.cargo-checksum.json`:

   Path dependencies in Firefox still require `.cargo-checksum.json` files. Without them, you'll get "failed to load source for dependency" errors.

   ```bash
   # Remove vendored Cargo.lock files (not needed for path deps)
   # Use absolute paths to Firefox root directory
   rm -f <firefox>/third_party/rust/<crate-name>/Cargo.lock
   rm -f <firefox>/third_party/rust/<nested-crate-name>/Cargo.lock

   # Generate .cargo-checksum.json for main crate
   cd <firefox>/third_party/rust/<crate-name> && python3 << 'EOF'
import hashlib, json, os
files = {}
for root, dirs, filenames in os.walk('.'):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for filename in filenames:
        if filename.startswith('.'): continue
        filepath = os.path.join(root, filename)
        relpath = os.path.relpath(filepath, '.')
        with open(filepath, 'rb') as f:
            files[relpath] = hashlib.sha256(f.read()).hexdigest()
with open('.cargo-checksum.json', 'w') as f:
    json.dump({"files": files, "package": ""}, f)
EOF

   # Repeat for nested crates
   cd <firefox>/third_party/rust/<nested-crate-name> && python3 << 'EOF'
import hashlib, json, os
files = {}
for root, dirs, filenames in os.walk('.'):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for filename in filenames:
        if filename.startswith('.'): continue
        filepath = os.path.join(root, filename)
        relpath = os.path.relpath(filepath, '.')
        with open(filepath, 'rb') as f:
            files[relpath] = hashlib.sha256(f.read()).hexdigest()
with open('.cargo-checksum.json', 'w') as f:
    json.dump({"files": files, "package": ""}, f)
EOF
   ```

6. **CRITICAL**: Update root Cargo.lock (from Firefox root directory):
   ```bash
   cd <firefox> && cargo update -p <crate-name>
   ```
   If there are nested crates, update them too:
   ```bash
   cd <firefox> && cargo update -p <crate-name> -p <nested-crate-name>
   ```

   **This step is essential** - the build system requires the root Cargo.lock to be updated before building. If you skip this step, the build will fail with a "--frozen" error.

7. Build to verify (from Firefox root directory):
   ```bash
   cd <firefox> && ./mach build
   ```

   **For multiple commits:** You can ask the user if they want to:
   - **Build after each commit** (slower but safer, catches issues early)
   - **Build only after the last commit** (faster, recommended if commits are known to be good)

**After vendoring each commit (for multiple commits only):**

1. Show a summary of what was vendored:
   ```
   ✓ Commit vendored successfully!

   Commit: <commit-hash>
   Message: <commit-message>
   Files updated:
   - third_party/rust/<crate-name>/
   - toolkit/library/rust/shared/Cargo.toml
   - Cargo.lock
   ```

2. Suggest a Firefox commit message:
   ```
   Suggested Firefox commit message:
   Update <crate-name> to <short-hash>

   <upstream-commit-message>

   Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
   ```

3. Ask the user if they want to commit now (using `AskUserQuestion`):
   - **Yes, commit now** - Create a Firefox commit with the suggested message
   - **No, I'll commit later** - Skip committing and continue

   If user chooses "Yes, commit now":
   - Stage the changes: `git add Cargo.lock toolkit/library/rust/shared/Cargo.toml third_party/rust/<crate-name>/ third_party/rust/<nested-crate-name>/`
   - Create the commit with the suggested message
   - Verify with `git status` to confirm clean working tree

4. If this is NOT the last commit, ask the user:
   Use `AskUserQuestion`:
   - **Continue to next commit** - Vendor the next commit in sequence
   - **Stop here** - Stop the multi-commit process

   If user chooses "Continue", loop back to the beginning of Step 4 with the next commit.
   If user chooses "Stop", exit the multi-commit loop and proceed to Step 5.

5. If this IS the last commit:

   a. Show success message:
      ```
      ✓ All commits vendored successfully!

      Vendored X commits total.
      ```

   b. Restore the local repo HEAD to its original state:
      ```bash
      cd <local-repo> && git checkout <original_head>
      ```
      Where `<original_head>` is the value saved in Step 2d (either a branch name like `refs/heads/coreaudio-behavior` or a commit hash).

      If `original_head` starts with `refs/heads/`, extract just the branch name (e.g., `refs/heads/main` → `main`) before checking out.

   c. Then proceed to Step 5 of the main workflow.

**Before landing:** When the upstream PR is merged and ready to land in Firefox:
1. Change back from path to git dependency with the merged commit
2. Run `./mach vendor rust --force` to restore normal vendoring
3. Remove any path reference changes in vendored Cargo.toml files

### Step 5: Offer to run tests on try

**For multiple commits:** Only offer this after ALL commits have been vendored and committed by the user.

Ask the user: "Do you want to run tests on try?" with options:
- Yes, run recommended tests
- Yes, let me specify tests
- No, skip try push

**Note:** Must commit all changes before pushing to try. For multiple commits, this means all Firefox commits should be created first.

**Recommended tests for audio/cubeb crates:**
- `./mach try fuzzy -q 'cubeb'` - cubeb-specific tests
- `./mach try fuzzy -q 'audio'` - broader audio tests
- `./mach try auto` - let the system pick relevant tests

**For other crates**, recommend:
- `./mach try auto` - automatic test selection based on changes

If the user selects yes:
1. Commit changes if not already committed
2. Run the appropriate try command

### Error handling

- If the crate is not found in Firefox's dependencies, inform the user and ask if they want to add it as a new dependency
- If `./mach vendor rust` fails, show the error and suggest using `--force` flag
- If try push fails, show the error and suggest checking VPN/authentication

### Important notes

- **Do NOT use `[patch]` sections** with local filesystem paths for try testing - these paths don't exist on try machines
- When vendoring from a fork, remember to update the git URL back to the upstream repo (e.g., `mozilla/`) before landing the final patch
- The `--force` flag for `./mach vendor rust` bypasses cargo-vet errors that may be unrelated to your changes
- **For security-sensitive work:** Use the path dependency approach (Option B). This keeps all code within the Firefox commit - only try server and Phabricator reviewers see the changes. No public exposure until the fix is ready to land.
- **Commit messages for security work:** Do NOT include bug numbers or specific details in commit messages. Use vague messages like "Update <crate> for testing" to avoid exposing the nature of the fix. The bug number can be added later when the fix is ready to land publicly.
- When using path dependencies, remember to convert back to git dependencies before landing
- **Multi-commit workflow:** When vendoring multiple commits, the skill vendors each commit in sequence and pauses after each one for you to create a Firefox commit. This creates a clean commit history where each Firefox commit corresponds to one upstream commit. You can stop the sequence at any time.
