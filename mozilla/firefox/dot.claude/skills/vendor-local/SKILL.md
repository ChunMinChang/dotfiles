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

### Step 3: Identify the crate and its Firefox dependency

1. Read the `Cargo.toml` in the user's local repo to get the crate name
2. Search Firefox's `toolkit/library/rust/shared/Cargo.toml` to find where this crate is referenced as a git dependency
3. Identify the git URL used in Firefox (e.g., `https://github.com/mozilla/cubeb-coreaudio-rs`)
4. Show the user what you found:
   - Crate name
   - Current git URL in Firefox
   - Current revision
   - Vendored location in `third_party/rust/`

### Step 4: Vendor the code

1. Get the commit hash of the selected branch:
   ```bash
   cd <local-repo> && git rev-parse <branch>
   ```

2. Check if the commit exists on `origin` remote (the main upstream repo):
   ```bash
   cd <local-repo> && git branch -r --contains <commit-hash> | grep "^  origin/"
   ```

3. **If commit IS on origin:** Use standard vendoring
   - Update the `rev` field in Firefox's `toolkit/library/rust/shared/Cargo.toml`
   - Run `cargo update -p <crate-name>`
   - Run `./mach vendor rust --force`

4. **If commit is NOT on origin:** Ask user how to proceed

   Use `AskUserQuestion` with options:
   - **Push to fork** - Push to user's fork and vendor from there. Works on try server.
   - **Path dependency (recommended for private/security work)** - Convert to path dependency. Works on try server without pushing anywhere.

   **IMPORTANT:** If the user mentions this is a security-sensitive fix or they don't want to expose code publicly, recommend the **Path dependency** option. This embeds the code in Firefox without any external references - only the try server and Phabricator reviewers will see the changes.

#### Option A: Push to fork (recommended for try testing)

This is the recommended approach because it works on Mozilla's try server.

1. Ask user for their fork's remote name (e.g., `myfork`)

2. Ask user for the branch name to push (default: current branch name)

3. Push the commit to the fork:
   ```bash
   cd <local-repo> && git push <remote> <branch>:<target-branch-name>
   ```

4. Get the fork's URL:
   ```bash
   cd <local-repo> && git remote get-url <remote>
   ```
   Convert SSH URLs to HTTPS if needed (e.g., `git@github.com:user/repo.git` → `https://github.com/user/repo`)

5. Update Firefox's `toolkit/library/rust/shared/Cargo.toml`:
   - Change the `git` URL to point to the fork
   - Update the `rev` to the new commit hash

6. Update Cargo.lock:
   ```bash
   cargo update -p <crate-name>
   ```

7. Vendor the crates:
   ```bash
   ./mach vendor rust --force
   ```

8. Build to verify:
   ```bash
   ./mach build
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

1. Copy source files from local repo to vendored location:
   ```bash
   rsync -av --delete \
     --exclude='.git' \
     --exclude='target' \
     --exclude='.gitignore' \
     --exclude='<nested-crate-dirs>' \
     <local-repo>/ <firefox>/third_party/rust/<crate-name>/
   ```

2. Handle nested crates/workspaces if present:
   - Check if the crate has subdirectories with their own Cargo.toml
   - Copy those to their respective locations in `third_party/rust/`
   - **Important:** Update the vendored crate's `Cargo.toml` to fix internal path references:
     ```toml
     # Change from:
     nested-crate = { path = "nested-crate" }
     # To:
     nested-crate = { path = "../nested-crate" }
     ```

3. Update Firefox's `toolkit/library/rust/shared/Cargo.toml` to use path dependency:
   ```toml
   # Change from:
   my-crate = { git = "https://github.com/...", rev = "...", ... }
   # To:
   my-crate = { path = "../../../../third_party/rust/my-crate", ... }
   ```
   Note: The path is relative to the Cargo.toml location (`toolkit/library/rust/shared/`)

4. Update Cargo.lock:
   ```bash
   cargo update -p <crate-name>
   ```
   If there are nested crates, update them too:
   ```bash
   cargo update -p <crate-name> -p <nested-crate-name>
   ```

5. Build to verify:
   ```bash
   ./mach build
   ```

**Before landing:** When the upstream PR is merged and ready to land in Firefox:
1. Change back from path to git dependency with the merged commit
2. Run `./mach vendor rust --force` to restore normal vendoring
3. Remove any path reference changes in vendored Cargo.toml files

### Step 5: Offer to run tests on try

Ask the user: "Do you want to run tests on try?" with options:
- Yes, run recommended tests
- Yes, let me specify tests
- No, skip try push

**Note:** Must commit changes before pushing to try.

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
