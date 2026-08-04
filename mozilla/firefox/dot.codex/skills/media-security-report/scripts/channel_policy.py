#!/usr/bin/env python3
"""Channel and library policy for Firefox-vendored media libraries.

This is the machine-readable half of ``references/library-policies.md`` and
``references/channel-profiles.md``. The prose in those files explains *why*;
this module holds only what a script must check. ``TestPolicyTablesInSync``
asserts the two never drift apart.

Nothing here describes the *contents* of a report beyond the requirement
tables: paths, revisions and Bugzilla components are read live from the
checkout by ``media_lib_facts``, because a hardcoded copy of those rots (see
sherlock's ``references/upstream-libs.md``, which still points at
``netwerk/srtp``).
"""

from __future__ import annotations

from collections import namedtuple


# --------------------------------------------------------------------------
# Channel profiles
# --------------------------------------------------------------------------

Profile = namedtuple(
    "Profile",
    """
    id intake_kind privacy_mechanic privacy_timing one_shot
    input_delivery input_fallback metadata_include metadata_omit
    access_preservation verification encryption cve_ownership
    disclosure_clock draft_anchor known_unknowns
    """.split(),
)

# input_delivery values and what they mean for the report writer:
#   attach            — a normal file attachment is safe and expected
#   attach-mandatory  — the channel requires the input as an attachment
#   attach-encrypted  — attach, but inside the encrypted mail body
#   attach-unverified — attachment support is not documented; state a fallback
#   inline-base64     — NEVER attach; the attachment would be world-readable
#   attach-bugzilla   — Bugzilla attachment, inherits the bug's group

