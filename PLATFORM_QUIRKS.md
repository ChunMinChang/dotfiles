# Platform-Specific Quirks and Requirements

**Last Updated**: 2026-01-09
**Purpose**: Document known platform differences, quirks, and workarounds

---

## Quick Reference

| Issue | macOS | Linux | Workaround |
|-------|-------|-------|------------|
| Default shell | zsh (10.15+) | bash | Both supported automatically |
| Package manager | brew | apt/dnf/pacman | Auto-detected |
| sudo required? | No (brew) | Yes (apt) | Gracefully handled |
| TRASH location | ~/.Trash | ~/.local/share/Trash/files | Auto-configured |
| `open` command | Native | Needs alias | xdg-open aliased |
| vim variant | macvim | system vim | Both work |
| Startup file | .zshrc or .bash_profile | .bashrc | Both supported |

---

## macOS-Specific Quirks

### 1. Shell Changes in Catalina (10.15)
**Issue**: macOS switched from bash to zsh as default shell in 10.15 (Catalina)

**Impact**:
- macOS < 10.15: Uses bash, needs ~/.bash_profile
- macOS >= 10.15: Uses zsh, needs ~/.zshrc

**Solution**:
- setup.py detects macOS version using `sw_vers`
- Uses tuple comparison: `(major, minor) >= (10, 15)`
- Creates appropriate symlinks automatically

**Code Location**: `setup.py:127-144, 484-486`

### 2. Homebrew Path Differences
**Issue**: Homebrew installs to different locations on Intel vs Apple Silicon

**Paths**:
- Intel Macs: `/usr/local/bin/brew`
- Apple Silicon: `/opt/homebrew/bin/brew`

**Impact**:
- PATH must include correct homebrew location
- Both are usually in PATH by default from Homebrew installer

**Solution**:
- CommandExists function works for both
- Homebrew typically adds itself to PATH during installation
- No special handling needed

### 3. macvim vs vim
**Issue**: macOS users often install macvim via Homebrew

**Behavior**:
- macvim provides GUI and terminal versions
- Terminal version: `mvim -v`
- Regular vim still available as system version

**Solution** (dot.settings_darwin):
```bash
alias vim='mvim -v'
```
- Creates consistent `vim` command
- Works in terminal
- Uses macvim features

### 4. Version Parsing Pitfall (FIXED)
**Issue**: macOS versions like "10.10" were incorrectly parsed as float

**Problem** (before fix):
```python
float("10.10") = 10.1  # Loses trailing zero!
10.9 > 10.1  # Wrong! Should be 10.10 > 10.9
```

**Solution** (implemented in setup.py):
```python
parts = version.split('.')
major, minor = int(parts[0]), int(parts[1])
if (major, minor) >= (10, 15):  # Tuple comparison
```

**Status**: ✅ Fixed in Item 1.5

### 5. M1/M2/M3 Apple Silicon (ARM64)
**Issue**: Some tools may need ARM64 or x86_64 versions

**Status**:
- Python: Works natively on ARM64 ✓
- Homebrew: ARM64 version at /opt/homebrew ✓
- All tests pass on Apple Silicon ✓

**No special handling needed** - works out of the box

---

## Linux-Specific Quirks

### 1. Multiple Package Managers
**Issue**: Different distros use different package managers

**Package Managers**:
- Debian/Ubuntu: `apt-get` or `apt`
- Fedora/RHEL/Rocky: `dnf` (older: `yum`)
- Arch: `pacman`
- Alpine: `apk`
- SUSE: `zypper`

**Impact on shellcheck install**:
```bash
# Debian/Ubuntu
sudo apt-get install shellcheck

# Fedora/Rocky
sudo dnf install shellcheck

# Arch
sudo pacman -S shellcheck
```

**Current Solution**: Only apt-get is supported in setup.py
**Future Enhancement**: Add detection for other package managers

**Code Location**: `setup.py:791-818`

### 2. sudo Requirements
**Issue**: Most Linux package managers require sudo

**Behavior**:
- setup.py checks for sudo access: `sudo -n true`
- If no sudo, warns and skips shellcheck
- Other tools (ruff, black, markdownlint) don't need sudo

