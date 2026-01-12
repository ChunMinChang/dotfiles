# Claude Code Security Hooks

This document describes the Claude Code security hooks system that protects sensitive files from being read by Claude Code across all your projects.

## Overview

The security hooks system provides **system-wide protection** for sensitive files like SSH keys, API tokens, and credentials. Once installed, these hooks apply to all Claude Code sessions on your machine, regardless of which project you're working in.

## What It Protects

The security hooks block Claude Code from reading:

### Critical System Files
- **SSH Keys**: `~/.ssh/id_*` (private keys)
- **GPG Keys**: `~/.gnupg/secring.gpg`, `~/.gnupg/private-keys-v1.d/*`
- **Netrc**: `~/.netrc` (contains FTP/HTTP credentials)
- **Docker**: `~/.docker/config.json` (registry credentials)

### Cloud Provider Credentials
- **AWS**: `~/.aws/credentials`, `~/.aws/config`
- **Google Cloud**: `~/.config/gcloud/*`, `~/gcloud/credentials`
- **Azure**: `~/.azure/credentials`
- **DigitalOcean**: `~/.config/doctl/config.yaml`
- **Heroku**: `~/.netrc`

### Mozilla Developer Credentials
- **Phabricator**: `~/.arcrc` (contains Phabricator API tokens)
- **Pernosco**: `pernosco-submit` scripts (debugging service tokens)