PROFILES = {
    "email-plain": Profile(
        id="email-plain",
        intake_kind="private mailing list or maintainer address, no encryption",
        privacy_mechanic="closed recipient list; the message itself is the report",
        privacy_timing="n/a",
        one_shot=False,
        input_delivery="attach-mandatory",
        input_fallback="none — the input is part of the report",
        metadata_include=(),
        metadata_omit=("firefox-internal",),
        access_preservation="keep your own copy; there is no thread you can read back",
        verification="none available — assume no acknowledgement",
        encryption="none",
        cve_ownership="none",
        disclosure_clock="undocumented — set your own and say so",
        draft_anchor="email-plain",
        known_unknowns=("no acknowledgement SLA is published",),
    ),
    "email-gpg": Profile(
        id="email-gpg",
        intake_kind="maintainer address with a published GPG key",
        privacy_mechanic="end-to-end GPG encryption to the published fingerprint",
        privacy_timing="n/a",
        one_shot=False,
        input_delivery="attach-encrypted",
        input_fallback="none — attach inside the encrypted payload",
        metadata_include=("affected-supported-release", "ai-usage-location"),
        metadata_omit=("firefox-internal",),
        access_preservation="keep your sent copy; encrypt to yourself as well",
        verification="none available",
        encryption="gpg",
        cve_ownership="none",
        disclosure_clock="undocumented",
        draft_anchor="email-gpg",
        known_unknowns=(),
    ),
    "buganizer": Profile(
        id="buganizer",
        intake_kind="Google Issue Tracker (Buganizer) instance; any Google account",
        privacy_mechanic=(
            "Type=Vulnerability flips Access to Limited Visibility and adds "
            "security@chromium.org as collaborator"
        ),
        privacy_timing="at-creation via the Security report template, or any time by setting Type",
        one_shot=False,
        input_delivery="attach",
        input_fallback="attach directly, never inside a zip (Chromium asks for this)",
        metadata_include=("git-describe-version",),
        metadata_omit=("firefox-internal",),
        access_preservation=(
            "CC yourself BEFORE submitting — Limited Visibility restricts the issue "
            "to explicitly listed identities and can lock the reporter out"
        ),
        verification="reopen the issue URL while signed in; confirm you still have access",
        encryption="transport-only",
        cve_ownership="chrome-cna",
        disclosure_clock="Chromium: 14 weeks after the issue is marked Fixed",
        draft_anchor="buganizer",
        known_unknowns=(
            "whether the WebM and AOMedia instances honour Chromium's 14-week clock",
            "whether libyuv's tracker offers a Security report template at all",
        ),
    ),
    "gitlab-confidential": Profile(
        id="gitlab-confidential",
        intake_kind="self-hosted GitLab; confidential work item; account required",
        privacy_mechanic='"Turn on confidentiality" checkbox, set at creation',
        privacy_timing="at-creation",
        one_shot=True,
        input_delivery="inline-base64",
        input_fallback=(
            "offer the file out-of-band once a maintainer replies; never attach"
        ),
        metadata_include=(),
        metadata_omit=("firefox-internal",),
        access_preservation=(
            "you keep access as the author (assignee_or_author); no extra step"
        ),
        verification="confirm the confidential (eye-slash) indicator on the created item",
        encryption="transport-only",
        cve_ownership="none",
        disclosure_clock="undocumented",
        draft_anchor="gitlab-confidential",
        known_unknowns=(),
    ),
    "github-pvr": Profile(
        id="github-pvr",
        intake_kind="GitHub private vulnerability reporting (Security tab)",
        privacy_mechanic="private advisory draft, visible to maintainers and you",
        privacy_timing="at-creation",
        one_shot=False,
        input_delivery="attach-unverified",
        input_fallback="temporary private fork, or hand over once the maintainer replies",
        metadata_include=("cvss", "cwe", "affected-versions", "credits"),
        metadata_omit=("firefox-internal",),
        access_preservation="you are added as a collaborator on the draft automatically",
        verification="the draft advisory appears under your Security tab",
        encryption="transport-only",
        cve_ownership="maintainer may request via GitHub",
        disclosure_clock="undocumented; GitHub's template suggests 90 days",
        draft_anchor="github-pvr",
        known_unknowns=(
            "whether the report form accepts file uploads — docs describe no upload field",
        ),
    ),
    "bugzilla-restricted": Profile(
        id="bugzilla-restricted",
        intake_kind="bugzilla.mozilla.org, security-restricted bug",
        privacy_mechanic="the product's default security group (Core -> core-security)",
        privacy_timing="at-creation via the Security row; can be set later too",
        one_shot=False,
        input_delivery="attach-bugzilla",
        input_fallback="none needed — attachments inherit the bug's group",
        metadata_include=("sec-keyword", "asan-trace", "testcase"),
        metadata_omit=("cvss", "cwe"),
        access_preservation=(
            'keep "CC list members can always see this bug" checked, or a CC\'d '
            "external silently loses access and receives no mail"
        ),
        verification=(
            "GET rest/bug/<id>?include_fields=is_cc_accessible,groups,cc and confirm "
            "is_cc_accessible is true and the group is set"
        ),
        encryption="none for BMO itself; security@mozilla.org publishes a PGP key",
        cve_ownership="mozilla-cna",
        disclosure_clock="reporter-controlled; Mozilla asks for notice before unhiding",
        draft_anchor="bugzilla-restricted",
        known_unknowns=(),
    ),
}


# --------------------------------------------------------------------------
# Libraries
# --------------------------------------------------------------------------

Library = namedtuple(
    "Library",
    """
    id paths moz_yaml channels intake revision_source repo_url forge
    has_upstream cc_external notes
    """.split(),
)

# revision_source values: "moz.yaml" (the normal case) or the name of the
# fallback file that records the vendored revision instead.

_MOZILLA_OWNED = "Mozilla-owned upstream; the Bugzilla bug drives the advisory and CVE"
_NO_UPSTREAM = "no upstream exists; this is a Firefox bug, do not CC anyone external"

