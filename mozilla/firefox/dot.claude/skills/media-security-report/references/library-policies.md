# Library policies

One row per vendored media library. This file carries **policy** only — which
channel, which extras, which traps. Paths, vendored revisions and Bugzilla
components are read from the checkout at run time by
`scripts/media_lib_facts.py`, because a hardcoded copy of those goes stale
(sherlock's `references/upstream-libs.md` still points at `netwerk/srtp`, which
no longer exists).

Adding a library means adding a row here **and** in
`scripts/channel_policy.py`; a test asserts the two agree.

## Routing table

| Library | Tree path(s) | Channel(s) | Revision source | Notes |
| --- | --- | --- | --- | --- |
| `ffvpx` | `media/ffvpx` | email-plain | `README_MOZILLA` | Trimmed FFmpeg subset; confirm the code is actually vendored before escalating |
| `libvpx` | `media/libvpx` | buganizer | moz.yaml | Security template `2023994`, not the `2023833` in the README |
| `libwebp` | `media/libwebp` | buganizer | moz.yaml | `tracking: tag` but pins a hash; `origin.url` and `vendoring.url` differ |
| `libaom` | `media/libaom`, `third_party/aom` | buganizer | moz.yaml | AOMedia tracker |
| `libyuv` | `media/libyuv` | buganizer | moz.yaml | No bug-reporting docs at all; set `Type = Vulnerability` by hand |
| `libwebrtc` | `third_party/libwebrtc`, `media/webrtc` | buganizer | `README.mozilla.last-vendor` | Short hash, not 40-hex; Bughunters vs tracker is unresolved |
| `dav1d` | `media/libdav1d`, `third_party/dav1d` | gitlab-confidential, email-plain | moz.yaml | Do both: confidential item for maintainers, `security@videolan.org` for the org record |
| `libvorbis` | `media/libvorbis` | gitlab-confidential | moz.yaml | No security address exists; fallback `monty@xiph.org` |
| `libogg` | `media/libogg` | gitlab-confidential | moz.yaml | Fallbacks `monty@`, `giles@`, `tterribe@xiph.org` |
| `libopus` | `media/libopus` | gitlab-confidential | moz.yaml | Never the public `opus@xiph.org` list; maintainer `jmvalin@jmvalin.ca` |
| `speexdsp` | `media/libspeex_resampler` | gitlab-confidential | moz.yaml | Its `CONTRIBUTING.md` is the only place Xiph documents the confidential route |
| `libpng` | `media/libpng` | github-pvr | moz.yaml | README misdirects to a publicly archived SourceForge list |
| `libjpeg-turbo` | `media/libjpeg` | email-gpg | moz.yaml | Has a scope gate; only project here with a published key |
| `libsoundtouch` | `media/libsoundtouch` | bugzilla-restricted | moz.yaml | No private channel upstream; CC `oparviai@iki.fi` |
| `libsrtp` | `third_party/libsrtp` | email-plain | moz.yaml | Cisco PSIRT only as a separate second notice |
| `nestegg` | `media/libnestegg` | bugzilla-restricted, github-pvr | moz.yaml | Mozilla-owned |
| `cubeb` | `media/libcubeb` | bugzilla-restricted, github-pvr | moz.yaml | Mozilla-owned |
| `mp4parse-rust` | `media/mp4parse-rust` | bugzilla-restricted, github-pvr | in-tree crate | Mozilla-owned; crate vendored under `third_party/rust` |
| `nicer` | `dom/media/webrtc/transport/third_party/nICEr` | bugzilla-restricted | moz.yaml | Upstream near-dormant; Mozilla carries the fixes |
| `widevine-adapter` | `dom/media/gmp/widevine-adapter` | buganizer | moz.yaml | The CDM interface headers are Chromium's |
| `libmkv` | `media/libmkv` | bugzilla-restricted | moz.yaml `release:` | **No upstream** — abandoned and deleted from libvpx; six local patches |
| `openmax_il` | `media/openmax_il` | bugzilla-restricted | none | **No upstream** — frozen Khronos IL 1.1.2 spec headers |
| `mozva` | `media/mozva` | bugzilla-restricted | none | **No upstream** — `mozva.c` is a Mozilla shim; only `va/*.h` are copied libva headers |
| `psshparser` | `media/psshparser` | bugzilla-restricted | none | **No upstream** — Mozilla-authored |
| `gmp-clearkey` | `media/gmp-clearkey` | bugzilla-restricted | none | **No upstream** — Mozilla-authored reference Clear Key CDM |
| `wmf-clearkey` | `media/wmf-clearkey` | bugzilla-restricted | none | **No upstream** — Mozilla-authored |