**Workaround for no-sudo users**:
```bash
# Manual shellcheck install from GitHub releases
wget https://github.com/koalaman/shellcheck/releases/...
```

**Code Location**: `setup.py:791-806`

### 3. No 'open' Command
**Issue**: Linux doesn't have macOS's `open` command

**Solution** (dot.settings_linux):
```bash
alias open='xdg-open'
```
- xdg-open is FreeDesktop standard
- Opens files with default application
- Works on most modern Linux distros

**Requirements**: xdg-utils package (usually pre-installed)

### 4. Wayland vs X11
**Issue**: Some GUI apps need special flags for Wayland

**Symptoms**:
- Apps may not start correctly on Wayland sessions
- May fall back to XWayland with degraded performance

**Solution** (dot.settings_linux):
```bash
function OpenWithWayland() {
    "$@" --enable-features=UseOzonePlatform --ozone-platform=wayland
}
```

**Usage**:
```bash
OpenWithWayland chromium
```

**Detection**: Check `$XDG_SESSION_TYPE` (returns "wayland" or "x11")

### 5. TRASH Directory Structure
**Issue**: Linux uses FreeDesktop.org Trash specification

**Path**: `~/.local/share/Trash/files/`

**Structure**:
```
~/.local/share/Trash/
├── files/        # Deleted files stored here
├── info/         # Metadata about deleted files
└── expunged/     # Permanently deleted (optional)
```

**Current Implementation**: Only uses `files/` directory
**Note**: Doesn't create .info files (not required for basic functionality)

### 6. pip3 Install Location
**Issue**: Linux pip installs user packages differently

**macOS**: `~/Library/Python/3.x/bin/`
**Linux**: `~/.local/bin/`

**Impact**: Both locations should be in PATH
**Solution**: setup.py doesn't modify PATH (user responsibility)

---

## Cross-Platform Quirks

### 1. PATH Differences
**Issue**: Different platforms have different default PATHs

**Common PATHs**:
```bash
# macOS
/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
/opt/homebrew/bin  # Apple Silicon
~/Library/Python/3.x/bin

# Linux
/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
~/.local/bin
```

**Impact**: May need to add directories to PATH manually
**Solution**: Users responsible for PATH configuration

### 2. Case Sensitivity
**Issue**: macOS file system is case-insensitive by default, Linux is case-sensitive

**Implications**:
- `File.txt` and `file.txt` are same file on macOS
- `File.txt` and `file.txt` are different files on Linux

**Impact on dotfiles**: None (we use lowercase consistently)
**Testing Note**: Always test on case-sensitive systems

### 3. Line Endings
**Issue**: Different platforms use different line endings

**Line Endings**:
- macOS/Linux: LF (`\n`)
- Windows: CRLF (`\r\n`)

**Current Handling**:
- .gitattributes could enforce LF
- Not currently an issue (no Windows support yet)

### 4. Python Versions
**Issue**: Different distros ship different Python versions

**Common Versions**:
- macOS 15: Python 3.9+ (via Homebrew)
- Ubuntu 24.04: Python 3.12
- Ubuntu 22.04: Python 3.10
- RHEL 9: Python 3.9

**Requirements**: Python 3.6+ (for f-strings, type hints)
**Current Usage**: No version-specific features beyond 3.6

### 5. Bash Versions
**Issue**: Different bash versions have different features

**Versions**:
- macOS: bash 3.2 (ancient, due to GPLv3 licensing)
- Linux: bash 4.0+ or 5.0+

**Impact**:
- Associative arrays (bash 4.0+) not available on macOS bash
- We use POSIX-compatible features only

**Current Status**: All scripts work with bash 3.2+ ✓

---

## Best Practices for Cross-Platform Code

### 1. Platform Detection
**Preferred Method**:
```python
import platform
system = platform.system()  # 'Darwin' or 'Linux'
```

**Alternative (bash)**:
```bash
PLATFORM=$(uname -s | tr '[:upper:]' '[:lower:]')
# Returns 'darwin' or 'linux'
```