LIBRARIES = {
    "ffvpx": Library(
        id="ffvpx",
        paths=("media/ffvpx",),
        moz_yaml=None,
        channels=("email-plain",),
        intake="ffmpeg-security@ffmpeg.org",
        revision_source="README_MOZILLA",
        repo_url="https://github.com/FFmpeg/FFmpeg",
        forge="github",
        has_upstream=True,
        cc_external=(),
        notes="ffvpx is a trimmed FFmpeg subset; confirm the code is in the vendored subset",
    ),
    "libvpx": Library(
        id="libvpx",
        paths=("media/libvpx",),
        moz_yaml="media/libvpx/moz.yaml",
        channels=("buganizer",),
        intake="issues.webmproject.org component 1618984, template 2023994 (Security report)",
        revision_source="moz.yaml",
        repo_url=None,
        forge="googlesource",
        has_upstream=True,
        cc_external=(),
        notes="the template ID in the README (2023833) is the bug template, not the security one",
    ),
    "libwebp": Library(
        id="libwebp",
        paths=("media/libwebp",),
        moz_yaml="media/libwebp/moz.yaml",
        channels=("buganizer",),
        intake="issues.webmproject.org component 1618983, template 2024050 (Security report)",
        revision_source="moz.yaml",
        repo_url=None,
        forge="github",
        has_upstream=True,
        cc_external=(),
        notes="tracking is 'tag' but the pin is a hash; origin.url and vendoring.url differ",
    ),
    "libaom": Library(
        id="libaom",
        paths=("media/libaom", "third_party/aom"),
        moz_yaml="media/libaom/moz.yaml",
        channels=("buganizer",),
        intake="aomedia.issues.chromium.org component 1597128, template 2015013 (Security report)",
        revision_source="moz.yaml",
        repo_url=None,
        forge="googlesource",
        has_upstream=True,
        cc_external=(),
        notes="",
    ),
    "libyuv": Library(
        id="libyuv",
        paths=("media/libyuv",),
        moz_yaml="media/libyuv/moz.yaml",
        channels=("buganizer",),
        intake="libyuv.issues.chromium.org — no documented security template",
        revision_source="moz.yaml",
        repo_url=None,
        forge="googlesource",
        has_upstream=True,
        cc_external=(),
        notes="no bug-reporting docs at all; set Type=Vulnerability manually after CC'ing yourself",
    ),
    "libwebrtc": Library(
        id="libwebrtc",
        paths=("third_party/libwebrtc", "media/webrtc"),
        moz_yaml=None,
        channels=("buganizer",),
        intake="Google Bughunters (Chrome VRP); fallback issues.chromium.org component 1363614 template 1922342",
        revision_source="README.mozilla.last-vendor",
        repo_url="https://webrtc.googlesource.com/src",
        forge="googlesource",
        has_upstream=True,
        cc_external=(),
        notes="security-notify@webrtc.org is the downstream-embedder list; revision is a short hash",
    ),
    "dav1d": Library(
        id="dav1d",
        paths=("media/libdav1d", "third_party/dav1d"),
        moz_yaml="media/libdav1d/moz.yaml",
        channels=("gitlab-confidential", "email-plain"),
        intake="code.videolan.org/videolan/dav1d confidential work item; also security@videolan.org",
        revision_source="moz.yaml",
        repo_url=None,
        forge="gitlab",
        has_upstream=True,
        cc_external=(),
        notes="do both: confidential item for the maintainers, email for the org record",
    ),
    "libvorbis": Library(
        id="libvorbis",
        paths=("media/libvorbis",),
        moz_yaml="media/libvorbis/moz.yaml",
        channels=("gitlab-confidential",),
        intake="gitlab.xiph.org/xiph/vorbis confidential work item",
        revision_source="moz.yaml",
        repo_url=None,
        forge="gitlab",
        has_upstream=True,
        cc_external=(),
        notes="no security@xiph.org exists; maintainer fallback monty@xiph.org",
    ),
    "libogg": Library(
        id="libogg",
        paths=("media/libogg",),
        moz_yaml="media/libogg/moz.yaml",
        channels=("gitlab-confidential",),
        intake="gitlab.xiph.org/xiph/ogg confidential work item",
        revision_source="moz.yaml",
        repo_url=None,
        forge="gitlab",
        has_upstream=True,
        cc_external=(),
        notes="maintainer fallback monty@xiph.org, giles@xiph.org, tterribe@xiph.org",
    ),
    "libopus": Library(
        id="libopus",
        paths=("media/libopus",),
        moz_yaml="media/libopus/moz.yaml",
        channels=("gitlab-confidential",),
        intake="gitlab.xiph.org/xiph/opus confidential work item",
        revision_source="moz.yaml",
        repo_url=None,
        forge="gitlab",
        has_upstream=True,
        cc_external=(),
        notes="never use the public opus@xiph.org list; maintainer jmvalin@jmvalin.ca",
    ),
    "speexdsp": Library(
        id="speexdsp",
        paths=("media/libspeex_resampler",),
        moz_yaml="media/libspeex_resampler/moz.yaml",
        channels=("gitlab-confidential",),
        intake="gitlab.xiph.org/xiph/speexdsp confidential work item",
        revision_source="moz.yaml",
        repo_url=None,
        forge="gitlab",
        has_upstream=True,
        cc_external=(),
        notes="its CONTRIBUTING.md is the only place Xiph documents the confidential route",
    ),
    "libpng": Library(
        id="libpng",
        paths=("media/libpng",),
        moz_yaml="media/libpng/moz.yaml",
        channels=("github-pvr",),
        intake="github.com/pnggroup/libpng -> Security -> Report a vulnerability",
        revision_source="moz.yaml",
        repo_url=None,
        forge="github",
        has_upstream=True,
        cc_external=(),
        notes="the README misdirects to a publicly archived SourceForge list; do not use it",
    ),
    "libjpeg-turbo": Library(
        id="libjpeg-turbo",
        paths=("media/libjpeg",),
        moz_yaml="media/libjpeg/moz.yaml",
        channels=("email-gpg",),
        intake="information@libjpeg-turbo.org, GPG D291 2829 1D60 993B 8CC8 5724 8475 77AB B633 DB01",
        revision_source="moz.yaml",
        repo_url=None,
        forge="github",
        has_upstream=True,
        cc_external=(),
        notes="has a scope gate: supported release, malformed data through a public API",
    ),
    "libsoundtouch": Library(
        id="libsoundtouch",
        paths=("media/libsoundtouch",),
        moz_yaml="media/libsoundtouch/moz.yaml",
        channels=("bugzilla-restricted",),
        intake="standalone security-restricted Bugzilla bug, CC oparviai@iki.fi",
        revision_source="moz.yaml",
        repo_url=None,
        forge="codeberg",
        has_upstream=True,
        cc_external=("oparviai@iki.fi",),
        notes=(
            "Codeberg has no confidential issues; precedent bugs 1328295, 1328300, "
            "1328317, 1328320, 1328340, 1328342, 1328346, 1328350"
        ),
    ),
    "libsrtp": Library(
        id="libsrtp",
        paths=("third_party/libsrtp",),
        moz_yaml="third_party/libsrtp/moz.yaml",
        channels=("email-plain",),
        intake="libsrtp-security@lists.packetizer.com (closed list, anyone may post)",
        revision_source="moz.yaml",
        repo_url=None,
        forge="github",
        has_upstream=True,
        cc_external=(),
        notes="Cisco PSIRT only as a separate second notice if Cisco products embed the flaw",
    ),
    "nestegg": Library(
        id="nestegg",
        paths=("media/libnestegg",),
        moz_yaml="media/libnestegg/moz.yaml",
        channels=("bugzilla-restricted", "github-pvr"),
        intake="security-restricted Bugzilla bug (primary); GitHub PVR only for downstream coordination",
        revision_source="moz.yaml",
        repo_url=None,
        forge="github",
        has_upstream=True,
        cc_external=(),
        notes=_MOZILLA_OWNED,
    ),
    "cubeb": Library(
        id="cubeb",
        paths=("media/libcubeb",),
        moz_yaml="media/libcubeb/moz.yaml",
        channels=("bugzilla-restricted", "github-pvr"),
        intake="security-restricted Bugzilla bug (primary); GitHub PVR only for downstream coordination",
        revision_source="moz.yaml",
        repo_url=None,
        forge="github",
        has_upstream=True,
        cc_external=(),
        notes=_MOZILLA_OWNED,
    ),
    "mp4parse-rust": Library(
        id="mp4parse-rust",
        paths=("media/mp4parse-rust",),
        moz_yaml=None,
        channels=("bugzilla-restricted", "github-pvr"),
        intake="security-restricted Bugzilla bug (primary); GitHub PVR only for downstream coordination",
        revision_source="Cargo.toml",
        repo_url="https://github.com/mozilla/mp4parse-rust",
        forge="github",
        has_upstream=True,
        cc_external=(),
        notes=_MOZILLA_OWNED + "; the crate is vendored under third_party/rust",
    ),
    "libmkv": Library(
        id="libmkv",
        paths=("media/libmkv",),
        moz_yaml="media/libmkv/moz.yaml",
        channels=("bugzilla-restricted",),
        intake="security-restricted Bugzilla bug",
        revision_source="moz.yaml",
        repo_url=None,
        forge=None,
        has_upstream=False,
        cc_external=(),
        notes="upstream abandoned and deleted from libvpx; six local patches. "
        + _NO_UPSTREAM,
    ),
    "openmax_il": Library(
        id="openmax_il",
        paths=("media/openmax_il",),
        moz_yaml=None,
        channels=("bugzilla-restricted",),
        intake="security-restricted Bugzilla bug",
        revision_source=None,
        repo_url=None,
        forge=None,
        has_upstream=False,
        cc_external=(),
        notes="frozen Khronos OpenMAX IL 1.1.2 spec headers. " + _NO_UPSTREAM,
    ),
    "mozva": Library(
        id="mozva",
        paths=("media/mozva",),
        moz_yaml=None,
        channels=("bugzilla-restricted",),
        intake="security-restricted Bugzilla bug",
        revision_source=None,
        repo_url=None,
        forge=None,
        has_upstream=False,
        cc_external=(),
        notes=(
            "mozva.c is a Mozilla dlopen shim; only va/*.h are copied libva headers. "
            "Route to Intel's process only if the flaw is in libva's own runtime. "
            + _NO_UPSTREAM
        ),
    ),
    "psshparser": Library(
        id="psshparser",
        paths=("media/psshparser",),
        moz_yaml=None,
        channels=("bugzilla-restricted",),
        intake="security-restricted Bugzilla bug",
        revision_source=None,
        repo_url=None,
        forge=None,
        has_upstream=False,
        cc_external=(),
        notes="Mozilla-authored. " + _NO_UPSTREAM,
    ),
    "gmp-clearkey": Library(
        id="gmp-clearkey",
        paths=("media/gmp-clearkey",),
        moz_yaml=None,
        channels=("bugzilla-restricted",),
        intake="security-restricted Bugzilla bug",
        revision_source=None,
        repo_url=None,
        forge=None,
        has_upstream=False,
        cc_external=(),
        notes="Mozilla-authored reference Clear Key CDM. " + _NO_UPSTREAM,
    ),
    "wmf-clearkey": Library(
        id="wmf-clearkey",
        paths=("media/wmf-clearkey",),
        moz_yaml=None,
        channels=("bugzilla-restricted",),
        intake="security-restricted Bugzilla bug",
        revision_source=None,
        repo_url=None,
        forge=None,
        has_upstream=False,
        cc_external=(),
        notes="Mozilla-authored WMF Clear Key. " + _NO_UPSTREAM,
    ),
    "nicer": Library(
        id="nicer",
        paths=("dom/media/webrtc/transport/third_party/nICEr",),
        moz_yaml="dom/media/webrtc/transport/third_party/nICEr/moz.yaml",
        channels=("bugzilla-restricted",),
        intake="security-restricted Bugzilla bug",
        revision_source="moz.yaml",
        repo_url=None,
        forge="github",
        has_upstream=True,
        cc_external=(),
        notes="upstream resiprocate/nICEr is near-dormant; Mozilla carries the fixes",
    ),
    "widevine-adapter": Library(
        id="widevine-adapter",
        paths=("dom/media/gmp/widevine-adapter",),
        moz_yaml="dom/media/gmp/widevine-adapter/moz.yaml",
        channels=("buganizer",),
        intake="Chromium security bug (the CDM interface headers are Chromium's)",
        revision_source="moz.yaml",
        repo_url=None,
        forge="googlesource",
        has_upstream=True,
        cc_external=(),
        notes="",
    ),
}

