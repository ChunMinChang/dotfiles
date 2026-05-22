# Agent teams (Phase 2)

Blindspot Phase 2 spawns multiple research subagents in **one message containing
multiple `Agent` tool calls**. They run concurrently — that is the agent-teams
primitive. No harness flag exists or is needed.

Each team has a tight I/O contract. Subagents never declare the verdict; the main
agent synthesises after all teams return.

## Output persistence

**Every team writes its full findings to a dedicated file** under `<run_dir>/`
and returns only a short summary (≤10 lines) for synthesis. The main agent
reads the file when it needs the full results — never relies on the subagent
transcript. This makes the work survivable: if the session halts, the next
session resumes from the on-disk files.

| Team | Output file (under `<run_dir>/`) |
|---|---|
| Team C | `team-c-code-trace.md` |
| Team H | `team-h-hypotheses.md` |
| Team D | `team-d-design-archaeology.md` |
| Team X | `team-x-cross-browser.md` |
| Team T | `team-t-frameworks.md` |

Each prompt template below ends with an instruction to write to that file.

---

## Team C — Code trace

**Goal:** map the suspect code's neighbourhood. Every caller of the suspect symbol,
every consumer of its return, every gating check upstream.

**Prompt template:**
```
You are Team C in blindspot. Trace the suspect code without diagnosing.

Suspect symbol: <symbol>
Suspect file:   <path>
Searchfox rev:  <$BLINDSPOT_REV>

Tasks:
1. searchfox-cli --define '<symbol>' to find the definition; record permalink.
2. searchfox-cli --id '<symbol>' --cpp -l 150 to find callers and references.
3. For each caller, read the caller's body. Note what it does with the return
   value (assigns to what type? clamps? checks against limits?).
4. For each *consumer of the return value*, follow one more hop: where does that
   variable flow next?
5. Flag (but do not diagnose) "notable observations": narrowing conversions,
   missing nullchecks, early returns that swallow errors, comments documenting a
   workaround, dead branches.

Output:

1. **Write to disk:** `<run_dir>/team-c-code-trace.md`. The file is a
   numbered Markdown list of trace steps. Each entry:
     N. [`Class::Method`](https://searchfox.org/firefox-main/rev/<sha>/<path>#L<n>) — one-line description
        - evidence sub-bullet (quote the relevant 1–2 lines)
   End the file with a "Notable observations" block of bullet points.

2. **Return** a short summary (≤10 lines): how many trace steps you produced,
   the 2–3 most striking observations, and any blockers. The main agent will
   `Read` the file for the full content.

Do NOT declare the root cause. Do NOT propose fixes.
```

**Hard rules:** revision-pinned URLs only. Never invent line numbers. Never claim
something is "the" root cause.

---

## Team H — Hypothesis brainstorm

**Goal:** generate **≥5** concrete failure scenarios and rank them by
confirm-value ÷ probe-cost.

**Prompt template:**
```
You are Team H in blindspot. The user submitted this claim:

<claim verbatim>

Suspect symbol: <symbol>
Searchfox rev:  <$BLINDSPOT_REV>

Generate AT LEAST 5 concrete failure scenarios. For each:
- Precondition (what input/state triggers it)
- Mechanism (how the bug manifests internally)
- Predicted user-visible signal (decode error? wrong size returned? crash?
  silent miscompute? cross-browser delta?)
- Probe cost (read-only / build + gtest / build + mochitest / requires sanitizer
  build / requires fault injection)

Then rank them: highest confirm_value / probe_cost first.

Output:

1. **Write to disk:** `<run_dir>/team-h-hypotheses.md`. The file contains
   a Markdown table with columns
     | # | Hypothesis | Mechanism | Predicted signal | Probe cost | Rank |
   followed by one paragraph per hypothesis expanding on the precondition.

2. **Return** a short summary (≤10 lines): hypothesis count, top-3 by rank
   with their one-line mechanism, and any class of failure you considered
   and dropped (with reason).

Do NOT pick the verdict. Do NOT propose fixes.
```

---

## Team D — Design archaeology

**Goal:** recover the original design intention and the contract the author
believed they were establishing.

