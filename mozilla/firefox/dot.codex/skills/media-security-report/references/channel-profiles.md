# Channel profiles

Six ways to reach a maintainer privately. The report body is the same for all
of them ([report-core.md](report-core.md)); this file governs how it is
delivered, what metadata to add or leave out, and which mechanics are
irreversible if you get them wrong.

`scripts/channel_policy.py` holds the machine-checkable half of this file. If
you change a profile here, change it there too — a test asserts they match.

Two rules cut across every profile:

- **The skill never sends, files, or submits anything.** It writes the report
  and a submission draft. A human does the rest.
- **Never open a prefilled tracker URL in a way that creates the item.** Prefill
  links appear below so the *user* can use them.

## email-plain — FFmpeg, libsrtp

| Field | Value |
| --- | --- |
| Intake | `ffmpeg-security@ffmpeg.org`; `libsrtp-security@lists.packetizer.com` |
| Privacy | Closed recipient list. Non-subscribers may post to both. |
| One-shot risk | No |
| Crash input | **Attach.** FFmpeg requires "an `ffmpeg` command line together with an attached multimedia input file". |
| Encryption | **None.** Neither publishes a key; FFmpeg's 2016 proposal to publish one never landed. The input travels in cleartext. |
| Access preservation | Keep your sent copy — there is no thread to read back. |
| Verification | None available. |
| CVE | Nobody assigns one. Say "none assigned at report time". |
| Disclosure clock | Undocumented. FFmpeg publishes no acknowledgement SLA; set your own timeline and state it. |
| Known unknowns | Whether anyone will reply at all. Plan for silence. |

FFmpeg additionally rejects ordinary bugs, non-exploitable undefined behavior,
and leaks at this address — those go to a pull request instead.

## email-gpg — libjpeg-turbo

| Field | Value |
| --- | --- |
| Intake | `information@libjpeg-turbo.org` (the website obfuscates it with ROT13; this is the decoded address) |
| Privacy | End-to-end GPG to `D291 2829 1D60 993B 8CC8 5724 8475 77AB B633 DB01` |
| One-shot risk | No |
| Crash input | Attach **inside the encrypted payload**. |
| Encryption | **Yes** — the only third-party library here with a published receiving key. Verify the fingerprint out of band. |
| Access preservation | Encrypt to yourself as well, or you cannot read your own sent mail. |
| Verification | None available. |
| CVE | Not stated. |
| Disclosure clock | Undocumented; a supported-version matrix is published instead. |
| Known unknowns | None. |

This is the only project with a **scope gate**, and it is enforced socially: an
issue counts as a vulnerability only when "an otherwise well-behaved calling
program can trigger a potentially exploitable failure … by passing malformed
image data to a public API function", in a supported (non-EOL) release. Caller
misuse — a reproducer that under-allocates its output buffer, say — is an
API-hardening bug and must go to a public GitHub issue. Reports that break the
rules "will be treated as spam".

## buganizer — libvpx, libwebp, libaom, libyuv, libwebrtc, widevine-adapter

| Field | Value |
| --- | --- |
| Intake | libvpx: webmproject tracker component `1618984`, template `2023994`. libwebp: `1618983` / `2024050`. libaom: aomedia tracker `1597128` / `2015013`. libyuv: `libyuv.issues.chromium.org`, no security template. libwebrtc: Google Bughunters (Chrome VRP). |
| Privacy | Choosing the Security report template sets `Type = Vulnerability`, which flips `Access` to **Limited Visibility** and adds `security@chromium.org` as collaborator. On a tracker with no security template, set `Type = Vulnerability` by hand — that is what actually restricts it. |
| One-shot risk | No — Type can be set after creation. |
| Crash input | Attach directly. Chromium asks for files "not in zip or other archive formats". |
| Encryption | Transport only. |
| Access preservation | **CC yourself before submitting.** Limited Visibility restricts the issue to explicitly listed identities, so a reporter who is not CC'd can lose access to their own report. |
| Verification | Reopen the issue URL while signed in and confirm you can still read it. |
| CVE | Chrome's CNA assigns. Do **not** also request one from MITRE. |
| Disclosure clock | Chromium opens bugs 14 weeks after they are marked Fixed. |
| Known unknowns | Whether the WebM and AOMedia instances honour that 14-week clock — it is documented for Chromium only. Whether libyuv's tracker offers a Security template at all. For libwebrtc, Chromium's FAQ deprecates direct tracker intake in favour of Bughunters while WebRTC's own docs still instruct the tracker; the two disagree. |

Any Google account works — there is no per-tracker registration. The template
IDs printed in the libvpx and libwebp READMEs (`2023833`, `2023995`) are the
*bug* templates, not the security ones.

For libwebrtc there is also `security-notify@webrtc.org`, "a community of
downstream WebRTC embedders" — the natural list for Mozilla. Chromium separately
invites vendors of Chromium-based products to request standing early access via
`security@chromium.org`, which beats per-bug CCs.

## gitlab-confidential — dav1d, libvorbis, libogg, libopus, speexdsp

| Field | Value |
| --- | --- |
| Intake | `code.videolan.org/videolan/dav1d/-/work_items`; `gitlab.xiph.org/xiph/<project>/-/work_items` |
| Privacy | "Turn on confidentiality" checkbox, **set at creation** |
| One-shot risk | **Yes — this is the dangerous one.** |
| Crash input | **Never attach. Inline base64 in the description.** |
| Encryption | Transport only. No key exists for either organisation. |
| Access preservation | You keep access automatically as the author. |
| Verification | Confirm the confidential (eye-slash) indicator on the created item. |
| CVE | Nobody assigns one. |
| Disclosure clock | Undocumented. |
| Known unknowns | None. |