# Where a library has no policy row, routing fails closed to this profile.
FALLBACK_PROFILE = "bugzilla-restricted"


def resolve_library(token):
    """Map a library id or a tree path to a library id.

    Returns ``(library_id, note)``. ``library_id`` is ``None`` when the token
    matched nothing at all; ``note`` is a human-readable explanation for the
    caller to surface. Never guesses between two candidates.
    """
    if not token:
        return None, "no library given"

    needle = token.strip().strip("/").lower()
    if needle in LIBRARIES:
        return needle, ""

    # Path match: longest path wins, so third_party/libsrtp/src resolves even
    # though the policy row records third_party/libsrtp.
    matches = []
    for lib in LIBRARIES.values():
        for path in lib.paths:
            p = path.lower()
            if needle == p or needle.startswith(p + "/") or p.startswith(needle + "/"):
                matches.append((len(p), lib.id))
    if matches:
        matches.sort(reverse=True)
        best = matches[0][0]
        winners = sorted({lib_id for length, lib_id in matches if length == best})
        if len(winners) == 1:
            return winners[0], ""
        return None, "ambiguous: matches " + ", ".join(winners)

    if needle.startswith(("media/", "third_party/", "dom/media/")):
        return None, (
            f"no policy row for {token}; fail closed to {FALLBACK_PROFILE} "
            "and add a row to references/library-policies.md"
        )
    return None, f"unknown library {token!r}"


