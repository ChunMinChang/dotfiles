---
name: update-media-lib
description: Update third-party media libraries (libvpx, libdav1d, libaom, libopus, libcubeb, etc.) in the Firefox media/ directory. Use when updating codecs, decoders, or vendored media packages.
---

# Update Media Libraries

## Overview

This skill helps update vendored third-party media libraries in Firefox. Each library has its own update process documented in its README and moz.yaml files.

## Supported Libraries

| Library | Path | Source Location | Update Method |
|---------|------|-----------------|---------------|
| libvpx | media/libvpx | media/libvpx/libvpx/ | mach vendor (two-step) |
| libdav1d | media/libdav1d | third_party/dav1d/ | mach vendor |
| libaom | media/libaom | third_party/aom/ | mach vendor (two-step) |
| libopus | media/libopus | media/libopus/ | update.sh script |
| libcubeb | media/libcubeb | media/libcubeb/ | mach vendor |
| libogg | media/libogg | media/libogg/ | mach vendor |
| libvorbis | media/libvorbis | media/libvorbis/ | mach vendor |
| libpng | media/libpng | media/libpng/ | mach vendor |
| libwebp | media/libwebp | media/libwebp/ | mach vendor |
| libyuv | media/libyuv | media/libyuv/ | mach vendor |

## Process

1. **Identify the library** - Confirm which library needs updating
2. **Read the README** - Check `media/<lib>/README_MOZILLA` or `README.md` for library-specific instructions
3. **Check moz.yaml** - Review `media/<lib>/moz.yaml` for current version and upstream URL
4. **Ask about commit preference** - For two-step libraries (with patches), ask user if they want one combined commit or two separate commits
5. **Ask for Bugzilla number** - Optionally ask user for a bug number to include in commit messages
6. **Run the update command** - Execute the appropriate vendor command
7. **Apply patches if needed** - Some libraries require a second step for patches
8. **Build and test** - Verify the update works

## Update Patterns

### Two-step with patches (libvpx, libaom)

Libraries with local patches use a two-step process:

```bash
# Step 1: Update the source (without patches)
./mach vendor media/libvpx/moz.yaml --patch-mode=none

# Step 2: Apply local patches
./mach vendor media/libvpx/moz.yaml --patch-mode=only --ignore-modified
```

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

### Simple vendor (libdav1d, libcubeb, libogg, etc.)

Most libraries use straightforward vendoring:

```bash
# Update to latest
./mach vendor media/libdav1d/moz.yaml

# Or update to specific version/commit
./mach vendor media/libdav1d/moz.yaml -r <tag-or-commit>

# Or update from a fork
./mach vendor media/libdav1d/moz.yaml --repo <repository-url> -r <commit>
```

**Commit format for simple vendor:**
Ask for optional Bugzilla bug number. If provided:
- `Bug XXXXXX - Update <library> to <version>`

If no bug number:
- `Update <library> to <version>`

### Script-based (libopus)

Some libraries use custom update scripts:

```bash
cd media/libopus && ./update.sh
```

## Key Files

For each library:
- `media/<lib>/moz.yaml` - Version info, upstream URL, vendoring configuration, patches list
- `media/<lib>/README_MOZILLA` or `README.md` - Detailed update instructions
- `media/<lib>/*.patch` - Local patches to apply

Some libraries store source in `third_party/`:
- `third_party/dav1d/` - dav1d source
- `third_party/aom/` - AOM source

## moz.yaml Structure

The moz.yaml file contains important metadata:

```yaml
origin:
  name: libvpx
  url: https://chromium.googlesource.com/webm/libvpx
  release: <commit-hash> (<date>)
  revision: <commit-hash>
  license: BSD-3-Clause

vendoring:
  url: <upstream-url>
  vendor-directory: <where-source-goes>
  patches:
    - patch1.patch
    - patch2.patch
```

## Post-Update Steps

1. **Build**: `./mach build`
2. **Lint**: `./mach lint`
3. **Format**: `./mach format`
4. **Test**: `./mach test --auto`

### Library-Specific Post-Update Tasks

**libdav1d** may require:
- Update `moz.build` and `asm/moz.build` for new/removed files
- Handle assembly files with `%if ARCH_X86_64` conditionals
- Move `*_tmpl.c` files to appropriate bitdepth_basenames lists
- Copy version headers if not auto-generated

**libvpx** may require:
- Run `generate_sources_mozbuild.sh` (usually done automatically)

## Troubleshooting

- **Build failures after update**: Check for new source files not added to moz.build
- **Patch failures**: Patches may need updating for new upstream changes
- **Assembly errors on win32**: Move x86_64-only .asm files to conditional blocks
- **nasm version errors**: May need to update minimum nasm version in toolchain
