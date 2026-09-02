---
name: source-permalinks
description: >
  Reference for constructing revision-pinned source, spec, and bug permalinks
  (Searchfox, GitHub, GitLab, googlesource, Codeberg, Chromium, FFmpeg,
  Bugzilla, specs) for Firefox/Codex analysis and reports. Use when citing
  code, specs, or bugs and you need stable, revision-pinned URLs instead of
  trunk/HEAD links.
metadata:
  short-description: Revision-pinned source/spec/bug permalinks
---

# Source Permalink Reference

## Golden Rule

Always use revision-pinned URLs in analysis documents. Never use trunk/tip/HEAD URLs.

## When to Link

- Source files and functions (Firefox, Chromium, any open-source project)
- Specification sections (WHATWG, W3C, TC39, IETF, etc.)
- Bug reports (Bugzilla, GitHub Issues, Chromium Issue Tracker)
- Documentation pages
- Any other web-accessible resource

## Anchor Text Rules

- Use function name, identifier, or short description as anchor text — not raw URL
- If citing a line range, use the starting line
- If no specific line known, link to file root
- Apply in all contexts: prose, tables, code snippets, plans

## Searchfox (Firefox, WebKit)

### URL Format

```
https://searchfox.org/{repo}/rev/{hash}/{path}#{line}
https://searchfox.org/{repo}/rev/{hash}/{path}#{start}-{end}
```

### Repository Table

| Repo ID | Description |
|---------|-------------|
| firefox-main | Firefox trunk (primary) |
| firefox-beta / mozilla-beta | Beta branch |
| firefox-release / mozilla-release | Release branch |
| firefox-esr115 | ESR 115 |
| firefox-esr128 | ESR 128 |
| firefox-esr140 | ESR 140 |
| wubkat | WebKit |

### Revision Resolution Strategy

1. Get the local revision, then **walk past any local-only commit**. Checkouts that
   have an agent overlay installed carry an `Install <X> overlay` commit at the tip
   which adds only `.claude/` / `.codex/` and `.gitignore` and is never pushed
   upstream. Pinning to it makes *every* link dead. Because it touches no source
   file, the tree is byte-identical at its parent, so line anchors are unaffected:
   ```bash
   REV=$(git rev-parse HEAD)
   while git log -1 --format=%s "$REV" | grep -q '^Install .* overlay$'; do
     REV=$(git rev-parse "$REV^")
   done
   ```
2. Validate on searchfox using the current web open/fetch mechanism, **never
   `curl`**:
   fetch `https://searchfox.org/firefox-main/rev/{hash}/moz.configure`
   - Renders source: use this hash for all links in the session
   - **HTTP 500**: searchfox does not know this revision — it is either local-only or
     not yet indexed. Fetch `https://searchfox.org/firefox-main/source/moz.configure`
     and extract the indexed revision from the page content.
3. Cache the validated revision for the entire session ($SHERLOCK_REV)
4. For ESR/beta branches: repeat with the appropriate repo ID

> ### Never validate a permalink by HTTP status
>
> A bare GET of **any** searchfox URL returns **200** carrying an anti-bot "Client
> Challenge" page, and searchfox returns **500** for a revision it does not know. So
> `curl -o /dev/null -w '%{http_code}'` reports 200 for a good revision and a dead
> one alike — it cannot tell them apart, and neither can any audit built on it.
>
> This is not hypothetical. It let a nine-iteration RCA (bug 2054288) certify an
> analysis pinned to a local-only overlay commit, in which every code link rendered
> "Bad Revision", past five link-audit lanes and three citation-review passes. Two of
> those lanes reached *opposite* verdicts on the same three URLs and were never
> reconciled, so the bad citations survived as well.

### Verifying permalinks

Resolve source citations against a local clone, not over HTTP. `git show <rev>:<path>`
plus a line-range bound check validates the revision, the path **and** the line anchor
in one step:

```bash
.codex/skills/source-permalinks/verify-permalinks \
  --repo <local-clone> [--repo <another-clone> ...] \
  [--expect-rev "$REV"] [--strict-rev] doc.md teams/*.md
```

`--expect-rev` refuses an overlay pin and reports citations on another revision as
**advisories**, because history and archaeology docs legitimately pin to the commit
they discuss — flagging those as errors is how a checker teaches its readers to
ignore it. Add `--strict-rev` for a document that should be entirely on-pin, such as
the analysis doc itself.