def profile_for(library_id):
    """Primary channel profile for a library id."""
    lib = LIBRARIES.get(library_id)
    if lib is None:
        return FALLBACK_PROFILE
    return lib.channels[0]


# --------------------------------------------------------------------------
# Forge grammars
# --------------------------------------------------------------------------

# Each pattern captures the ref (branch, tag or commit) a source link is
# pinned to, so the validator can insist it matches the vendored revision.
FORGE_PATTERNS = {
    "github": (
        r"https?://github\.com/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)"
        r"/(?:blob|commit|tree|raw)/(?P<ref>[^/#?\s]+)"
    ),
    "gitlab": (
        r"https?://(?P<host>gitlab\.[^/\s]+|code\.videolan\.org)/(?P<ns>[^\s?#]+?)"
        r"/-/(?:blob|commit|tree|raw)/(?P<ref>[^/#?\s]+)"
    ),
    "googlesource": (
        r"https?://(?P<host>[a-z0-9.-]*googlesource\.com)/(?P<repo>[^\s?#]+?)"
        r"/\+/(?P<ref>[^/#?\s]+)"
    ),
    "codeberg": (
        r"https?://codeberg\.org/(?P<owner>[^/\s]+)/(?P<repo>[^/\s]+)"
        r"/src/(?:commit|branch|tag)/(?P<ref>[^/#?\s]+)"
    ),
}

