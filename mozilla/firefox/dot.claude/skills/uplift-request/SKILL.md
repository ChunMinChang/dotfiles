---
name: uplift-request
description: Help prepare a Firefox uplift approval request (Beta, Release, and/or ESR) by checking whether patches are already on the bug, auditing sanitization once for sec-* bugs, and drafting the approval comment per https://wiki.mozilla.org/Release_Management/Uplift_rules. Use after a fix is ready and needs to ride into a stabilization branch. May or may not follow sec-approval (sec-moderate typically skips sec-approval but may still need uplift).
argument-hint: "[bug-id] [path-to-bug-report] [--beta] [--release] [--esr NN]"
allowed-tools:
  - Bash(git:*)
  - Bash(jj:*)
  - Bash(searchfox-cli:*)
  - Bash(bmo-to-md:*)
  - Bash(moz-phab:*)
  - Bash(python3:*)
  - Read
  - Grep
  - Glob
  - AskUserQuestion
  - WebFetch
  - Write
---

# Uplift Request Skill

Drafts a Bugzilla uplift-approval comment for Firefox Beta, Release, and/or
ESR, following the
[Uplift rules](https://wiki.mozilla.org/Release_Management/Uplift_rules).

This skill may run standalone (e.g. sec-moderate, non-security regressions) or
after `sec-approval` has already been filed. The sanitization audit for
sec-\* bugs runs exactly **once**, early in the flow, and all later steps
trust that result.

**Config.** This skill shares the Bugzilla API key config with the
`sec-approval` skill — no separate setup. Resolution order:

1. `$BMO_API_KEY` environment variable
2. `~/.config/bugzilla/config.toml` (`api_key = "..."`)
3. `~/.config/bmo-to-md/config.toml` (`api_key = "..."`)

Never read or print the key. Use
`python3 .claude/skills/uplift-request/bmo-uplift-request --check-auth`
to test availability.

**Arguments:** $0

Parse:

- The first all-digit token is the **bug ID**.
- Any token containing `/` is the **bug report path** (a folder of markdown
  written by `bmo-to-md`).
- `--beta`, `--release`, and `--esr NN` select target channels; multiple are
  allowed. If none are supplied, ask after Step 1.

All arguments are optional.

---

## Step 1 — Gather context

### Retrieve the bug

- **sec-\* or otherwise restricted**: `mcp__moz__get_bugzilla_bug` will fail.
  Use the same priority order as `sec-approval`:
  1. If the user supplied a bug-report path, read `summary.md` / `bug-<id>.md`
     from that folder.
  2. Otherwise run `bmo-to-md -o /tmp/bug-<id> -a <bug_id>` (requires a
     Bugzilla API key — check with the `--check-auth` command above).
  3. Otherwise ask the user.
- **public bugs**: prefer `mcp__moz__get_bugzilla_bug`.

Collect: component, keywords, severity, `sec-*` level (if any), existing
`status-firefoxNN` / `tracking-firefoxNN` flags, regressor bug if known, and
any prior uplift comments.

### Inspect local commits

```bash
# Detect VCS
jj --version 2>/dev/null && echo "jj" || echo "git"
```

**git:**

```bash
git log --oneline origin/main..HEAD
git log origin/main..HEAD --format=%B
git diff origin/main..HEAD
```

**jj:**

```bash
jj log -T builtin_log_detailed -r 'trunk()..@'
jj diff -r 'trunk()..@'
```

Record: commit messages, every `Differential Revision: .../D<N>` trailer, and
the full diff.

### Current release context

```
WebFetch: https://whattrainisitnow.com/calendar/
```

Extract current Nightly, Beta, Release, and live ESR versions. Also read the
local tree version if available: `cat config/milestone.txt`.

---

## Step 2 — Determine target channel(s)

If the user did not pass `--beta` / `--release` / `--esr NN`, ask with a
single `AskUserQuestion` (multiSelect) using concrete versions from the
calendar (e.g. "Beta 149", "ESR 140", "ESR 128"). Only offer ESR versions
that are currently supported.

One questionnaire may cover several channels; per-channel differences (risk,
backport patches) are called out inside the answer.

---

## Step 3 — Check whether patches are on the bug

Goal: know which of the four scenarios below we're in, so Step 4 can audit
exactly once.

1. **List attachments** (the script never prints the API key):

   ```bash
   python3 .claude/skills/uplift-request/bmo-uplift-request <bug_id> --list
   ```

   This prints each active Phabricator and raw-patch (`text/plain`)
   attachment with its ID, Phabricator revision (if any), summary, and
   current flags.

2. **Match** each local commit against the attachments:

   - **Strong — Phabricator**: `Differential Revision: .../D<N>` trailer
     matches an attachment whose summary or (decoded) data contains `D<N>`.
   - **Strong — raw patch**: fetch the `text/plain` attachment content and
     compare the first few `diff --git` hunk headers against the local diff.
     Matching file paths + identical hunk headers is a strong match;
     identical bodies is conclusive.
   - **Weak**: title/summary overlap only — treat as "possible", confirm with
     the user before trusting.

3. **Record the scenario** (sec-\* cases only — non-sec bugs skip Step 4):

   - **A.** No matching attachments. Local has the patches.
     → User hasn't submitted. Audit local commits.
   - **B.** Same as A, but the user only wants the form drafted (no
     submission). → Audit local commits.
   - **C.** Attachments match local. → Audit local commits (same content).
   - **D.** Attachments exist but diverge from local, or there are no local
     commits.
     → Audit what we can fetch: raw-patch attachment content and/or local
     commits if present. For Phabricator attachments with no local match we
     cannot pull the diff without Phab auth — flag that to the user and ask
     them to confirm the attached patches were sanitized.

Present the outcome as a short table before branching.

---

## Step 4 — Sanitization audit (sec-\* only, runs once)

Skip this entire step for non-sec bugs.

Run **Phase 1 — Compliance Audit** from the `sec-approval` skill
(commit messages, inline comments, identifiers, tests, Try server,
obfuscation). Do not duplicate the audit text here — follow the checks in
`.claude/skills/sec-approval/SKILL.md` Phase 1 and present the same
PASS/FAIL table.

**Inputs, per scenario from Step 3:**

| Scenario | What to audit                                                                        |
| -------- | ------------------------------------------------------------------------------------ |
| A, B     | Local commits (and diffs).                                                           |
| C        | Local commits (same content as the attachments).                                     |
| D        | Local commits if any; raw-patch attachment content; for Phabricator-only, ask user.  |

**Outcome:**

- **All PASS** → set an internal flag `sanitization_ok = true`. Steps 5 and 6
  proceed without re-auditing.
- **Any FAIL** → block. Present the specific violations with suggested fixes
  and ask the user to resolve them. After fixes, re-run this step. If
  attachments on the bug already contain unsanitized content (scenario C/D
  where the audit fails), remind the user they must update both local **and**
  re-submit the sanitized version (Step 5) before continuing.

No downstream step runs the audit again.

---

## Step 5 — Submit path (only if patches aren't on the bug, or need re-submission)

Triggers:

- Scenario A: user asks Claude to submit.
- Scenario D after a re-sanitization.

This is a user-visible, hard-to-reverse action — always confirm before
running any submit command.

- **Phabricator (preferred)**: show the exact `moz-phab submit` command,
  confirm, then run.
  ```bash
  moz-phab submit <base>..HEAD
  ```
- **Raw patch** (when Phabricator isn't appropriate): `git format-patch -1 HEAD`
  (or `jj` equivalent) and attach via the BMO API using the helper script.
  Ask the user to confirm the attachment summary.

After submission, re-list attachments to record the new IDs for Step 8.

Scenario B (user submits themselves later) — skip this step; just tell the
user which commands to run when they are ready.

---

## Step 6 — Draft the uplift questionnaire

The form, per
<https://wiki.mozilla.org/Release_Management/Uplift_rules#Guidelines_on_approval_comments_for_Beta_and_Release>,
has nine fields (same set for Beta, Release, ESR):

1. **User impact if declined** — user-facing consequence, not repro steps.
2. **Is this code covered by automated tests?** — Yes / No / Unknown.
3. **Has the fix been verified in Nightly?** — Yes / No (ask the user).
4. **Needs manual test from QE?** — Yes / No; if Yes, provide/reference repro.
5. **List of other uplifts needed** — dependent patches not on the target
   branch.
6. **Risk to taking this patch** — Low / Medium / High.
7. **Why is the change risky/not risky?** — concrete justification tied to
   diff size, scope, test coverage, behaviour changes.
8. **String changes made/needed** — "none" or describe. String changes need
   l10n driver approval.
9. **Is Android affected?** — Yes / No / Unknown based on whether touched code
   is shared with GeckoView.

Use the bug, the diff, and the `status-firefoxNN` flags to fill every field.
Keep answers tight and factual — one sentence where possible.

**For sec-\* bugs** (already sanitized by Step 4): keep the same caution in
the *text* of these answers. No "security" / "exploit" / "vulnerability", no
function names, no line numbers, no code snippets. Frame "user impact" and
"risk" as generic correctness/stability consequences.

**Per-channel differences**: if answers diverge across channels (different
backport, different risk), draft one block per channel:

```
### Uplift Request — Firefox {version} {Beta|Release|ESR NN}
```

If answers are identical, one block with an explicit
"Targets: Beta 149, ESR 140" header is acceptable.

---

## Step 7 — Write the markdown file

Write to the repository root as `uplift-request-bug-<bug_id>.md` (or
`uplift-request.md` if no bug ID). Use compact markdown — no blank lines
between bullets, one answer per line:

```text
### Uplift Request — Firefox <version> <channel>
* **User impact if declined**: <answer>
* **Is this code covered by automated tests?**: <Yes/No/Unknown>
* **Has the fix been verified in Nightly?**: <Yes/No>
* **Needs manual test from QE?**: <Yes/No — steps or reference>
* **List of other uplifts needed**: <answer or "None">
* **Risk to taking this patch**: <Low/Medium/High>
* **Why is the change risky/not risky?**: <answer>
* **String changes made/needed**: <none or description>
* **Is Android affected?**: <Yes/No/Unknown>

*Drafted with the assistance of Claude Code — reviewed and approved by the patch author.*
```

For multiple channels, concatenate one block per channel separated by a
single blank line. Use the `Write` tool, then tell the user the file path.

---

## Step 8 — Post to Bugzilla (optional)

Ask the user whether to post. Always dry-run first.

1. **Check API key** — never read or print it:

   ```bash
   python3 .claude/skills/uplift-request/bmo-uplift-request --check-auth
   ```

   On failure, offer the user the two options already documented in
   `sec-approval` (persistent in `~/.config/bugzilla/config.toml`, or
   one-time `$BMO_API_KEY`) and stop. The same config is used for both
   skills, so if `sec-approval` already works, this will too.

2. **Resolve attachment(s)**: uplift flags go on Phabricator attachments (one
   flag per target branch, often one attachment per backport patch). Use the
   `--list` output and the local commits' `D<N>` trailers to pick defaults.
   Ask the user to confirm. If none match (e.g. raw-patch-only), ask for the
   attachment ID.

3. **Dry-run** per channel:

   ```bash
   python3 .claude/skills/uplift-request/bmo-uplift-request \
       <bug_id> uplift-request-bug-<bug_id>.md \
       --attachment <id> --beta --dry-run
   ```

   Flags supported: `--beta`, `--release`, `--esr NN` (may be combined). Show
   the dry-run output and confirm.

4. **Post** — re-run without `--dry-run`. For multiple channels on different
   attachments, invoke the script once per attachment with the relevant
   flags.

5. Report the Bugzilla URL printed by the script.

---

## Tips

- Uplift flags:
  - `approval-mozilla-beta?`
  - `approval-mozilla-release?`
  - `approval-mozilla-esr{NN}?` (version-specific, e.g. `approval-mozilla-esr140?`)
- Beta cut-offs, ESR dot-releases, and merge-day dates come from
  <https://whattrainisitnow.com/calendar/> — don't guess.
- String changes need l10n driver approval separate from release drivers.
- ESR uplift is *additional* to sec-approval when both apply.
- If `bmo-to-md` isn't installed, point the user to `cargo install bmo-to-md`
  (<https://github.com/padenot/bmo-to-md>).
