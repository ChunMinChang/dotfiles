#!/usr/bin/env python3
"""
Claude Code Security Hook - Read Access Blocker
Prevents Claude from reading sensitive files across all projects.

Version: 1.0.0
Part of: dotfiles (github.com/chunminchang/dotfiles)
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from fnmatch import fnmatch

# Configuration
LOG_FILE = Path.home() / '.dotfiles-claude-hooks' / 'security-blocks.log'
DISABLE_ENV = "DOTFILES_CLAUDE_SECURITY_DISABLED"
WHITELIST_ENV = "DOTFILES_CLAUDE_SECURITY_WHITELIST"

# Sensitive file patterns (glob-style, ~ will be expanded)
SENSITIVE_PATTERNS = [
    # SSH keys
    "~/.ssh/id_*",
    "~/.ssh/*.pem",
    "~/.ssh/*_rsa",
    "~/.ssh/*_ed25519",
    "~/.ssh/*_ecdsa",
    "~/.ssh/*_dsa",
    "~/.gnupg/*",
    
    # Mozilla credentials
    "~/.arcrc",
    "~/.hgrc",
    "~/.moz-phab-config",
    "*/pernosco-submit",
    
    # Cloud credentials
    "~/.aws/credentials",
    "~/.aws/config",
    "~/.gcp/*.json",
    "~/.azure/credentials",
    "~/.config/gcloud/*credential*",
    
    # Git credentials
    "~/.git-credentials",
    "~/.config/gh/hosts.yml",
    "*/.git-credentials",
    
    # API tokens
    "~/.netrc",
    "~/.npmrc",
    "~/.pypirc",
    
    # Password managers
    "~/.password-store/*",
    "~/Library/Keychains/*",
    "~/.mozilla/firefox/*/key*.db",
    "~/.config/1Password/*",
    
    # Containers & clusters
    "~/.docker/config.json",
    "~/.kube/config",
    
    # Browser data
    "*/Cookies",
    "*/Login Data",
    "*/Web Data",
    
    # System
    "/etc/shadow",
]

# Explicitly safe patterns (always allow)
SAFE_PATTERNS = [
    "~/.mozbuild/*",
]

# Sensitive keywords for .env files
SENSITIVE_KEYWORDS = [
    'API_KEY', 'APIKEY', 'API_SECRET',
    'SECRET_KEY', 'SECRET', 'PRIVATE_KEY',
    'PASSWORD', 'PASSWD', 'PWD',
    'TOKEN', 'AUTH_TOKEN', 'ACCESS_TOKEN',
    'CREDENTIAL', 'CLIENT_SECRET',
    'AWS_SECRET', 'GCP_KEY',
    'PERNOSCO_USER_SECRET_KEY',
    'TASKCLUSTER_ACCESS_TOKEN',
    'BUGZILLA_API_KEY',
]


def matches_pattern(file_path, pattern):
    """Check if file_path matches glob pattern."""
    expanded_path = os.path.expanduser(file_path)
    expanded_pattern = os.path.expanduser(pattern)
    return fnmatch(expanded_path, expanded_pattern)


def is_safe_path(file_path):
    """Check if path is explicitly safe."""
    for pattern in SAFE_PATTERNS:
        if matches_pattern(file_path, pattern):
            return True
    return False


def is_sensitive_path(file_path):
    """Check if path matches sensitive patterns."""
    for pattern in SENSITIVE_PATTERNS:
        if matches_pattern(file_path, pattern):
            return True
    return False


def is_sensitive_env_file(file_path):
    """Check if .env file contains sensitive data."""
    if not (file_path.endswith('.env') or '.env.' in file_path):
        return False
    
    try:
        expanded = os.path.expanduser(file_path)
        if not os.path.exists(expanded):
            return False
        
        with open(expanded, 'r') as f:
            content = f.read().upper()
            return any(keyword in content for keyword in SENSITIVE_KEYWORDS)
    except:
        return False


def is_whitelisted(file_path):
    """Check if path is in whitelist."""
    whitelist = os.getenv(WHITELIST_ENV, "")
    if not whitelist:
        return False
    
    expanded_path = os.path.expanduser(file_path)
    return expanded_path in [os.path.expanduser(p.strip()) 
                              for p in whitelist.split(':') if p.strip()]


def log_block(hook_input, file_path, reason):
    """Log blocked access."""
    LOG_FILE.parent.mkdir(exist_ok=True)
    
    entry = {
        'timestamp': datetime.now().isoformat(),
        'tool_name': hook_input.get('tool_name', 'Unknown'),
        'file_path': str(file_path),
        'reason': reason,
        'session_id': hook_input.get('session_id', 'Unknown'),
        'cwd': hook_input.get('cwd', 'Unknown'),
    }
    
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except:
        pass
    
    sys.stderr.write(f"\n{'='*60}\n")
    sys.stderr.write(f"🔒 SECURITY HOOK: Blocked access to sensitive file\n")
    sys.stderr.write(f"{'='*60}\n")
    sys.stderr.write(f"Time:     {entry['timestamp']}\n")
    sys.stderr.write(f"Tool:     {entry['tool_name']}\n")
    sys.stderr.write(f"File:     {file_path}\n")
    sys.stderr.write(f"Reason:   {reason}\n")
    sys.stderr.write(f"Session:  {entry['session_id']}\n")
    sys.stderr.write(f"Directory: {entry['cwd']}\n")
    sys.stderr.write(f"\nThis access was blocked to protect sensitive credentials.\n")
    sys.stderr.write(f"Log file: {LOG_FILE}\n")
    sys.stderr.write(f"\nTo override (use with extreme caution):\n")
    sys.stderr.write(f"  export {DISABLE_ENV}=true\n")
    sys.stderr.write(f"{'='*60}\n\n")


def check_bash_command(hook_input, command):
    """Check if bash command accesses sensitive files."""
    for pattern in SENSITIVE_PATTERNS:
        pattern_simple = pattern.replace('*', '').replace('~/', '')
        if pattern_simple in command:
            return True
    return False


def main():
    # Emergency override
    if os.getenv(DISABLE_ENV) == "true":
        sys.exit(0)
    
    # Parse input
    try:
        hook_input = json.loads(sys.stdin.read())
    except:
        sys.exit(0)
    
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    file_path = None
    
    # Extract file path
    if tool_name == "Read":
        file_path = tool_input.get("file_path")
    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        if check_bash_command(hook_input, command):
            log_block(hook_input, command, "Bash command accessing sensitive file")
            sys.exit(2)
    elif tool_name in ["Grep", "Glob"]:
        file_path = tool_input.get("path", "")
    
    # Check file path
    if file_path:
        # Check safe patterns first
        if is_safe_path(file_path):
            sys.exit(0)
        
        # Check whitelist
        if is_whitelisted(file_path):
            sys.exit(0)
        
        # Check .env files
        if file_path.endswith('.env') or '.env.' in file_path:
            if is_sensitive_env_file(file_path):
                log_block(hook_input, file_path, "Contains sensitive environment variables")
                sys.exit(2)
            else:
                sys.exit(0)
        
        # Check sensitive patterns
        if is_sensitive_path(file_path):
            log_block(hook_input, file_path, "Contains sensitive credentials or keys")
            sys.exit(2)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