# Refs that are never acceptable, whatever the library pins.
MOVING_REFS = frozenset(
    {"master", "main", "head", "trunk", "latest", "tip", "default", "stable"}
)

SEARCHFOX_REV = r"https?://searchfox\.org/[^/\s]+/rev/(?P<ref>[0-9a-f]{40})/"


# --------------------------------------------------------------------------
# Requirements
# --------------------------------------------------------------------------

Requirement = namedtuple("Requirement", "key label patterns evidence severity")
Prohibition = namedtuple("Prohibition", "key label pattern reason severity")


def _req(key, label, patterns, evidence, severity="error"):
    return Requirement(key, label, tuple(patterns), evidence, severity)


# The universal evidence core. This is FFmpeg's ten generalized -- that list is
# really "what a maintainer needs in order to act" -- plus the AI-disclosure
# item, which FFmpeg, libjpeg-turbo and Chromium all now demand.
CORE_REQUIREMENTS = (
    _req(
        "human-reviewer",
        "human reviewer",
        (r"human\s+reviewer", r"reviewer\s*[:)]", r"reviewed\s+by"),
        "name or an explicit unavailable/unknown status",
    ),
    _req(
        "finder-credit",
        "finder credit",
        (r"finder\s+credit", r"credited?\s+(?:to|for)", r"human.*find"),
        "finder name or an explicit unavailable/unknown status",
    ),
    _req(
        "testcase",
        "reproducible testcase",
        (r"reproduc", r"test\s*case", r"testcase", r"command\s+line", r"harness"),
        "copy/paste command or complete harness description",
    ),
    _req(
        "source-identifier",
        "source identifier",
        (
            r"source\s+(?:identifier|revision)",
            r"version\s*/?\s*revision",
            r"git\s+commit",
            r"vendored\s+revision",
        ),
        "source/revision field naming the affected revision",
    ),
    _req(
        "stack-trace",
        "stack trace",
        (r"stack\s+trace", r"observed\s+crash", r"asan", r"sanitizer", r"#\d+"),
        "stack or explicit unavailable/unknown status",
    ),
    _req(
        "analysis",
        "analysis/description",
        (r"analysis", r"root\s+cause", r"code\s+path", r"impact", r"description"),
        "evidence-backed issue description",
    ),
    _req(
        "introducing-commit",
        "introducing commit",
        (r"introduc(?:ing|ed)", r"first\s+affected", r"originat(?:ing|ed)", r"unknown"),
        "commit/history statement or explicit unknown status",
    ),
    _req(
        "proposed-fix",
        "proposed fix",
        (
            r"proposed\s+fix",
            r"suggested\s+fix",
            r"fix\s+patch",
            r"\.patch",
            r"no\s+fix\s+(?:is\s+)?available",
        ),
        "patch or explicit unavailable status",
    ),
    _req(
        "cve-status",
        "CVE/related identifier",
        (
            r"\bcve\b",
            r"related\s+identifier",
            r"none\s+(?:assigned|known)",
            r"not\s+assigned",
        ),
        "identifier or explicit none/unknown status",
    ),
    _req(
        "ai-disclosure",
        "human origination / AI-usage disclosure",
        (
            r"ai[- ]?(?:usage|assisted|generated|tool)",
            r"human[- ]verified",
            r"human[- ]originat",
            r"no\s+ai\s+(?:was\s+)?used",
            r"verified\s+by\s+a\s+human",
        ),
        "statement of whether and where AI was used, and who verified it by hand",
    ),
)