### 2. Conditional Logic
```python
if platform.system() == 'Darwin':
    # macOS-specific code
elif platform.system() == 'Linux':
    # Linux-specific code
else:
    # Unsupported platform
    print_warning('Unsupported platform')
```

### 3. Path Construction
**DO**:
```python
path = os.path.join(HOME_DIR, '.bashrc')
```

**DON'T**:
```python
path = HOME_DIR + '/.bashrc'  # May break on Windows
```

### 4. Shell Compatibility
- Use POSIX-compatible features
- Avoid bash 4.0+ features (associative arrays, etc.)
- Test on both old (macOS) and new (Linux) bash versions
- Quote all variables: `"$var"` not `$var`

### 5. Graceful Degradation
```bash
if CommandExists tool; then
    # Use tool
else
    echo "Tool not available, skipping" >&2
fi
```

### 6. Don't Assume Package Managers
```python
# BAD: Assumes brew exists
subprocess.run(['brew', 'install', 'package'])

# GOOD: Check first
if is_tool('brew'):
    subprocess.run(['brew', 'install', 'package'])
elif is_tool('apt-get'):
    subprocess.run(['sudo', 'apt-get', 'install', 'package'])
```

---

## Testing Recommendations

### Before Committing Platform-Specific Code

1. **Test on both platforms** (if possible)
2. **Use platform-specific test cases**
3. **Document platform behavior** in code comments
4. **Add to CROSS_PLATFORM_TESTING.md** if significant

### Red Flags to Watch For

❌ Hardcoded paths: `/usr/local/bin/python3`
❌ Platform assumptions: "Everyone uses brew"
❌ Package manager assumptions: Only apt-get
❌ Shell version features: bash 4.0+ arrays
❌ Unquoted variables: `$var` instead of `"$var"`

✅ Use `os.path.join()` or `pathlib`
✅ Detect platform first: `platform.system()`
✅ Check tool exists: `CommandExists` or `is_tool()`
✅ POSIX-compatible shell code
✅ Quote all variables: `"$var"`

---

## Known Limitations

### Current
1. **Package managers**: Only brew (macOS) and apt-get (Linux/Debian) supported
2. **pip location**: Assumes ~/.local/bin or standard paths
3. **TRASH metadata**: Doesn't create .info files (FreeDesktop spec)
4. **Wayland**: Requires manual OpenWithWayland usage

### Future Enhancements
1. Add support for dnf, pacman, zypper package managers
2. Auto-detect Wayland and apply flags automatically
3. Implement full FreeDesktop Trash specification
4. Add Windows/WSL2 support
5. Add BSD support (FreeBSD, OpenBSD)

---

## Troubleshooting Guide

### macOS Issues

**Issue**: "zsh: command not found: brew"
**Solution**: Install Homebrew: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`

**Issue**: vim doesn't work correctly
**Solution**: Install macvim: `brew install macvim`

**Issue**: Wrong shell detected
**Solution**: Check macOS version with `sw_vers`, ensure >= 10.15 for zsh

### Linux Issues

**Issue**: "command not found: xdg-open"
**Solution**: Install xdg-utils: `sudo apt-get install xdg-utils`

**Issue**: shellcheck won't install (no sudo)
**Solution**: Install from GitHub releases or skip with --dev-tools (other tools only)

**Issue**: ~/.local/bin not in PATH
**Solution**: Add to ~/.bashrc: `export PATH="$HOME/.local/bin:$PATH"`

**Issue**: Wayland apps won't start
**Solution**: Use `OpenWithWayland` function or set environment variables

### Cross-Platform Issues

**Issue**: Different behavior on different platforms
**Solution**: Check CROSS_PLATFORM_TESTING.md for expected behavior

**Issue**: Test failures on one platform
**Solution**: Check platform-specific code, may need conditional logic

---

## References

- [Python platform module](https://docs.python.org/3/library/platform.html)
- [FreeDesktop Trash Specification](https://specifications.freedesktop.org/trash-spec/latest/)
- [macOS Shell Change (Catalina)](https://support.apple.com/en-us/HT208050)
- [Homebrew Documentation](https://docs.brew.sh/)
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/)

---

**Document Status**: ✅ Complete
**Last Updated**: 2026-01-09
**Maintained By**: Repository contributors
