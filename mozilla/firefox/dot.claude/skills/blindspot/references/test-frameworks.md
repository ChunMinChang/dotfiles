# Test framework selection (blindspot)

Blindspot reuses sherlock's decision tree. Read
[`../../sherlock/references/test-frameworks.md`](../../sherlock/references/test-frameworks.md)
for the full decision tree, framework table, proof-test rules, and
FuzzingFunctions mapping.

## Blindspot-specific overrides

The sherlock document targets known-failing bugs with a reproducer in the bug
attachments. Blindspot starts from a hypothesis. Two practical implications:

1. **No bug attachments to mine.** Team T must derive the testcase shape from
   the suspect code's neighbour tests, not from an attached `test.html`. The
   neighbour-test path returned by Team T is the seed.

2. **Test must drive *real* inputs.** A blindspot proof test cannot
   monkey-patch a private to force a value. The test produces an
   actually-malformed (but parseable) input that drives the suspect code path
   on its own. Fault injection has its own escape hatch — see
   [`injection-patterns.md`](./injection-patterns.md).

## Quick framework picker by hypothesis class

| Hypothesis class | Framework | Why |
|---|---|---|
| Internal parser/decoder produces wrong value | **gtest** | Reach the function directly with controlled bytes; no browser needed. |
| Browser API returns wrong value to JS | **mochitest-plain** | Drive via JS, observe via JS. |
| API behaviour differs from spec | **wpt** | Cross-engine, ships upstream. Run `spec-check` first. |
| Crash on malformed media/HTML/etc. | **crashtest** | The crash itself is the assertion. |
| Privileged behaviour (about: pages, prefs) | **browser-chrome** | Needs privileged JS context. |
| Standalone JS API w/o DOM | **xpcshell** | Faster than mochitest for JS-only checks. |
| Race / timing | reconsider | See sherlock doc — usually skip the test and document. |

## Reaching the blindspot "end-to-end" bar

A test is end-to-end when **every step from the user-controllable input to the
observable consequence runs in real code** with no production-source patches.

- **Bad (simulated):** unit test that calls the suspect function directly with
  hand-built internal state, asserting it returns the bad value.
- **Good (e2e gtest):** unit test that feeds a real serialized SPS byte stream
  through the public parser entry point and observes the post-parse `ImageSize`.
- **Good (e2e mochitest):** create a `<video>` with a constructed media source,
  let the decoder pipeline pull frames, observe `videoWidth`/`videoHeight`.

If you cannot reach end-to-end without violating that rule, the proof is a
fault-injection proof (see [`injection-patterns.md`](./injection-patterns.md))
or the hypothesis is `lucky-prevented`.
