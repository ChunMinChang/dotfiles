---
name: update-media-lib
description: Update third-party media libraries (libvpx, libdav1d, libaom, libopus, libcubeb, etc.) in the Firefox media/ directory. Use when updating codecs, decoders, or vendored media packages.
---

# Update Media Libraries

## Overview

This skill helps update vendored third-party media libraries in Firefox. Each library has its own update process documented in its README and moz.yaml files.

## Supported Libraries

### Fully Automated (mach vendor)

| Library | Path | Source Location | Update Method |
|---------|------|-----------------|---------------|
| libvpx | media/libvpx | media/libvpx/libvpx/ | Two-step with patches |
| libaom | media/libaom | third_party/aom/ | Two-step with patches |
| libsoundtouch | media/libsoundtouch | media/libsoundtouch/ | Two-step with patches |
| libspeex_resampler | media/libspeex_resampler | media/libspeex_resampler/ | Two-step with patches |
| highway | media/highway | third_party/highway/ | Two-step with patches |
| libcubeb | media/libcubeb | media/libcubeb/ | Two-step with patches |
| libpng | media/libpng | media/libpng/ | Two-step with patches |
| libogg | media/libogg | media/libogg/ | Two-step with patches |
| libyuv | media/libyuv | media/libyuv/libyuv/ | Two-step with patches |
| libdav1d | media/libdav1d | third_party/dav1d/ | Simple vendor |
| libvorbis | media/libvorbis | media/libvorbis/ | Simple vendor (file renames) |
| libwebp | media/libwebp | media/libwebp/ | Simple vendor |
| libjxl | media/libjxl | third_party/jpeg-xl/ | Simple vendor |
| libnestegg | media/libnestegg | media/libnestegg/ | Simple vendor |
| libopus | media/libopus | media/libopus/ | Script-based (update.sh) |
| Rust crates (git) | (Cargo.toml) | third_party/rust/* | Git crate (update rev + cargo update + mach vendor rust) |
| Rust crates (crates.io) | (Cargo.toml) | third_party/rust/* | Crates.io (update version + cargo update + mach vendor rust) |
| libjpeg | media/libjpeg | media/libjpeg/ | Script-based (update-libjpeg.sh) |

### Manual Update Required (Cannot Auto-Update)

| Library | Path | Reason | Update Method |
|---------|------|--------|---------------|
| ffvpx | media/ffvpx | Requires platform-specific config regeneration | Manual rsync + config generation |
| libmkv | media/libmkv | No vendoring section, upstream abandoned | Cannot update |

## Related Skills

If you have **local changes** to a Rust crate that you want to test before they're merged upstream, use `/vendor-local` instead. This skill (`/update-media-lib`) is for pulling the **latest upstream release** from remote repositories.

## Initial Question: Update Type

**IMPORTANT:** Before starting any work, determine what kind of update the user needs. If the user's request clearly indicates one type (e.g., they provide a commit URL to cherry-pick, or say "update to latest"), skip the question and proceed directly. Otherwise, use AskUserQuestion:

> "What type of update do you need?"
> - **Full library update** - Update the vendored library to a new upstream version
> - **Cherry-pick a specific commit** - Apply a single upstream commit to the current vendored source

If the user provides a URL to a specific commit or mentions "cherry-pick", go directly to the **Cherry-pick Process** section.
If the user asks to update to a version/tag or to latest, go to the **Full Update Process** section.

## Cherry-pick Process

Cherry-picking applies a single upstream commit directly to the vendored source without running `mach vendor`. This is useful for backporting security fixes or targeted bug fixes.

1. **Identify the library and commit** - Confirm the library and the upstream commit hash/URL
2. **Read moz.yaml** - Check `media/<lib>/moz.yaml` for the current vendored revision and upstream URL
3. **Fetch the upstream diff** - Use WebFetch to get the commit diff (e.g., from Googlesource `?format=TEXT` for base64-encoded diffs, or from GitHub)
4. **Verify the diff applies cleanly** - Read the affected files in the vendored source and confirm the pre-image (context lines) matches
5. **Ask for Bugzilla number** - Use AskUserQuestion to get an optional bug number
6. **Apply the changes** - Use Edit to apply each hunk from the diff to the corresponding vendored file (e.g., `media/<lib>/libvpx/path/to/file.c`)
7. **Build and test** - Run `./mach build` to verify

**Commit format for cherry-picks:**
If bug number provided:
- `Bug XXXXXX - Cherry-pick upstream <library> commit <short-hash>. <commit-subject>`

If no bug number:
- `Cherry-pick upstream <library> commit <short-hash>. <commit-subject>`

**Verifying compatibility across branches:**
When the user asks whether a cherry-pick applies cleanly on a specific Firefox release (e.g., Firefox 147):
1. Find the Firefox release date (use WebSearch)
2. Find which libvpx version was vendored at that time: `git log --oneline --before="<date>" -1 -- media/<lib>/moz.yaml`
3. Read the file at that commit: `git show <commit>:media/<lib>/path/to/file.c`
4. Compare the pre-image lines from the diff against the file content at that revision

## Full Update Process

1. **Identify the library** - Confirm which library needs updating
2. **Check limitations** - Verify the library can be auto-updated (see table above)
3. **Read the README** - Check `media/<lib>/README_MOZILLA` or `README.md` for library-specific instructions
4. **Check moz.yaml** - Review `media/<lib>/moz.yaml` for current version and upstream URL
5. **Ask about commit preference** - For two-step libraries, ask user if they want one combined commit or two separate commits
6. **Ask for Bugzilla number** - Optionally ask user for a bug number to include in commit messages
7. **Run the update command** - Execute the appropriate vendor command
8. **Apply patches if needed** - Some libraries require a second step for patches
9. **Build and test** - Verify the update works

## Update Patterns

### Two-step with patches

Libraries with local patches use a two-step process:

```bash
# Step 1: Update the source (without patches)
./mach vendor media/<lib>/moz.yaml --patch-mode=none

# Step 2: Apply local patches
./mach vendor media/<lib>/moz.yaml --patch-mode=only --ignore-modified
```

**Two-step libraries:** libvpx, libaom, libsoundtouch, libspeex_resampler, highway, libcubeb, libpng, libogg, libyuv

**IMPORTANT - Commit Workflow:**
For two-step libraries, ALWAYS ask the user whether they want:
1. **Two separate commits** (recommended by upstream README):
   - First commit: "Update <library> to <version>" (after step 1)
   - Second commit: "Apply local patches to <library>" (after step 2)
2. **Single combined commit**:
   - One commit after both steps: "Update <library> to <version> and apply local patches"

**IMPORTANT - Bugzilla Bug Number:**
ALWAYS ask the user if they have a Bugzilla bug number for this update. This should be asked alongside the commit preference question using AskUserQuestion.

If user provides a bug number, format commit messages as:
- `Bug XXXXXX - Update <library> to <version>`
- `Bug XXXXXX - Apply local patches to <library>`

If no bug number is provided, use the standard format without the "Bug XXXXXX - " prefix.

Use AskUserQuestion to get both the commit preference and optional bug number before proceeding.

### Simple vendor

Libraries without patches or with auto-applied patches:

```bash
# Update to latest
./mach vendor media/<lib>/moz.yaml

# Or update to specific version/commit
./mach vendor media/<lib>/moz.yaml -r <tag-or-commit>

# Or update from a fork
./mach vendor media/<lib>/moz.yaml --repo <repository-url> -r <commit>
```

**Simple vendor libraries:** libdav1d, libvorbis, libwebp, libjxl, libnestegg

**Commit format for simple vendor:**
Ask for optional Bugzilla bug number. If provided:
- `Bug XXXXXX - Update <library> to <version>`

If no bug number:
- `Update <library> to <version>`

### Script-based (libopus)

libopus uses a custom update script integrated with mach vendor:

```bash
./mach vendor media/libopus/moz.yaml
```

The update.sh script is automatically invoked during vendoring.

### Script-based (libjpeg)

libjpeg uses a custom update script that requires cloning the upstream repository first.

**Known issue with patch step:**
The script runs `patch -p0` from `media/libjpeg/`, but the patch file (`mozilla.diff`) contains paths like `a/media/libjpeg/jmorecfg.h`. With `-p0`, patch looks for `a/media/libjpeg/jmorecfg.h` relative to current directory, which doesn't exist. This is documented in MOZCHANGES: *"fix up any rejects from applying the Mozilla specific patches"*.

**Workaround:** After the script fails at the patch step, apply manually with `-p1` from Firefox root (strips the `a/` prefix).

**Update process:**

1. Clone libjpeg-turbo to a temporary directory:
   ```bash
   git clone https://github.com/libjpeg-turbo/libjpeg-turbo.git /tmp/libjpeg-turbo
   ```

2. Run the update script (patch step will fail - this is expected per MOZCHANGES):
   ```bash
   ./media/update-libjpeg.sh /tmp/libjpeg-turbo [tag]
   # Example: ./media/update-libjpeg.sh /tmp/libjpeg-turbo 2.1.5.1
   ```

3. When prompted about patch failure, skip (press Enter or 'y')

4. Apply the patch manually from the Firefox root directory:
   ```bash
   patch -p1 -i media/libjpeg/mozilla.diff
   ```

5. Clean up temporary clone:
   ```bash
   rm -rf /tmp/libjpeg-turbo
   ```

**Version compatibility:**
- Versions 2.x: Compatible with current file structure
- Versions 3.x: Reorganized source structure (files in `src/` subdirectory) - may require additional work

**Commit format:**
Ask for optional Bugzilla bug number. If provided:
- `Bug XXXXXX - Update libjpeg-turbo to <version>`

If no bug number:
- `Update libjpeg-turbo to <version>`

### Rust crates

Rust crates are defined in `/toolkit/library/rust/shared/Cargo.toml` and vendored into `/third_party/rust/`. There are two types:

#### Git-based Rust crates

Crates with a `git` URL and `rev` attribute pointing to a specific commit.

**Examples:**
- `mp4parse_capi` - MP4 parser (https://github.com/mozilla/mp4parse-rust)
- `cubeb-coreaudio` - macOS audio backend (https://github.com/mozilla/cubeb-coreaudio-rs, default branch: `trailblazer`)
- `cubeb-pulse` - PulseAudio backend (https://github.com/mozilla/cubeb-pulse-rs)
- `audioipc2-client` / `audioipc2-server` - Audio IPC (https://github.com/mozilla/audioipc)

**Update process:**

1. Find the current revision in `/toolkit/library/rust/shared/Cargo.toml`:
   ```toml
   <crate-name> = { git = "https://github.com/...", rev = "<current-rev>", ... }
   ```

2. Get the new revision (commit hash or tag) from upstream repository

3. Update the `rev` attribute in Cargo.toml to the new revision

4. Update Cargo.lock to reflect the new revision:
   ```bash
   cargo update -p <crate-name>
   ```

5. Run the vendor command:
   ```bash
   ./mach vendor rust
   # Use --force if needed for large files
   ./mach vendor rust --force
   ```

6. Verify expected changes in `/third_party/rust/<crate-name>*`

7. **Run cargo vet** to check for missing audits:
   ```bash
   ./mach cargo vet suggest 2>&1 | head -20
   ```

8. **Add required audits** if any crates need certification (see crates.io section below for examples)

9. Include `supply-chain/audits.toml` in the commit if audits were added

**Commit format:**
Ask for optional Bugzilla bug number. If provided:
- `Bug XXXXXX - Update <crate-name> to <revision>`

If no bug number:
- `Update <crate-name> to <revision>`

#### Crates.io Rust crates

Crates with a `version` attribute, pulled from crates.io.

**Examples:**
- `cubeb-sys` - Cubeb native bindings (bundles libcubeb C code)

**Update process:**

1. Find the current version in `/toolkit/library/rust/shared/Cargo.toml`:
   ```toml
   <crate-name> = { version = "<current-version>", ... }
   ```

2. Check available versions on crates.io:
   ```bash
   cargo search <crate-name> --limit 1
   ```

3. **Ask the user** what version they want to update to. Present the current version, latest available version, and ask for their preferred target version.

4. Update the `version` attribute in Cargo.toml to the chosen version

5. Update Cargo.lock to reflect the new version:
   ```bash
   cargo update -p <crate-name>
   ```

6. Run the vendor command:
   ```bash
   ./mach vendor rust
   # Use --force if needed for large files
   ./mach vendor rust --force
   ```

7. Verify expected changes in `/third_party/rust/<crate-name>*`

8. **Run cargo vet** to check for missing audits:
   ```bash
   ./mach cargo vet suggest 2>&1 | head -20
   ```

9. **Add required audits** for each crate that needs certification:
   ```bash
   ./mach cargo vet certify <crate-name> <old-version> <new-version> --criteria safe-to-deploy --accept-all
   ```

   For example, when updating cubeb crates from 0.30.1 to 0.32.0:
   ```bash
   ./mach cargo vet certify cubeb 0.30.1 0.32.0 --criteria safe-to-deploy --accept-all
   ./mach cargo vet certify cubeb-backend 0.30.1 0.32.0 --criteria safe-to-deploy --accept-all
   ./mach cargo vet certify cubeb-core 0.30.1 0.32.0 --criteria safe-to-deploy --accept-all
   ./mach cargo vet certify cubeb-sys 0.30.1 0.32.0 --criteria safe-to-deploy --accept-all
   ```

10. Include `supply-chain/audits.toml` in the commit

**Commit format:**
Ask for optional Bugzilla bug number. If provided:
- `Bug XXXXXX - Update <crate-name> to <version>`

If no bug number:
- `Update <crate-name> to <version>`

## Limitations and Known Issues

### libaom
- **Issue:** `generate_sources_mozbuild.sh` requires `python3-venv` system package
- **Solution:** Install `python3-venv` before updating: `apt install python3-venv`

### libdav1d
- **Issue:** May require manual moz.build updates for new/removed files
- **Post-update:** Check `moz.build` and `asm/moz.build` for file changes
- **Note:** Assembly files with `%if ARCH_X86_64` may need conditional handling

### libmkv
- **Issue:** Cannot be auto-updated - no vendoring section in moz.yaml
- **Reason:** Upstream (Chromium libvpx) is abandoned
- **Status:** Maintenance only, manual patches required

### ffvpx
- **Issue:** Cannot use mach vendor
- **Update method:** Manual rsync from FFmpeg source
- **Requires:** Platform-specific config regeneration for each target (Unix32, Unix64, Darwin, Windows, Android)
- **See:** `media/ffvpx/README_MOZILLA` for detailed instructions

## Key Files

For each library:
- `media/<lib>/moz.yaml` - Version info, upstream URL, vendoring configuration, patches list
- `media/<lib>/README_MOZILLA` or `README.md` - Detailed update instructions
- `media/<lib>/*.patch` - Local patches to apply

Some libraries store source in `third_party/`:
- `third_party/dav1d/` - dav1d source
- `third_party/aom/` - AOM source
- `third_party/highway/` - highway source
- `third_party/jpeg-xl/` - libjxl source

## Post-Update Steps

1. **Build**: `./mach build`
2. **Lint**: `./mach lint`
3. **Format**: `./mach format`
4. **Cargo vet** (for Rust crate updates): `./mach cargo vet suggest` - add any required audits
5. **Test**: `./mach test --auto`

## Backporting Rust Crate Updates to ESR/Beta/Release

When a Rust crate update on central needs to be uplifted to older branches (ESR, beta, release), the process differs from a normal update because each branch may pin a different base revision of the crate.

### Overview

1. Identify the base revision on each target branch
2. Create backport branches upstream if needed
3. Vendor the backported revision on each Firefox branch
4. Clean up vendoring noise
5. Push to try and verify builds

### Step 1: Identify Base Revisions

Check what revision each branch uses:

```bash
# For each branch (esr140, beta, release)
git show origin/<branch>:toolkit/library/rust/shared/Cargo.toml | grep <crate-name>
```

Branches often share the same base revision (e.g., beta and release), so you may only need one or two backport branches.

### Step 2: Create Backport Branches (if needed)

If the upstream commit doesn't apply cleanly to a branch's base revision, create a backport branch on the upstream repo:

```bash
git clone <upstream-repo-url> /tmp/<repo>
cd /tmp/<repo>

# Create backport branch from the branch's base revision
git checkout -b backport-<branch> <base-revision>

# Cherry-pick the commit(s) from central's update
git cherry-pick <commit-hash>

# Push the backport branch
git push origin backport-<branch>
```

Note the resulting commit hash — this becomes the new `rev` for that Firefox branch.

### Step 3: Vendor on the Target Branch

```bash
# Check out the target branch
git checkout -b <branch>-uplift upstream/<branch>

# Edit Cargo.toml with the backport revision
# In toolkit/library/rust/shared/Cargo.toml, update the rev for the crate

# Update Cargo.lock
cargo update -p <crate-name>

# Vendor
./mach vendor rust
```

**ESR branches may fail with cargo-vet errors** (policy drift from central). In this case, use `--force`:

```bash
./mach vendor rust --force
```

### Step 4: Clean Up `--force` Noise

`--force` re-vendors ALL crates, adding `.cargo_vcs_info.json`, `.github/`, `.travis.yml` and other files to every crate. This produces 1000+ changed files. Only the target crate's changes should be kept.

```bash
# Unstage everything
git reset HEAD

# Restore all modified files EXCEPT the ones we want to keep
git diff --name-only | grep -v -E '^(\.cargo/config\.toml\.in|Cargo\.lock|toolkit/library/rust/shared/Cargo\.toml|third_party/rust/<crate-name>/)' | xargs git checkout --

# Remove all untracked noise files, keeping only the target crate
git ls-files --others --exclude-standard | grep -v 'third_party/rust/<crate-name>/' | xargs rm -f

# Clean up empty directories
find third_party/rust -type d -empty -delete 2>/dev/null

# Verify only target files remain
git status --short
```

Expected files after cleanup:
- `.cargo/config.toml.in` — rev update
- `Cargo.lock` — lockfile update
- `toolkit/library/rust/shared/Cargo.toml` — rev update
- `third_party/rust/<crate-name>/.cargo-checksum.json` — updated checksums
- `third_party/rust/<crate-name>/src/...` — actual code changes

### Step 5: Push to Try

`mach try auto` may fail on older branches with bugbug timeout errors (the bugbug service can't classify tasks for non-central revisions). Use `mach try fuzzy` as a reliable alternative:

```bash
# Build-only (fastest verification)
./mach try fuzzy -q "'build"

# If mach try auto works on the branch, that's also fine
./mach try auto
```

### Notes

- **Security bugs:** Use a generic commit message like "test" with no bug number or details when pushing to try
- **Beta and release often share the same base revision**, so one backport branch may cover both
- **ESR branches** are more likely to have cargo-vet drift requiring `--force`
- The `--force` cleanup step is critical — without it you'll have 1000+ noise files in your patch

## Troubleshooting

- **Build failures after update**: Check for new source files not added to moz.build
- **Patch failures**: Patches may need updating for new upstream changes
- **Assembly errors on win32**: Move x86_64-only .asm files to conditional blocks
- **nasm version errors**: May need to update minimum nasm version in toolchain
- **python3-venv missing**: Install with `apt install python3-venv` (for libaom)
- **Uncommitted changes error**: Use `--ignore-modified` flag for step 2, or commit between steps
- **Cargo vet missing audit error**: Run `./mach cargo vet certify <crate> <old> <new> --criteria safe-to-deploy --accept-all` for each crate, then include `supply-chain/audits.toml` in the commit
