---
name: security-approval
description: Help prepare a Firefox security approval request by analyzing local commits/changes and drafting answers to the sec-approval questionnaire. Use when setting sec-approval? on a Bugzilla bug.
argument-hint: "[bug-id]"
allowed-tools:
  - Bash(git:*)
  - Bash(jj:*)
  - Bash(searchfox-cli:*)
  - Read
  - Grep
  - Glob
  - AskUserQuestion
---

# Security Approval Skill

This skill helps you prepare the answers to the Firefox security approval
questionnaire needed when setting `sec-approval?` on a Bugzilla bug.

Reference: https://firefox-source-docs.mozilla.org/bug-mgmt/processes/security-approval.html

**Bug ID** (if provided): $0

---

## Step 1: Gather Patch Context

### Retrieve the bug (if ID provided)

If a bug ID was given, fetch it via the MCP tool `mcp__moz__get_bugzilla_bug`
to understand the vulnerability type, severity, and any existing comments.
Note the `sec-*` keyword (sec-critical, sec-high, sec-moderate, sec-low) and
the `status-firefox*` flags.

### Inspect the local changes

Determine which VCS is in use and read the relevant commits:

```bash
# Check if using jj or git
jj --version 2>/dev/null && echo "jj" || echo "git"
```

**If jj:**
```bash
jj log -T builtin_log_detailed -r 'trunk()..@'
jj diff -r 'trunk()..@'
```

**If git:**
```bash
git log --oneline origin/main..HEAD
git diff origin/main..HEAD
```

Collect:
- Commit messages (check-in comments)
- All changed files
- The full diff

---

## Step 2: Check for Automatic Approval Eligibility

Before drafting the questionnaire, check if the patch qualifies for **automatic
approval** (i.e., no explicit `sec-approval` needed):

1. Bug has severity **sec-low**, **sec-moderate**, or **sec-other/sec-want**
2. OR the bug is a **recent unshipped regression** — all affected `status-firefox*`
   flags are marked `affected` only on Nightly/Beta with no release versions affected

If either condition is met, inform the user they may be able to land without
explicit approval. Ask if they still want to prepare the questionnaire (useful
for sec-high/sec-critical, or when in doubt).

---

## Step 3: Analyze the Patch for Each Question

Work through the six questions systematically by examining the diff and commit
messages gathered in Step 1.

### Q1: Patch Visibility

**Question**: "How easily can the security issue be deduced from the patch?"

Analyze:
- Does the diff clearly show a specific memory safety fix (e.g., bounds check,
  null check, free ordering fix)?
- Are variable names, function names, or code structure self-explanatory about
  the vulnerability class?
- Could a malicious actor trivially write an exploit by reading the diff?

Rate as one of:
- **Obvious**: The patch directly reveals the vulnerability class and location.
  A security researcher would immediately understand it.
- **Moderate**: Requires some knowledge to connect the patch to the vulnerability.
- **Not obvious**: The fix is generic enough that it doesn't reveal the issue.

### Q2: Comments and Tests as Bulls-Eyes

**Question**: "Do comments in the patch, the check-in comment, or tests included
in the patch paint a bulls-eye on the security problem?"

Check for red flags in:
- **Commit message**: Does it mention "use-after-free", "buffer overflow",
  "heap overflow", "null deref", "crash", "memory corruption", CVE numbers,
  "attacker", "exploit"?
- **Code comments**: Are there inline comments explaining the security nature
  of the fix?
- **Test files**: Do test names, test content, or test file paths hint at the
  vulnerability? (e.g., `test_uaf_in_foo.html`)
- **Function/variable names**: Are any new names security-revealing?

Report specifically which parts (if any) are problematic.

### Q3: Affected Branches

**Question**: "Which older supported branches are affected by this flaw?"

Check `status-firefox*` flags from the bug (if fetched). If not available,
inspect the code history:

```bash
# Find when the vulnerable code was introduced
git log --oneline --follow -p -- <affected-file> | head -100
```

Current Firefox release channels to consider (check MDN/wiki for current
version numbers if needed):
- **Nightly** (main/trunk)
- **Beta**
- **ESR 128** (if still supported)
- **ESR 115** (if still supported)
- **Release**

