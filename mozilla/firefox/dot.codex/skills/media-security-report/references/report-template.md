# Report template

The shape a finished report takes. Derived from a real accepted FFmpeg report
(`vp9-frame-thread-flush-oob.md`), generalized to any vendored library. Section
names are worth keeping — a maintainer scanning for "where is the fix" or "does
it still reproduce on master" should find it in the same place every time.

Content rules live in [report-core.md](report-core.md); this is the skeleton.

---

````markdown
# <Library> <component>: <vulnerability class> <under what conditions>

## Attribution and Identifiers

- **Human reviewer**: <name> (`<email>`) — built, ran and re-read every result
  quoted here by hand.
- **Finder credit**: Found by <finder>; reduced, analysed and verified by hand
  by <reviewer>.
- **AI usage**: <what AI assisted with — analysis, tests, drafting>. Every
  claim, source line, stack trace and reproduction step in it was verified by
  hand by <name> on the revisions named below; nothing here is reported on the
  strength of an AI-generated result alone.
- **CVE / related identifier**: <id, or "None assigned at report time">.
  <If tracked downstream: say so, and that no detail from it is needed to
  reproduce or fix the issue.>

## Summary

- **Library**: <library> — <component>
- **Version/Revision**: still present on <upstream> master `<hash>` (tip as of
  <date>), reproduced end-to-end on <platform> / <compiler>. Originally
  validated on `<vendored hash>`.
- **Reported**: <YYYY-MM-DD>
- **First affected commit**: [`<hash>`](<pinned commit url>), `<commit subject>`
  (<date>) — <what it introduced that created the defect>.

<One or two paragraphs: the conditions, then the distinct manifestations as a
numbered list, each with its access size and the function that performs it.>

1. **<Manifestation A>** (<n> bytes) — `<function>()` <what it does wrong>.
2. **<Manifestation B>** — <...>

<Then the shared root cause in one paragraph: what is not released / not
validated / not reset, and how that reaches the access above.>

## Code Path Trace

<Preamble: what the numbered sequence follows. "Every source link is pinned to
revision `<hash>`.">

1. [`entry_point`](<pinned url>) → [`callee`](<pinned url>) — <what happens
   here, and which state it establishes>, with a line-range link
   ([L851-L854](<pinned url with range>)) for the exact statement.
2. …

### <READ path> (<access class>)

<n>. …

### <WRITE path> (<access class>)

<n>. …

## Crash Stacks

<Label every stack with the failure type, exact revision, build configuration,
platform, and thread role. Copy the complete symbolized stack exactly as emitted.
Preserve every consecutive frame from the first (`#0` or `#1`) through the final
`#N`; never omit middle frames, renumber an excerpt, or use an ellipsis. Put
faulting-thread and thread-creation stacks in separate subsections.>

### <failure / build / thread>

```text
#0 <first frame exactly as emitted>
#1 <next frame exactly as emitted>
#2 <continue with every consecutive frame through the final frame>
```

## Test Cases

<How many targets from how many source files. Whether inputs are embedded or
external.>

<If no CLI reproduction exists, say so explicitly and why: "The trigger is an
API sequence the CLI never performs — <sequence>. The packets that drive it are
embedded as base64 inside the test sources, so each attached test patch is a
complete, self-contained reproducer.">

<Patch ordering: "apply 01, 02, 03 in that order, then the fix patch 04 on top.
Each patch is a single self-contained commit that creates its test and its
registration together.">

## Input Generation

<Either the generator script and its invocation, or an explicit statement of
why none is available: what was captured, what cannot be recovered, and what is
generated at runtime instead. Never a guessed generator.>

### 1. `<test-name>` — <what it detects>

<Per-test detail: the oracle it uses, the packet sequence, what it asserts, and
what it prints on failure.>

## How to Reproduce

### 1. Get the source and apply the test patches

```bash
git clone <repo url> && cd <dir>
# Pin to the exact revision this report was verified against:
#   git checkout <hash>
git am 01-test-<desc>.patch
```

### 2. Configure a build folder

```bash
<build commands — both a sanitized and a plain configuration where both matter>
```

### 3. Run the tests

```bash
<test commands, with the expected unfixed result beside each>
```

### 4. Apply the fix and verify

```bash
git am 0N-fix-<desc>.patch
<rebuild + rerun, with the expected fixed result beside each>
```

## Suggested Fix

<One paragraph: what the change does and why it closes every manifestation.>

```c
     <context line>
+    <the added line>
     <context line>
```

**Patch**: See `0N-fix-<desc>.patch`.

**Fix matrix**, re-measured on `<hash>` (<platform>, <compiler>), <n> runs of
each target in each build folder:

| Build folder | Fix | Runs | Behaviour | Result |
| --- | --- | --- | --- | --- |
| `build-asan` | no | <n> | <what happens> | <n>/<n> detected — 0% clean |
| `build-asan` | yes | <n> | **rejected** | <n>/<n> clean |
| `build-plain` | no | <n> | <what happens> | <n>/<n> detected |
| `build-plain` | yes | <n> | **rejected** | <n>/<n> clean |

<Note any additional hardening you considered but did not include, and why the
proposed fix is sufficient on its own.>

## Supersedes

<Only when replacing an earlier report: what it merges and why.>
````

---

## Why these sections

- **Attribution first.** Two projects now reject bot-submitted reports outright,
  so the human and the AI-usage statement belong above the fold, not in a
  footer.
- **"Still present on master `<hash>`"** in the Summary answers the maintainer's
  first question before they ask it. Give the tip hash *and* the vendored hash;
  they are different claims.
- **Line-range links inside the trace.** A link to the function is not enough
  when the argument turns on three specific lines — pin the range.
- **A fix matrix with run counts**, not "works for me". Scheduling-dependent
  bugs need the round count on the page; one clean run proves nothing.
- **Input Generation as its own section**, even when the answer is "none". A
  reader who cannot regenerate the input needs to know that is expected rather
  than missing.
- **Per-test subsections.** When a report ships four oracles, the maintainer
  needs to know which one detects what — especially which works without a
  sanitizer.
