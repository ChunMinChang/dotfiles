#!/usr/bin/env python3
"""Scope profiles for the Firefox bug triage skill.

A scope profile bounds the Bugzilla search performed during the
investigation step to a specific Product + Component set, so we don't
drown in unrelated hits. Profile tables are kept in sync verbatim with
mozilla/firefox/media-skills/media-bug-triage/SKILL.md §Scope Profiles.
"""

import sys

# ---------------------------------------------------------------------------
# Profile table (verbatim from media-bug-triage SKILL.md)
# ---------------------------------------------------------------------------

PROFILES = {
    "media": {
        "product": "Core",
        "components": [
            "Audio/Video",
            "Audio/Video: cubeb",
            "Audio/Video: GMP",
            "Audio/Video: MediaStreamGraph",
            "Audio/Video: Playback",
            "Audio/Video: Recording",
            "Audio/Video: Web Codecs",
        ],
    },
    "web-conferencing": {
        "product": "Core",
        "components": [
            "WebRTC",
            "WebRTC: Audio/Video",
            "WebRTC: Networking",
            "WebRTC: Signaling",
            "DOM: Screen Capture",
        ],
    },
    "media-and-web-conferencing": {
        "product": "Core",
        "components": [
            "Audio/Video",
            "Audio/Video: cubeb",
            "Audio/Video: GMP",
            "Audio/Video: MediaStreamGraph",
            "Audio/Video: Playback",
            "Audio/Video: Recording",
            "Audio/Video: Web Codecs",
            "WebRTC",
            "WebRTC: Audio/Video",
            "WebRTC: Networking",
            "WebRTC: Signaling",
            "DOM: Screen Capture",
        ],
    },
    "graphics": {
        "product": "Core",
        "components": [
            "Graphics",
            "Graphics: Canvas2D",
            "Graphics: CanvasWebGL",
            "Graphics: Color Management",
            "Graphics: Image Blocking",
            "Graphics: ImageLib",
            "Graphics: Layers",
            "Graphics: Text",
            "Graphics: WebGPU",
            "Graphics: WebRender",
            "Web Painting",
        ],
    },
    "android": {
        "product": ["Firefox for Android", "GeckoView"],
        "components": ["Media"],
    },
}

DEFAULT_PROFILE = "media"

# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def infer_profile(product, component):
    """Pick a profile from a bug's Product and Component.

    Rules (in order):
      Core / Audio/Video* or Web Audio          → media
      Core / WebRTC* or DOM: Screen Capture     → web-conferencing
      Core / Graphics* or Web Painting          → graphics
      Firefox for Android, GeckoView (any)      → android
      anything else                             → media (with stderr warning)
    """
    product = (product or "").strip()
    component = (component or "").strip()

    if product in ("Firefox for Android", "GeckoView"):
        return "android"

    if product == "Core":
        if component.startswith("Audio/Video") or component.startswith("Web Audio"):
            return "media"
        if component.startswith("WebRTC") or component == "DOM: Screen Capture":
            return "web-conferencing"
        if component.startswith("Graphics") or component == "Web Painting":
            return "graphics"

    sys.stderr.write(
        "scope_profiles: no profile match for product={!r} component={!r}; "
        "defaulting to {!r}\n".format(product, component, DEFAULT_PROFILE)
    )
    return DEFAULT_PROFILE


def resolve_profile(name):
    """Validate a user-supplied profile name. Returns the canonical key.

    Raises ValueError listing valid names if unknown.
    """
    if name is None:
        return None
    key = name.strip().lower()
    if key in PROFILES:
        return key
    raise ValueError(
        "Unknown scope profile {!r}; valid: {}".format(
            name, ", ".join(sorted(PROFILES))
        )
    )


def components_for(profile):
    """Return the list of components in this profile."""
    return list(PROFILES[profile]["components"])


def product_for(profile):
    """Return the product (str) or products (list[str]) for this profile."""
    return PROFILES[profile]["product"]