It covers searchfox, googlesource, GitHub, GitLab and Codeberg citations; falls back to
HTTP only for non-source hosts (bugzilla, phabricator, spec sites), which do not
bot-challenge; flags a Git SHA placed on a Mercurial host; and refuses an
`Install <X> overlay` pin outright.

A rate-limited or unreachable non-source host (HTTP 429, 5xx, DNS failure) is
retried and then reported as `UNVERIFIED`, never as a defect — it says nothing about
whether the link is good, and counting it as broken teaches readers to discount real
findings. Re-run those rather than editing the citation.

**It checks transport and anchors, not meaning.** A link that resolves to the *wrong*
lines is still a defect, so follow the mechanical pass with a manual read confirming
the cited lines support the citing sentence. Never report a citation audit as passing
on transport alone.

### Mercurial Hash Compatibility

```
https://searchfox.org/{repo}/hgrev/{hg-hash}/{path}#{line}
```

Automatically converts Mercurial hashes to Git revisions.

## GitHub

```
https://github.com/{owner}/{repo}/blob/{hash}/{path}#L{line}
https://github.com/{owner}/{repo}/blob/{hash}/{path}#L{start}-L{end}
```

## GitLab

```
https://{host}/{owner}/{repo}/-/blob/{hash}/{path}#L{line}
```

Known hosts: gitlab.xiph.org, code.videolan.org

## googlesource.com

```
https://{host}/{repo}/+/{hash}/{path}#{line}
```

Known hosts: chromium.googlesource.com, aomedia.googlesource.com, webrtc.googlesource.com

## Codeberg

```
https://codeberg.org/{owner}/{repo}/src/commit/{hash}/{path}#L{line}
```

## Chromium Code Search

```
https://source.chromium.org/chromium/chromium/src/+/main:{path};l={line}
```

Note: source.chromium.org does NOT support revision pinning in URLs.
For pinned Chromium links, use the googlesource.com mirror:

```
https://chromium.googlesource.com/chromium/src/+/{hash}/{path}#{line}
```

## FFmpeg (via GitHub mirror)

```
https://github.com/FFmpeg/FFmpeg/blob/{hash}/{path}#L{line}
```

The Firefox moz.yaml revision maps to a git commit on this mirror.

## Bugzilla

```
https://bugzilla.mozilla.org/show_bug.cgi?id={id}
```

Anchor text: `[Bug {id}](URL)`

## Specifications

Trusted spec domains:

- html.spec.whatwg.org — WHATWG HTML Standard
- w3c.github.io — W3C specs (WebCodecs, MSE, EME, etc.)
- webaudio.github.io — Web Audio API
- tc39.es — ECMAScript
- datatracker.ietf.org — IETF RFCs
- `www.rfc-editor.org` — RFC editor
- itu.int — ITU-T codec specs (H.264, H.265)

Format: `[Section Name](full URL with anchor)`

## Examples

**Searchfox (revision-pinned):**
[`MediaDecoder::Shutdown`](https://searchfox.org/firefox-main/rev/8fe6930c0832009b3162bebee7d4ede1a4c8c9a8/dom/media/MediaDecoder.cpp#456)

**Searchfox (WebKit):**
[`MediaPlayer::pause`](https://searchfox.org/wubkat/rev/abc123def456/Source/WebCore/platform/graphics/MediaPlayer.cpp#120)

**GitHub:**
[`nestegg_read_packet`](https://github.com/mozilla/nestegg/blob/abc123def456/src/nestegg.c#L1234)

**GitLab:**
[`dav1d_decode`](https://code.videolan.org/videolan/dav1d/-/blob/abc123def456/src/decode.c#L567)

**googlesource.com:**
[`vpx_codec_decode`](https://chromium.googlesource.com/webm/libvpx/+/abc123def456/vpx/vpx_decoder.c#89)

**Chromium (pinned via googlesource):**
[`MediaFoundationCdm::OnHardwareContextReset`](https://chromium.googlesource.com/chromium/src/+/abc123def456/media/cdm/win/media_foundation_cdm.cc#680)

**Codeberg:**
[`SoundTouch::processRemainingFrames`](https://codeberg.org/soundtouch/soundtouch/src/commit/abc123def456/source/SoundTouch/SoundTouch.cpp#L345)

**FFmpeg:**
[`avcodec_send_packet`](https://github.com/FFmpeg/FFmpeg/blob/abc123def456/libavcodec/decode.c#L567)

**Spec:**
[HTML Standard §8.5 — The `media` element](https://html.spec.whatwg.org/multipage/media.html#media-element)

**Bug:**
[Bug 1234567](https://bugzilla.mozilla.org/show_bug.cgi?id=1234567)