**Prompt template:**
```
You are Team D in blindspot. Find the design intention behind:

Suspect symbol: <symbol>
Suspect file:   <path>
Searchfox rev:  <$BLINDSPOT_REV>

Tasks:
1. git log -S '<symbol>' --follow -- <path>  (find introducing commit)
2. git blame -L <line>,<line>+20 -- <path>   (find recent touchers)
3. For each interesting commit, read the message and follow Bugzilla links.
4. Read 2–3 commits before and after for context.
5. Summarise the original purpose, design rationale, and any documented
   constraint or tradeoff.

Output:

1. **Write to disk:** `<run_dir>/team-d-design-archaeology.md`. The file
   covers:
     - Introducing commit (hash + bugzilla link)
     - Original purpose (1 sentence)
     - Design rationale (cite commit message / bug discussion)
     - Constraints/tradeoffs
     - Function contract (preconditions, postconditions, invariants,
       threading model, ownership)
     - Drift signals (followup commits patching the same area, comments
       documenting workarounds, dead branches)

2. **Return** a short summary (≤10 lines): introducing-commit hash + bug,
   one-sentence original purpose, the single most important constraint,
   and any drift signal worth flagging.

Do NOT claim how the current claim relates to the design. That is the main
agent's job.
```

---

## Team X — Cross-browser & spec check

**Goal:** establish what other engines do and what the spec says.

**Prompt template:**
```
You are Team X in blindspot. Compare cross-engine behaviour and check the spec.

Claim: <claim verbatim>
Suspect symbol: <symbol>
Searchfox rev:  <$BLINDSPOT_REV>

Tasks:
1. Identify the relevant spec section if any. If the claim is about a web-
   exposed feature, invoke Skill(webspec-index, ...) to find the algorithm.
2. grep testing/web-platform/tests/ for existing coverage of the same surface.
3. If a live observation is cheap and useful, invoke Skill(playwright, ...)
   to observe Chrome and Firefox behaviour side by side. Capture screenshots
   or console output into <run_dir>/logs/team-x-*.{log,png}.
4. Read Chrome's source if a public link is known (Chromium source.chromium
   .org); otherwise rely on spec wording.

Output:

1. **Write to disk:** `<run_dir>/team-x-cross-browser.md`. The file contains:
     - Spec citation (URL + section, or "no spec — internal").
     - Behaviour table:
         | Engine | Behaviour | Source |
     - Existing WPT coverage (paths) or "none".
     - Notable spec/impl divergence (if any).

2. **Return** a short summary (≤10 lines): one-sentence spec status, the
   cross-engine behaviour delta in one line, and existing WPT coverage
   count.

Do NOT pick the verdict.
```

---

## Team T — Test framework scout

**Goal:** for each hypothesis from Team H, pick the right framework and find a
neighbour test that already exercises the suspect code path.

**Prompt template:**
```
You are Team T in blindspot. Pick the right test framework for each hypothesis.

Hypotheses (from Team H):
<paste Team H output>

Suspect file: <path>
Searchfox rev: <$BLINDSPOT_REV>

Reference: blindspot/references/test-frameworks.md (delegates to
sherlock/references/test-frameworks.md for the decision tree).

For each hypothesis, choose ONE framework from:
  gtest | mochitest-plain | mochitest-chrome | browser-chrome | xpcshell
  | reftest | crashtest | wpt

For each pick, find a representative neighbour test in the tree that already
exercises the suspect code path (same dir or sibling dir). The new test
should be written in that file's style.

Output:

1. **Write to disk:** `<run_dir>/team-t-frameworks.md`. The file is a
   Markdown table with columns
     | # | Hypothesis | Framework | Neighbour test path | Reason |

2. **Return** a short summary (≤10 lines): framework distribution across
   hypotheses (e.g. "3 gtest, 1 wpt, 1 crashtest") and any hypothesis where
   you weren't confident about the framework choice.

Do NOT write the tests. Do NOT pick the verdict.
```

---

## When to skip a team

| Team | Skip when | Skip note in report |
|---|---|---|
| C | Never — always run. | n/a |
| H | Never — always run. | n/a |
| D | Suspect symbol is brand new (no history beyond the introducing commit). | Note "introducing commit only; no further history" in Design Intention. |
| X | Suspect code has no web surface (internal helper, codec parser with no JS bridge, IPC plumbing). | Note "no web surface; cross-browser comparison N/A" in report. |
| T | Phase 1 outcome was Nonsense or Ambiguous-without-resolution. | n/a (skipped phases). |

---

## Anti-patterns

- **Do not** give the same prompt to two teams hoping one returns better
  results. Pick the right team and trust the contract.
- **Do not** let any team propose a fix. Teams that step outside their
  contract should be re-prompted, not promoted.
- **Do not** sequentialise teams. They run in parallel. If one team needs the
  output of another, that's a sign of bad partitioning — restructure.