Three traps, all verified:

1. **Attachments leak.** GitLab: "For public projects or groups, anyone can
   access these files through the direct attachment URL, even if the issue …
   is confidential." The mitigation requires Maintainer role *and* is blocked on
   public projects, and all five of these projects are public. Protection is a
   random 32-character URL and nothing else. If you already attached something,
   delete the upload — the URL then 404s.
2. **You get one shot at the checkbox.** GitLab enables `set_confidentiality`
   for non-members only on a not-yet-created issue. Miss it and you cannot fix
   it: notifications, RSS and webhooks have already fired. Use the prefill URL
   `…/-/issues/new?issue[confidential]=true` and still confirm visually before
   submitting.
3. **`/-/issues` returns 404 on gitlab.xiph.org** (the work-items migration).
   Only `/-/work_items` works. Do not conclude the tracker is closed and fall
   back to the GitHub mirror — those mirrors have no confidentiality and are
   indexed immediately.

Accounts: self-registration is open on both instances, and both sit behind an
Anubis proof-of-work gate, so a real browser is required. Filing needs only a
confirmed account; Xiph's admin approval applies to forking, not to issues.

Secondary contacts, for establishing contact only — never for technical
detail, since IRC is public and bot-logged: `#dav1d` and `#xiph` on
Libera.Chat (`#vorbis` and `#speex` are nearly empty). For dav1d also email
`security@videolan.org` with a one-paragraph summary and a link to the
confidential item. Xiph has no security address at all; maintainer fallbacks
are `monty@xiph.org` (vorbis, ogg), `jmvalin@jmvalin.ca` (opus, speexdsp),
`tmatth@videolan.org` (speexdsp, current maintainer) and `webmaster@xiph.org`.

Xiph documents this route in exactly one place — `speexdsp/CONTRIBUTING.md`:
"Security bugs should be filed as confidential issues."

## github-pvr — libpng

| Field | Value |
| --- | --- |
| Intake | `github.com/pnggroup/libpng` → Security → Report a vulnerability |
| Privacy | Private advisory draft, visible to maintainers and you |
| One-shot risk | No |
| Crash input | **Unverified.** GitHub's documentation describes no upload field on the report form. State the fallback: a temporary private fork, or hand the file over once a maintainer replies. |
| Encryption | Transport only. |
| Access preservation | You are added as a collaborator on the draft automatically. |
| Verification | The draft appears under your Security tab. |
| CVE | The maintainer can request one through GitHub. |
| Disclosure clock | Undocumented; GitHub's researcher template suggests 90 days. |
| Known unknowns | The attachment question above. |

Only Title and Description are mandatory. CVSS, CWE, affected/patched version
ranges, vulnerable functions and credits are all offered and all welcome here —
the opposite of Bugzilla.

**Ignore libpng's README**, which points at `png-mng-implement@lists.sourceforge.net`.
That list has a public archive and requires a subscription. Private reporting is
the live channel; libpng has published several advisories through it.

## bugzilla-restricted — libsoundtouch, Mozilla-owned, and everything with no upstream

| Field | Value |
| --- | --- |
| Intake | `bugzilla.mozilla.org`, product/component from the library's `moz.yaml` `bugzilla:` block |
| Privacy | The product's default security group (`core-security` for Core) |
| One-shot risk | No |
| Crash input | Attach — attachments inherit the bug's group. |
| Encryption | None for BMO itself. `security@mozilla.org` publishes a PGP key if you need an encrypted alternative. |
| Access preservation | Keep **"CC list members can always see this bug"** checked. |
| Verification | `GET rest/bug/<id>?include_fields=is_cc_accessible,groups,cc` — confirm `is_cc_accessible` is true, the group is set, and any external CC landed. |
| CVE | Mozilla is a CNA and assigns for its own code. |
| Disclosure clock | Reporter-controlled; Mozilla asks for a few days' notice before unhiding. |
| Known unknowns | None. |

Metadata to **omit**: Mozilla states that "a report should not have severity
keywords set or include CVSS scores or CWEs". The validator errors on those.
What Mozilla wants instead is an ASAN stack trace or crash dump plus a testcase
that reproduces it.

This profile covers three different situations:

- **libsoundtouch** — an upstream library with no private channel anywhere.
  Codeberg has no confidential issues (the Forgejo feature request has been open
  since 2022), and the maintainer publishes no key. The route is a *standalone*
  security-restricted bug containing no Firefox-internal detail, with
  `oparviai@iki.fi` CC'd, plus a contentless heads-up email telling him to log
  in. There is precedent: bugs 1328295, 1328300, 1328317, 1328320, 1328340,
  1328342, 1328346 and 1328350 were filed exactly this way in 2017.
- **Mozilla-owned upstreams** (nestegg, cubeb, mp4parse-rust) — Bugzilla
  directly. These ship in Firefox, so the Bugzilla bug is what drives the
  advisory, the uplift and the CVE. GitHub private reporting is enabled on all
  three but is only worth using afterwards, to coordinate with non-Firefox
  consumers.
- **No upstream at all** (libmkv, openmax_il, mozva, psshparser, gmp-clearkey,
  wmf-clearkey) — there is nobody external to tell. **Do not CC anyone
  outside Mozilla**; it would only widen exposure.