Cross-reference with the `status-firefoxNN: affected/unaffected/fixed` flags
on the bug if available.

### Q4: Regression Source

**Question**: "If not all supported branches, which bug introduced the flaw?"

Only needed if Q3 shows some branches are unaffected. Use git bisect or blame
to find the introducing commit:

```bash
git log --oneline -- <affected-file> | head -30
git blame -L <line>,<line> <affected-file>
```

Report the bug number or commit that introduced the flaw, which determines
the oldest affected branch.

### Q5: Backport Status

**Question**: "Do you have backports for the affected branches? If not, how
different, hard to create, and risky will they be?"

Ask the user:
- Are backports already prepared?
- If not: review the diff complexity to assess backport risk:
  - **Low risk**: Small, self-contained change in code that hasn't diverged
  - **Medium risk**: Moderate change, code has some differences across branches
  - **High risk**: Large refactor, depends on other recent changes, or code
    has significantly diverged

### Q6: Regression Risk and Testing

**Question**: "How likely is this patch to cause regressions; how much testing
does it need?"

Assess:
- **Size**: Number of lines changed
- **Scope**: How many call sites / how core is the changed component?
- **Test coverage**: Are there existing tests? Is a new test included?
- **Change type**: Pure addition (lower risk) vs. behavioral change (higher risk)

Rate as:
- **Low**: Minimal, well-tested, targeted fix with no API changes
- **Moderate**: Some risk, needs test run on affected platforms
- **High**: Significant change, needs thorough testing including edge cases

---

## Step 4: Flag Potential Issues

Before drafting the final text, flag any issues that should be addressed:

- **Revealing commit message**: If the commit message mentions vulnerability
  class explicitly, suggest a generic alternative. Examples:
  - Bad: `Fix use-after-free in MediaDecoder::Shutdown`
  - Good: `Improve lifetime management in MediaDecoder`
  - Bad: `Fix heap buffer overflow when parsing VP9`
  - Good: `Add validation for buffer size in VP9 decoder`

- **Revealing code comments**: If inline comments describe the vulnerability,
  suggest removing or generalizing them.

- **Revealing test names/content**: If test files have security-revealing names
  or content, suggest renaming or sanitizing.

- **Try push**: Remind the user to **not push to Try** with the bug number or
  security-revealing tests. If they need CI, they should omit bug numbers and
  tests from the try push.

Present these issues clearly before generating the questionnaire text.

---

## Step 5: Draft the Questionnaire

Generate the complete text to paste into the Bugzilla comment when requesting
`sec-approval?`. Use this format:

```
[Requesting sec-approval]

1. How easily can the security issue be deduced from the patch?
   <answer>

2. Do comments in the patch, the check-in comment, or tests included in the
   patch paint a bulls-eye on the security problem?
   <answer>

3. Which older supported branches are affected by this flaw?
   <answer>

4. If not all supported branches, which bug introduced the flaw?
   <answer — or "N/A, all branches affected">

5. Do you have backports for the affected branches? If not, how different,
   hard to create, and risky will they be?
   <answer>

6. How likely is this patch to cause regressions; how much testing does
   it need?
   <answer>
```

Keep answers factual, specific, and concise. Do not reveal more about the
vulnerability than necessary.

---

## Step 6: Present Summary and Confirm

Present to the user:

1. **Any issues found** (revealing comments, commit messages, test names) with
   suggested fixes — ask if they want help fixing them now.

2. **The draft questionnaire text** to copy into Bugzilla.

3. **Checklist reminder**:
   - [ ] Commit message is not security-revealing
   - [ ] No security-revealing inline comments in the patch
   - [ ] Tests don't paint a bulls-eye
   - [ ] Not pushed to Try with bug number / security tests
   - [ ] Bug is filed as restricted/sec-* on Bugzilla

Ask the user if they want to revise any answer before finalizing.

---

## Tips

- Security keywords in Firefox: `sec-critical`, `sec-high`, `sec-moderate`,
  `sec-low`, `sec-other`, `sec-want`
- The security team is primarily concerned about `sec-high` and `sec-critical`
  bugs that land before a public release
- Backports to ESR require separate approval; mention this if ESR is affected
- If the patch is on an uplift request (not main/nightly), that changes the
  urgency and review process
