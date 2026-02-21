---
name: security-approval
description: Help prepare a Firefox security approval request by analyzing local commits/changes and drafting answers to the sec-approval questionnaire. Use when setting sec-approval? on a Bugzilla bug.
argument-hint: "[bug-id]"
allowed-tools:
  - Bash(git:*)
  - Bash(jj:*)
  - Bash(searchfox-cli:*)
  - Bash(bmo-to-md:*)
  - Read
  - Grep
  - Glob
  - AskUserQuestion
  - Write
---

# Security Approval Skill

This skill has two phases:

1. **Compliance audit** — verify the patch strictly follows the
   [Fixing Security Bugs](https://firefox-source-docs.mozilla.org/bug-mgmt/processes/fixing-security-bugs.html)
   guidelines. Violations are a hard gate: they **must** be resolved before
   proceeding.
2. **Sec-approval questionnaire** — draft answers to the
   [Security Approval](https://firefox-source-docs.mozilla.org/bug-mgmt/processes/security-approval.html)
   questions.

**Bug ID** (if provided): $0

---

## Preliminary: Gather Patch Context

### Retrieve the bug (if ID provided)

Security bugs are private and **cannot** be fetched via the MCP tool
`mcp__moz__get_bugzilla_bug` — it will always fail for sec-* bugs. Instead:

1. **Ask the user for bug data**: ask whether they already have a local bug
   report (markdown files from `bmo-to-md`), and if so, where the files are
   located. If they provide a path, read the summary file there.
2. **If no local data exists**, use the `bmo-to-md` command:
   - Check that `bmo-to-md` is installed: run `bmo-to-md --help`. If not
     found, ask the user to install it: `cargo install bmo-to-md`
     (see <https://github.com/padenot/bmo-to-md>).
   - Check that a Bugzilla API key is configured: run `echo $BMO_API_KEY`.
     If empty, ask the user to set it up.
   - Ask the user where to save the files, then download:
     `bmo-to-md -o <folder> -a <bug_id>`
   - If `bmo-to-md` fails, **stop and report** to the user.
3. Read the summary to understand the vulnerability type, severity, and any
   existing comments. Note the `sec-*` keyword (sec-critical, sec-high,
   sec-moderate, sec-low) and the `status-firefox*` flags.

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

## Phase 1: Compliance Audit — Fixing Security Bugs

Audit the patch against **every** rule from the
[Fixing Security Bugs](https://firefox-source-docs.mozilla.org/bug-mgmt/processes/fixing-security-bugs.html)
guidelines. Work through each check below. For each one, report **PASS** or
**FAIL** with specifics. If any check fails, present concrete fixes and ask the
user to resolve them before moving to Phase 2.

### Check 1: Commit Messages

Commit messages **must not** contain any of the following:

- Nature of the vulnerability (overflow, use-after-free, XSS, CSP bypass,
  null deref, race condition, etc.)
- Exploitation methods or triggering mechanisms
- Security-related trigger words: "security", "exploitable", "vulnerable",
  "vulnerability", "CVE", "attacker", "exploit", "malicious", "crash"
  (when crash implies a security issue)
- Security approver names
- Affected Firefox versions or components in a security context
- Any phrasing that makes the patched vulnerability obvious

**If a commit message fails**: suggest a generic rewrite. Examples:

- Bad: `Fix use-after-free in MediaDecoder::Shutdown`
- Good: `Improve lifetime management in MediaDecoder`
- Bad: `Fix heap buffer overflow when parsing VP9`
- Good: `Add validation for buffer size in VP9 decoder`
- Bad: `Prevent XSS in content process`
- Good: `Strengthen input sanitization in content process`

Omitting a detailed commit message entirely is acceptable — details should go
in the private bug comment instead.

### Check 2: Code Comments

Inline comments in the diff **must not**:

- Reveal the nature of the vulnerability or exploitation vectors
- Disclose that the change is security-related
- Mention the bug as a security issue
- Reference CVE numbers or sec-* keywords

**If comments fail**: suggest removing them or rewriting them as generic
correctness/robustness comments. Security context belongs in the private bug,
not in the source.

### Check 3: Test Cases

Tests included in the patch **must not**:

- Have filenames that hint at the vulnerability (e.g., `test_uaf_in_foo.html`,
  `test_overflow_parser.js`)
- Contain comments or assertions that describe the security nature of the fix
- Include exploit-like test content that demonstrates the attack vector

Additionally, verify the test-landing policy:

- **If the bug affects released branches**: tests should generally **not** be
  landed with the fix. They should land in a follow-up at least 4 weeks after
  the release containing the fix ships. Suggest creating a cloned "task" bug
  (also security-sensitive) to track the deferred test landing, or setting the
  `in-testsuite` flag to `?`.
- **If the bug is a development-branch-only regression** (never shipped in a
  release): tests may land immediately.

**If tests fail**: suggest renaming, sanitizing test content, or splitting
tests into a deferred follow-up.

### Check 4: Try Server / CI

Check whether the user has pushed (or plans to push) to Try:

- **Best practice**: do not push to Try at all; test locally instead.
- **If a Try push is necessary**: remind the user to:
  - Get informal sec-approval first
  - Remove bug numbers from all commits in the Try push
  - Exclude vulnerability test cases entirely
  - Never disclose the vulnerability nature or triggering methods in the
    Try push commit message or mozconfig

Ask the user about their Try push status.

### Check 5: Patch Obfuscation

Review whether the fix can be plausibly framed as a non-security change
(performance improvement, correctness fix, code cleanup). The goal is to reduce
the identifiability of the security fix:

- Can the fix be bundled with other unrelated work?
- Does the diff look like a pure correctness or robustness improvement rather
  than a targeted security patch?

This is advisory — report observations but do not block on it.

### Compliance Verdict

Present a summary table:

| Check             | Status        | Details |
| ----------------- | ------------- | ------- |
| Commit messages   | PASS/FAIL     | ...     |
| Code comments     | PASS/FAIL     | ...     |
| Test cases        | PASS/FAIL     | ...     |
| Try server        | PASS/FAIL/N/A | ...     |
| Patch obfuscation | Advisory      | ...     |

Then present the checklist for the user to confirm:

- [ ] Commit message is not security-revealing
- [ ] No security-revealing inline comments in the patch
- [ ] Tests don't paint a bulls-eye (or are deferred to follow-up)
- [ ] Not pushed to Try with bug number / security tests
- [ ] Bug is filed as restricted/sec-* on Bugzilla

**If any check is FAIL**: present the specific violations with suggested fixes.
Ask the user if they want help fixing them now. Re-audit after fixes.

**This is a hard gate.** Ask the user to confirm all checklist items pass
before proceeding. Do not proceed to Phase 2 until Checks 1–4 all pass and the
user gives explicit approval to continue.

---

## Phase 2: Security Approval Questionnaire

### Step 1: Check for Automatic Approval Eligibility

Before drafting the questionnaire, check if the patch qualifies for **automatic
approval** (i.e., no explicit `sec-approval` needed):

1. Bug has severity **sec-low**, **sec-moderate**, or **sec-other/sec-want**
2. OR the bug is a **recent unshipped regression** — a specific regressing
   commit is identified, the developer has marked ESR and Beta status flags as
   `unaffected`, and the vulnerability only shipped in Nightly builds

If either condition is met, inform the user they may be able to land without
explicit approval. Ask if they still want to prepare the questionnaire (useful
for sec-high/sec-critical, or when in doubt).

### Step 2: Answer the Questionnaire

Work through all questions systematically by examining the diff and commit
messages gathered in the Preliminary step.

#### Q1: Patch Visibility

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

#### Q2: Comments and Tests as Bulls-Eyes

**Question**: "Do comments in the patch, the check-in comment, or tests included
in the patch paint a bulls-eye on the security problem?"

By this point, Phase 1 should have already caught and resolved any bulls-eyes.
Confirm that:

- Commit messages are clean (verified in Check 1)
- Code comments are clean (verified in Check 2)
- Test files are clean or deferred (verified in Check 3)

Report the current state — ideally "No, the patch has been reviewed for
information leaks."

#### Q3: Affected Branches

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
- **Release**
- **ESR** (check which ESR versions are currently supported)

Cross-reference with the `status-firefoxNN: affected/unaffected/fixed` flags
on the bug if available. If no regression range is identified, **assume the
worst** — all supported branches are affected.

#### Q4: Regression Source

**Question**: "If not all supported branches, which bug introduced the flaw?"

Only needed if Q3 shows some branches are unaffected. Use git blame to find the
introducing commit:

```bash
git log --oneline -- <affected-file> | head -30
git blame -L <line>,<line> <affected-file>
```

Report the bug number or commit that introduced the flaw, which determines the
oldest affected branch.

#### Q5: Backport Status

**Question**: "Do you have backports for the affected branches? If not, how
different, hard to create, and risky will they be?"

Ask the user:

- Are backports already prepared?
- If not: review the diff complexity to assess backport risk:
  - **Low risk**: Small, self-contained change in code that hasn't diverged
  - **Medium risk**: Moderate change, code has some differences across branches
  - **High risk**: Large refactor, depends on other recent changes, or code
    has significantly diverged

Note: backports to ESR require separate approval — mention this if ESR is
affected.

#### Q6: Regression Risk and Testing

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

#### Q7: Landing Readiness

**Question**: "Is the patch ready to land after security approval is given?"

Answer Yes or No. Consider whether:

- The patch has been reviewed (r+ on Phabricator)
- CI/try results are green (or local testing is sufficient)
- Any blockers remain

#### Q8: Android Affected

**Question**: "Is Android affected?"

Answer Yes, No, or Unknown. Check whether:

- The affected code paths are shared with Android (GeckoView)
- The code is desktop-only (e.g., Windows-specific compositing, macOS-only
  widget code) or cross-platform
- If the code is in `gfx/`, `dom/media/`, or other shared directories, it is
  likely Android-affected

### Step 3: Draft the Questionnaire

Generate the complete text to paste into the Bugzilla comment when requesting
`sec-approval?`. Use this format:

```text
[Requesting sec-approval]

1. How easily can the security issue be deduced from the patch?
   <answer>

2. Do comments in the patch, the check-in comment, or tests
   included in the patch paint a bulls-eye on the security
   problem?
   <answer>

3. Which older supported branches are affected by this flaw?
   <answer>

4. If not all supported branches, which bug introduced the
   flaw?
   <answer — or "N/A, all branches affected">

5. Do you have backports for the affected branches? If not,
   how different, hard to create, and risky will they be?
   <answer>

6. How likely is this patch to cause regressions; how much
   testing does it need?
   <answer>

7. Is the patch ready to land after security approval is
   given?
   <Yes/No>

8. Is Android affected?
   <Yes/No/Unknown>
```

Keep answers factual, specific, and concise. Do not reveal more about the
vulnerability than necessary.

### Step 4: Present and Confirm

Present to the user:

1. **The draft questionnaire text** to copy into Bugzilla.
2. A reminder that Phase 1 compliance was already verified (re-show the summary
   table if fixes were applied during this session).

Ask the user if they want to revise any answer before finalizing.

### Step 5: Generate Markdown File

After the user confirms they are satisfied with the questionnaire answers,
generate a markdown file at the repository root named
`sec-approval-bug-<bug_id>.md` (e.g., `sec-approval-bug-1234567.md`).
If no bug ID is available, use `sec-approval.md`.

The file should be plain text (no markdown headings, no indented answers,
no markdown list syntax). Format as follows:

```text
[Requesting sec-approval]

1. How easily can the security issue be deduced from the
patch?
<answer as a single flowing paragraph>

2. Do comments in the patch, the check-in comment, or tests
included in the patch paint a bulls-eye on the security
problem?
<answer as a single flowing paragraph>

3. Which older supported branches are affected by this flaw?
<answer as a single flowing paragraph>

4. If not all supported branches, which bug introduced the
flaw?
<answer as a single flowing paragraph>

5. Do you have backports for the affected branches? If not,
how different, hard to create, and risky will they be?
<answer as a single flowing paragraph>

6. How likely is this patch to cause regressions; how much
testing does it need?
<answer as a single flowing paragraph>

7. Is the patch ready to land after security approval is
given?
<Yes/No>

8. Is Android affected?
<Yes/No/Unknown>
```

Use the Write tool to create this file, then inform the user of the file path.

---

## Tips

- Security keywords in Firefox: `sec-critical`, `sec-high`, `sec-moderate`,
  `sec-low`, `sec-other`, `sec-want`
- The security team is primarily concerned about `sec-high` and `sec-critical`
  bugs that land before a public release
- Backports to ESR require separate approval; mention this if ESR is affected
- If the patch is on an uplift request (not main/nightly), that changes the
  urgency and review process
- When in doubt, assume worst-case severity and request sec-approval
- Contact the security team (needinfo) when uncertain about any guideline