A media path with no row here **fails closed** to `bugzilla-restricted` with no
external CC, and the skill says the table needs a row. Guessing an upstream
security address is the one mistake that leaks a live vulnerability.

## Per-library extras beyond the core

### ffvpx — FFmpeg's ten

FFmpeg is the only library whose published list goes beyond
[report-core.md](report-core.md). Both additions are required:

- **An input-generation script**, if one exists — "A script generating the
  input, if available." If none can be recovered, say so explicitly.
- **An attached input file** — FFmpeg asks for "an `ffmpeg` command line
  together with an attached multimedia input file", not a description of one.

FFmpeg's full ten map onto core items 1–10 exactly; the page's opening
insistence on "careful human verification" is core item 11.

### libjpeg-turbo — the scope gate

State explicitly, before anything else, that the finding clears the project's
definition: a well-behaved caller, malformed image data, a public API function,
a supported (non-EOL) release. State whether and where AI was used — this
project asks for it by name.

### libsoundtouch — CC access verification

The report must record the post-filing check that the CC actually granted
access: `is_cc_accessible` true on the bug. If that bit is cleared the CC'd
maintainer silently loses access *and receives no mail*, so a report that skips
the check can sit unread indefinitely.

### Libraries with no upstream

Reproduction is a Firefox gtest, crashtest or mochitest rather than an upstream
harness, and the code is cited with revision-pinned
`searchfox.org/mozilla-central/rev/<hash>/` links. There is no upstream patch to
propose — the fix lands in mozilla-central.

## Build and test hints

For reproducing in the upstream tree. Confirm against the project's own docs;
these change.

| Library | Build | Tests |
| --- | --- | --- |
| ffvpx / FFmpeg | `./configure && make` | FATE: `make fate` |
| libvpx | `./configure && make` | `make test` (googletest) |
| libaom | `cmake -B build && cmake --build build` | `ctest --test-dir build` |
| dav1d | `meson setup build && ninja -C build` | `ninja -C build test` |
| libopus | `cmake -B build && cmake --build build` | `ctest --test-dir build` |
| libvorbis / libogg | `./autogen.sh && ./configure && make` | `make check` |
| speexdsp | `./autogen.sh && ./configure && make` | `make check` |
| libpng | `cmake -B build && cmake --build build` | `ctest --test-dir build` |
| libjpeg-turbo | `cmake -B build && cmake --build build` | `ctest --test-dir build` |
| libsoundtouch | `./bootstrap && ./configure && make` | `make check` |
| libsrtp | `cmake -B build && cmake --build build` | `ctest --test-dir build` |
| libwebrtc | `gn gen out/Default && ninja -C out/Default` | googletest binaries |
| libyuv / libwebp | `cmake -B build && cmake --build build` | `ctest --test-dir build` |
| no-upstream components | Firefox build | `./mach gtest`, `./mach test` |

## Known unknowns

Record these in the report rather than resolving them by assumption:

- Whether GitHub's private report form accepts file uploads.
- Whether the WebM and AOMedia trackers honour Chromium's 14-weeks-after-Fixed
  disclosure clock, which is documented for Chromium only.
- Whether libyuv's tracker offers a Security report template at all.
- For libwebrtc, whether Google Bughunters or the Chromium tracker is the
  intended intake today — the two docs disagree.
- Whether WebM's generic security component `1615215` or the per-library
  components are the intended destination.
