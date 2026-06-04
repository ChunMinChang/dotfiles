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

## Running a WPT against another engine

When the chosen framework is WPT, the same `.html` / `.js` test can be run
against Chrome / Chromium / Safari / WebKit / Edge via `./mach wpt`'s
`--product` and `--binary` flags. This is the cheapest way to confirm a
cross-engine behavioural delta the report claims:

```bash
# Firefox (default)
./mach wpt testing/web-platform/tests/path/to/test.html

# Chrome / Chromium
./mach wpt --product chrome --binary /usr/bin/google-chrome \
  testing/web-platform/tests/path/to/test.html

# Chrome headless shell
./mach wpt --product headless_shell --binary /path/to/headless_shell \
  testing/web-platform/tests/path/to/test.html

# WebKit / Safari (see --webkit-port, --kill-safari)
./mach wpt --product webkit --binary /path/to/MiniBrowser \
  testing/web-platform/tests/path/to/test.html
```

Supported `--product` values include `chrome`, `chromium`, `headless_shell`,
`safari`, `webkit`, `edge`, `chrome_android`, `firefox`, `firefox_android`,
and several others — `./mach wpt --help | grep -- --product` shows the full
list on this machine.

Use this in Phase 3 when WPT is the framework and the hypothesis claims a
cross-engine delta: run the test against both Firefox (FAIL expected) and
Chrome (PASS / FAIL per the spec or the predicted Chrome behaviour). Capture
both logs to `<run_dir>/logs/test-h<N>-firefox.log` and
`<run_dir>/logs/test-h<N>-chrome.log` so the report can cite both outcomes.

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