PROFILE_REQUIREMENTS = {
    "buganizer": (
        _req(
            "git-describe-version",
            "library version from git describe",
            (
                r"git\s+describe",
                r"version\s*\(use\s*`?git\s+describe",
                r"\bversion:\s*\S",
            ),
            "the version line the Security report template asks for",
        ),
        _req(
            "cc-yourself",
            "access-preservation note (CC yourself)",
            (r"cc\s+yourself", r"cc'?d?\s+myself", r"preserve\s+access"),
            "a reminder that Limited Visibility can lock the reporter out",
        ),
    ),
    "gitlab-confidential": (
        _req(
            "inline-input",
            "crash input delivered inline",
            (r"inline\s+base64", r"base64", r"no\s+attachment"),
            "attachments on a confidential issue in a public project are world-readable",
        ),
        _req(
            "confidential-at-creation",
            "confidentiality set at creation",
            (
                r"turn\s+on\s+confidentiality",
                r"issue\[confidential\]=true",
                r"confidential\s+(?:issue|work\s+item)",
            ),
            "a non-member cannot make an issue confidential after it is created",
        ),
    ),
    "email-gpg": (
        _req(
            "scope-gate",
            "upstream scope gate",
            (
                r"supported\s+release",
                r"public\s+api",
                r"malformed\s+(?:image\s+)?data",
                r"not\s+eol",
            ),
            "libjpeg-turbo only counts it if a well-behaved caller trips it on a supported release",
        ),
        _req(
            "gpg-fingerprint",
            "GPG fingerprint quoted",
            (r"[0-9A-F]{4}(?:\s?[0-9A-F]{4}){9}", r"gpg", r"encrypt"),
            "the published key fingerprint, so the sender verifies it out of band",
            severity="warning",
        ),
    ),
    "bugzilla-restricted": (
        _req(
            "security-group",
            "security group named",
            (r"core-security", r"security[- ]sensitive", r"security\s+group"),
            "the bug must be filed into the product's security group",
        ),
        _req(
            "asan-or-testcase",
            "ASAN trace or crash dump plus a testcase",
            (r"asan", r"crash\s+dump", r"testcase", r"test\s+case"),
            "Mozilla's baseline report expectation",
        ),
    ),
    "github-pvr": (),
    "email-plain": (),
}