### API Tokens and Secrets
- **GitHub**: `~/.config/gh/hosts.yml` (GitHub CLI tokens)
- **npm**: `~/.npmrc` (can contain auth tokens)
- **PyPI**: `~/.pypirc` (Python package index credentials)
- **Sensitive .env files**: Only blocks .env files containing keywords like `API_KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `PRIVATE_KEY`, `CLIENT_SECRET`, `AUTH_TOKEN`

### Password Managers and Browsers
- **KeePass**: `*.kdbx`
- **1Password**: `~/Library/Group Containers/*.1password`
- **LastPass**: `~/Library/Application Support/LastPass/*`
- **Browser credential stores**: Chrome, Firefox, Safari password databases

### macOS Keychain
- `~/Library/Keychains/*`

## What It Allows

The security hooks are designed to **not interfere with normal development**:

- **Source code**: All project files are accessible
- **Configuration**: Non-sensitive config files like `.eslintrc`, `package.json`, etc.
- **Build artifacts**: `~/.mozbuild/*` (Mozilla build directory), `node_modules/`, etc.
- **Non-sensitive .env**: Environment files without sensitive keywords are allowed
- **Git configs**: `.gitconfig` and `.git/config` are safe (don't contain secrets)

## Installation

### Install Security Hooks

```bash
# Install only security hooks
python setup.py --claude-security

# Install as part of full setup
python setup.py --all

# Dry run to see what would be installed
python setup.py --claude-security --dry-run
```

The installation:
1. Creates `~/.dotfiles-claude-hooks/` directory
2. Copies `security-read-blocker.py` hook script
3. Makes the hook executable
4. Backs up existing `~/.claude.json` to `~/.claude.json.backup-claude-security`
5. Merges security hooks into `~/.claude.json` (non-destructive)
6. Prints installation confirmation with file paths

**IMPORTANT**: You must restart Claude Code after installation for hooks to take effect.

### Verify Installation

```bash
# Show all installed hooks
python setup.py --show-claude-hooks

# View the security log
python setup.py --show-claude-security-log
```

### Remove Security Hooks

```bash
# Remove hooks (keeps backup)
python setup.py --remove-claude-security

# Dry run to see what would be removed
python setup.py --remove-claude-security --dry-run
```

## How It Works

### Hook Execution Flow

1. Claude Code attempts to use a tool (Read, Bash, Grep, or Glob)
2. **PreToolUse hook triggers** before the tool executes
3. Hook script receives JSON input via stdin:
   ```json
   {
     "tool_name": "Read",
     "tool_input": {"file_path": "/home/user/.ssh/id_rsa"}
   }
   ```
4. Hook checks file path against sensitive patterns
5. **If sensitive**: Exit code 2 (blocks tool), logs to file, prints error to stderr
6. **If safe**: Exit code 0 (allows tool to proceed)

### Pattern Matching

The hook uses glob-style patterns with `fnmatch`:

```python
# Example patterns
"~/.ssh/id_*"           # Matches id_rsa, id_ed25519, etc.
"~/.aws/credentials"    # Exact match
"*.kdbx"                # Any KeePass database
```

Patterns are expanded with `os.path.expanduser()` so `~` correctly resolves to your home directory.

### Content-Based .env Filtering

Instead of blocking all `.env` files, the hook reads the content and only blocks files containing sensitive keywords:

```bash
# BLOCKED - contains API_KEY
API_KEY=sk-1234567890
DATABASE_URL=postgresql://localhost/mydb

# ALLOWED - no sensitive keywords
NODE_ENV=development
DEBUG=true
PORT=3000
```

**Keywords that trigger blocking:**
- `API_KEY`, `SECRET`, `TOKEN`, `PASSWORD`
- `PRIVATE_KEY`, `CLIENT_SECRET`, `AUTH_TOKEN`
- `CREDENTIALS`, `PASSPHRASE`

### Logging

Every blocked attempt is logged to `~/.dotfiles-claude-hooks/security-blocks.log`:

```json
{"timestamp": "2026-01-09T12:34:56", "tool_name": "Read", "file_path": "~/.ssh/id_rsa", "reason": "Matches sensitive pattern: ~/.ssh/id_*"}
```

The hook also prints a clear error message to Claude Code:

```
[DOTFILES SECURITY] Blocked access to: /home/user/.ssh/id_rsa
[DOTFILES SECURITY] Reason: Matches sensitive pattern: ~/.ssh/id_*
[DOTFILES SECURITY] Override: export DOTFILES_CLAUDE_SECURITY_DISABLED=true
```

## Emergency Override

If you need to temporarily disable security hooks:

```bash
# Disable for current shell session
export DOTFILES_CLAUDE_SECURITY_DISABLED=true

# Run Claude Code
claude-code

# Re-enable (close terminal or unset)
unset DOTFILES_CLAUDE_SECURITY_DISABLED
```

**Warning**: Only use this if you fully trust the code you're working with and understand the risks.

## Configuration Files

### `~/.claude.json`

The hook is registered in your Claude Code configuration:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Bash|Grep|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "/home/user/.dotfiles-claude-hooks/security-read-blocker.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

### `~/.dotfiles-claude-hooks/`

```
~/.dotfiles-claude-hooks/
├── security-read-blocker.py    # Hook script
└── security-blocks.log         # Log file (created on first block)
```

## Whitelisting Files

If you need to allow Claude to read a specific sensitive file, you have two options:

### Option 1: Temporary Override (Recommended)

Use the environment variable for a single session:

```bash
export DOTFILES_CLAUDE_SECURITY_DISABLED=true
claude-code  # Work with sensitive files
unset DOTFILES_CLAUDE_SECURITY_DISABLED
```

### Option 2: Modify Hook Script

Edit `~/.dotfiles-claude-hooks/security-read-blocker.py` and add to `SAFE_PATTERNS`:

```python
SAFE_PATTERNS = [
    "~/.mozbuild/*",
    "/path/to/your/whitelisted/file",
]
```

After modifying, restart Claude Code.

## Troubleshooting

### Hook Not Blocking Files

1. **Check hook is installed**: `python setup.py --show-claude-hooks`
2. **Verify file exists**: `ls -la ~/.dotfiles-claude-hooks/security-read-blocker.py`
3. **Check permissions**: `ls -l ~/.dotfiles-claude-hooks/security-read-blocker.py` (should be executable)
4. **Restart Claude Code**: Hooks only load on startup
5. **Test hook manually**:
   ```bash
   echo '{"tool_name":"Read","tool_input":{"file_path":"~/.ssh/id_rsa"}}' | \
     ~/.dotfiles-claude-hooks/security-read-blocker.py
   echo $?  # Should be 2 (blocked)
   ```

### Hook Blocking Too Much

1. **Check what's blocked**: `python setup.py --show-claude-security-log`
2. **Review patterns**: `grep SENSITIVE_PATTERNS ~/.dotfiles-claude-hooks/security-read-blocker.py`
3. **Whitelist if needed**: Add to `SAFE_PATTERNS` in hook script
4. **Use override**: Export `DOTFILES_CLAUDE_SECURITY_DISABLED=true` temporarily

### Hook Not Running

1. **Verify ~/.claude.json syntax**: `python -m json.tool ~/.claude.json`
2. **Check for errors**: Look for hook execution errors in Claude Code output
3. **Timeout issues**: Default timeout is 5 seconds; increase in `~/.claude.json` if needed

### Multiple Hook Installations

If you accidentally install multiple times:

```bash
# Check for duplicates
python setup.py --show-claude-hooks | grep security-read-blocker

# Remove all security hooks
python setup.py --remove-claude-security

# Reinstall once
python setup.py --claude-security
```

## Testing

The repository includes a comprehensive test suite:

```bash
# Run all tests
python3 test_claude_security.py

# Test specific functionality
python3 test_claude_security.py 2>&1 | grep "Hook blocks SSH keys"
```

**Test coverage** (23 tests):
- Hook script behavior (8 tests)
- Logging functionality (2 tests)
- setup.py integration (6 tests)
- Hook installation (3 tests)
- Uninstallation (1 test)
- Cross-platform compatibility (1 test)
- Documentation (2 tests)

## Security Considerations

### What This Protects Against

- **Accidental exposure**: Prevents Claude from reading and potentially including sensitive data in responses
- **Log retention**: Claude conversations may be retained; hooks prevent sensitive data from entering logs
- **Copy-paste errors**: Stops you from accidentally sharing sensitive files

### What This Does NOT Protect Against

- **Malicious local code**: If you run malicious code locally, it can still access your files
- **Already-read data**: If Claude read a file before hooks were installed, that data may be in conversation history
- **Derived data**: If code prints secrets to stdout, Claude can still see them
- **Network access**: Hooks don't prevent network access to credential services

### Best Practices

1. **Install on all machines**: Run `python setup.py --claude-security` on every machine you use Claude Code
2. **Review logs periodically**: Check `~/.dotfiles-claude-hooks/security-blocks.log` for unexpected blocks
3. **Keep patterns updated**: If you add new credential files, update `SENSITIVE_PATTERNS` in the hook script
4. **Restart after changes**: Always restart Claude Code after modifying hooks or `~/.claude.json`
5. **Use override sparingly**: Only disable security when absolutely necessary and re-enable immediately after

## Advanced Usage

### Adding Custom Patterns

Edit `~/.dotfiles-claude-hooks/security-read-blocker.py`:

```python
SENSITIVE_PATTERNS = [
    # ... existing patterns ...
    "~/my-company/secrets/*",
    "*.pem",
    "/etc/ssl/private/*",
]
```

### Integration with Other Tools

The hook script can be used as a reference for other security tools:

```bash
# Test a file path
echo '{"tool_name":"Read","tool_input":{"file_path":"/path/to/test"}}' | \
  ~/.dotfiles-claude-hooks/security-read-blocker.py
```

### Monitoring Usage

```bash
# Count blocks
wc -l ~/.dotfiles-claude-hooks/security-blocks.log

# Most blocked files
jq -r .file_path ~/.dotfiles-claude-hooks/security-blocks.log | sort | uniq -c | sort -rn

# Recent blocks (last hour)
jq -r 'select(.timestamp > (now - 3600 | strftime("%Y-%m-%dT%H:%M:%S")))' \
  ~/.dotfiles-claude-hooks/security-blocks.log
```

## License

This security hooks system is part of the dotfiles repository and uses the same license.

## Support

If you encounter issues:

1. Check this documentation
2. Review test suite: `python3 test_claude_security.py`
3. Check logs: `python setup.py --show-claude-security-log`
4. File an issue in the repository

Remember: **Security is a shared responsibility**. These hooks provide protection, but you should still follow security best practices like using SSH agent forwarding, avoiding plaintext credentials, and regularly rotating secrets.