LIBRARY_REQUIREMENTS = {
    # FFmpeg's ten are the only published list that goes beyond the core: it
    # additionally insists on a generator script and an attached input file.
    "ffvpx": (
        _req(
            "input-generation-script",
            "input-generation script",
            (
                r"input[- ]generation",
                r"input\s+generator",
                r"generat(?:or|ing)\s+script",
                r"no\s+independent",
            ),
            "script or an explicit unavailable status (FFmpeg requirement 8)",
        ),
        _req(
            "attached-input",
            "attached input file",
            (r"attach", r"\binput-[\w.-]+", r"multimedia\s+input"),
            "FFmpeg asks for the input file alongside the command line (requirement 3)",
        ),
    ),
    "libsoundtouch": (
        _req(
            "cc-accessible",
            "CC access verification",
            (r"is_cc_accessible", r"cc\s+list\s+members\s+can\s+always\s+see"),
            "a CC'd external loses access silently if the bit is cleared",
        ),
    ),
}

PROFILE_PROHIBITIONS = {
    "bugzilla-restricted": (
        Prohibition(
            "no-cvss",
            "CVSS score",
            r"CVSS:?\s*3|cvss\s*score|AV:[NALP]/AC:",
            "Mozilla: a report should not include CVSS scores",
            "error",
        ),
        Prohibition(
            "no-cwe",
            "CWE identifier",
            r"\bCWE-\d+",
            "Mozilla: a report should not include CWEs",
            "error",
        ),
    ),
}

# Downstream detail that must never reach an upstream maintainer. Skipped for
# bugzilla-restricted, where the report *is* the Bugzilla bug.
LEAK_PATTERNS = (
    Prohibition(
        "leak-bugzilla",
        "Bugzilla link",
        r"bugzilla\.mozilla\.org",
        "downstream tracker detail",
        "error",
    ),
    Prohibition(
        "leak-searchfox",
        "searchfox link",
        r"searchfox\.org",
        "cite the upstream forge, not Firefox's code index",
        "error",
    ),
    Prohibition(
        "leak-phabricator",
        "Phabricator link",
        r"phabricator\.services\.mozilla\.com",
        "downstream review detail",
        "error",
    ),
    Prohibition(
        "leak-sec-rating",
        "Mozilla security rating",
        r"\bsec-(?:critical|high|moderate|low|other)\b",
        "internal severity rating",
        "error",
    ),
    Prohibition(
        "leak-home-path",
        "local absolute path",
        r"/(?:home|Users)/[A-Za-z0-9._-]+/",
        "local filesystem path",
        "error",
    ),
    Prohibition(
        "leak-product-name",
        "downstream product name",
        r"\b(?:Firefox|Gecko|mozilla-central)\b",
        "acceptable as provenance, but never as part of the reproduction",
        "warning",
    ),
)


def requirements_for(library_id, profile_id):
    """Effective requirement set: core + profile + library."""
    return (
        CORE_REQUIREMENTS
        + PROFILE_REQUIREMENTS.get(profile_id, ())
        + LIBRARY_REQUIREMENTS.get(library_id, ())
    )


def prohibitions_for(library_id, profile_id):
    """Effective prohibition set, including the downstream-leak scan."""
    rules = list(PROFILE_PROHIBITIONS.get(profile_id, ()))
    lib = LIBRARIES.get(library_id)
    upstream_bound = profile_id != "bugzilla-restricted"
    if upstream_bound and (lib is None or lib.has_upstream):
        rules.extend(LEAK_PATTERNS)
    return tuple(rules)
