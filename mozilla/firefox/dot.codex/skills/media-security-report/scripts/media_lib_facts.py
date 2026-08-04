#!/usr/bin/env python3
"""Read per-library facts out of a Firefox checkout.

Paths, vendored revisions and Bugzilla components are read from the tree at
run time rather than copied into this skill, so they cannot go stale. Only
*policy* (which channel, which traps) is hardcoded, in ``channel_policy``.

Three things make this less trivial than "grep moz.yaml":

* Three libraries that ship in ``media/`` have no ``moz.yaml`` at all --
  ffvpx records its revision in ``README_MOZILLA``, libwebrtc in
  ``README.mozilla.last-vendor``, and mp4parse-rust is an in-tree crate.
* ``origin.url`` is often the project homepage, not the repository. Permalinks
  must use ``vendoring.url`` + ``vendoring.source-hosting``.
* The Bugzilla component may come from the ``bugzilla:`` block, from the
  directory's own ``moz.build``, or from a ``with Files(...)`` glob in an
  ancestor ``moz.build``.

Stdlib only: the tree's vendored PyYAML is not importable from a plain
``python3``, and this must run before any build.
"""

from __future__ import annotations

import argparse
import dataclasses
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import channel_policy  # noqa: E402


FULL_HASH_RE = re.compile(r"^[0-9a-f]{40}$", re.I)
SHORT_HASH_RE = re.compile(r"^[0-9a-f]{7,39}$", re.I)
BUG_COMPONENT_RE = re.compile(
    r"""BUG_COMPONENT\s*=\s*\(\s*["']([^"']+)["']\s*,\s*["']([^"']+)["']\s*\)"""
)
WITH_FILES_RE = re.compile(r"""^\s*with\s+Files\(\s*["']([^"']+)["']\s*\)\s*:""")

# Keys worth extracting, as "section.key". Everything else is ignored, which
# keeps deeply nested blocks (update-actions, exclude lists) out of the way.
WANTED_KEYS = frozenset(
    {
        "origin.name",
        "origin.url",
        "origin.revision",
        "origin.release",
        "origin.license",
        "vendoring.url",
        "vendoring.source-hosting",
        "vendoring.vendor-directory",
        "vendoring.tracking",
        "bugzilla.product",
        "bugzilla.component",
    }
)


@dataclasses.dataclass
class LibraryFacts:
    """Everything the skill needs to know about one vendored library."""

    library_id: str
    tree_root: str | None = None
    moz_yaml: str | None = None
    vendor_dir: str | None = None
    origin_name: str | None = None
    homepage_url: str | None = None
    repo_url: str | None = None
    forge: str | None = None
    revision: str | None = None
    revision_kind: str = "none"  # full-hash | short-hash | tag | in-tree | none
    revision_source: str | None = None
    bug_product: str | None = None
    bug_component: str | None = None
    bug_component_source: str | None = None
    has_upstream: bool = True
    channels: tuple = ()
    profile: str | None = None
    intake: str | None = None
    cc_external: tuple = ()
    local_patches: tuple = ()
    notes: str = ""
    warnings: tuple = ()

    def permalink_template(self):
        """URL template for citing a line of upstream source."""
        if not self.repo_url or not self.forge or not self.revision:
            return None
        base = self.repo_url.rstrip("/")
        ref = self.revision
        if self.forge == "github":
            return f"{base}/blob/{ref}/{{path}}#L{{line}}"
        if self.forge == "gitlab":
            return f"{base}/-/blob/{ref}/{{path}}#L{{line}}"
        if self.forge == "googlesource":
            return f"{base}/+/{ref}/{{path}}#{{line}}"
        if self.forge == "codeberg":
            return f"{base}/src/commit/{ref}/{{path}}#L{{line}}"
        return None


# --------------------------------------------------------------------------
# Checkout discovery
# --------------------------------------------------------------------------


def find_checkout(explicit=None, start=None):
    """Locate a Firefox checkout.

    Order: explicit argument, then walk up from ``start`` (default cwd), then
    ``$FIREFOX_SRC``. Never falls back to a hardcoded path -- the skill is
    symlinked into each worktree's ``.codex/skills/`` and the worktrees sit
    at different revisions, so guessing one would silently pin a report to the
    wrong source.
    """
    if explicit:
        root = Path(explicit).expanduser().resolve()
        return root if _is_checkout(root) else None

    here = Path(start or Path.cwd()).resolve()
    for candidate in [here, *here.parents]:
        if _is_checkout(candidate):
            return candidate

    env = os.environ.get("FIREFOX_SRC")
    if env:
        root = Path(env).expanduser().resolve()
        if _is_checkout(root):
            return root
    return None


def _is_checkout(path):
    return (path / "mach").is_file() and (path / "media" / "moz.build").is_file()


# --------------------------------------------------------------------------
# moz.yaml
# --------------------------------------------------------------------------


def _strip_comment(value):
    """Drop a trailing ``#`` comment that is not inside quotes."""
    out, quote = [], None
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).strip()


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_moz_yaml(path):
    """Extract the handful of ``moz.yaml`` keys this skill needs.

    A whitelisting scanner rather than a YAML parser: it reads only top-level
    sections and their immediate children, so nested list blocks such as
    ``update-actions`` cannot inject a stray ``url``. Comment lines are dropped
    first -- the schema template itself contains ``# Revision to pull in``,
    which a naive grep would happily match.
    """
    data = {}
    section = None
    child_indent = None

    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = _strip_comment(raw.strip())
        if not line:
            continue

        if indent == 0:
            section = line[:-1].strip() if line.endswith(":") else None
            child_indent = None
            if ":" in line and not line.endswith(":"):
                key, _, value = line.partition(":")
                data[key.strip()] = _unquote(value.strip())
            continue

        if section is None or line.startswith("-") or ":" not in line:
            continue

        # Lock onto the indent of the section's first child; anything deeper
        # belongs to a nested structure we do not care about.
        if child_indent is None:
            child_indent = indent
        if indent != child_indent:
            continue

        key, _, value = line.partition(":")
        full = f"{section}.{key.strip()}"
        if full in WANTED_KEYS:
            data[full] = _unquote(value.strip())
    return data


def classify_revision(value):
    """Return ``(revision, kind)`` for a raw revision/release string."""
    if not value:
        return None, "none"
    token = _unquote(value.strip()).split()[0].strip().rstrip(".,")
    if not token:
        return None, "none"
    if FULL_HASH_RE.match(token):
        return token, "full-hash"
    if SHORT_HASH_RE.match(token):
        return token, "short-hash"
    return token, "tag"


# --------------------------------------------------------------------------
# Revision fallbacks for the libraries with no moz.yaml
# --------------------------------------------------------------------------


def _revision_from_readme_mozilla(root):
    path = root / "media" / "ffvpx" / "README_MOZILLA"
    if not path.is_file():
        return None, "none", None
    match = re.search(
        r"revision\s+([0-9a-f]{7,40})",
        path.read_text(encoding="utf-8", errors="replace"),
    )
    if not match:
        return None, "none", None
    revision, kind = classify_revision(match.group(1))
    return revision, kind, "media/ffvpx/README_MOZILLA"


def _revision_from_last_vendor(root):
    path = root / "third_party" / "libwebrtc" / "README.mozilla.last-vendor"
    if not path.is_file():
        return None, "none", None
    text = path.read_text(encoding="utf-8", errors="replace")
    # The base revision is the last bare hash in the file; earlier lines record
    # the vendoring command and a timestamp.
    hashes = re.findall(r"\b([0-9a-f]{7,40})\b", text)
    if not hashes:
        return None, "none", None
    revision, kind = classify_revision(hashes[-1])
    return revision, kind, "third_party/libwebrtc/README.mozilla.last-vendor"


def _revision_in_tree(root):
    return "in-tree", "in-tree", "in-tree crate (no vendored revision)"


REVISION_FALLBACKS = {
    "README_MOZILLA": _revision_from_readme_mozilla,
    "README.mozilla.last-vendor": _revision_from_last_vendor,
    "Cargo.toml": _revision_in_tree,
}


# --------------------------------------------------------------------------
# Bugzilla component
# --------------------------------------------------------------------------


def _glob_matches(glob, relative):
    """Match a ``with Files(...)`` glob against a path relative to moz.build."""
    if glob in ("**", "*"):
        return True
    if glob.endswith("/**"):
        prefix = glob[:-3]
        return relative == prefix or relative.startswith(prefix + "/")
    return fnmatch.fnmatch(relative, glob)


def _scan_moz_build(path, relative):
    """Best (longest-glob) BUG_COMPONENT in one moz.build for ``relative``."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    best = None
    current_glob = None
    for line in text.splitlines():
        match = WITH_FILES_RE.match(line)
        if match:
            current_glob = match.group(1)
            continue
        found = BUG_COMPONENT_RE.search(line)
        if found and current_glob and _glob_matches(current_glob, relative):
            score = len(current_glob)
            if best is None or score > best[0]:
                best = (score, found.group(1), found.group(2))
    return best[1:] if best else None


def resolve_bug_component(root, tree_path):
    """Walk up from ``tree_path`` looking for a BUG_COMPONENT that applies."""
    directory = (root / tree_path).resolve()
    for parent in [directory, *directory.parents]:
        if root not in parent.parents and parent != root:
            continue
        moz_build = parent / "moz.build"
        if moz_build.is_file():
            relative = (
                str(directory.relative_to(parent)) if directory != parent else "."
            )
            hit = _scan_moz_build(moz_build, "" if relative == "." else relative)
            if hit:
                source = str(moz_build.relative_to(root))
                return hit[0], hit[1], source
        if parent == root:
            break
    return None, None, None


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


def collect(library_id, root=None):
    """Build a :class:`LibraryFacts` for one library id."""
    lib = channel_policy.LIBRARIES.get(library_id)
    if lib is None:
        raise KeyError(library_id)

    facts = LibraryFacts(
        library_id=lib.id,
        has_upstream=lib.has_upstream,
        channels=lib.channels,
        profile=lib.channels[0],
        intake=lib.intake,
        cc_external=lib.cc_external,
        notes=lib.notes,
        repo_url=lib.repo_url,
        forge=lib.forge,
    )
    warnings = []

    if root is None:
        facts.warnings = ("no Firefox checkout found; policy data only",)
        return facts
    facts.tree_root = str(root)

    if lib.moz_yaml and (root / lib.moz_yaml).is_file():
        data = parse_moz_yaml(root / lib.moz_yaml)
        facts.moz_yaml = lib.moz_yaml
        facts.origin_name = data.get("origin.name")
        facts.homepage_url = data.get("origin.url")
        if lib.has_upstream:
            # origin.url is the project homepage for about half of these
            # libraries (libjpeg-turbo.org, xiph.org/ogg, ...), so permalinks
            # must come from vendoring.url.
            facts.repo_url = (
                lib.repo_url or data.get("vendoring.url") or data.get("origin.url")
            )
            facts.forge = lib.forge or data.get("vendoring.source-hosting")
        facts.vendor_dir = data.get("vendoring.vendor-directory") or lib.paths[0]
        facts.bug_product = data.get("bugzilla.product")
        facts.bug_component = data.get("bugzilla.component")
        if facts.bug_component:
            facts.bug_component_source = lib.moz_yaml

        revision, kind = classify_revision(data.get("origin.revision"))
        if revision:
            facts.revision, facts.revision_kind = revision, kind
            facts.revision_source = lib.moz_yaml
        else:
            revision, kind = classify_revision(data.get("origin.release"))
            if revision:
                facts.revision, facts.revision_kind = revision, kind
                facts.revision_source = f"{lib.moz_yaml} (release:, no revision:)"
    elif lib.moz_yaml:
        warnings.append(
            f"{lib.moz_yaml} is recorded in policy but missing from the tree"
        )

    if facts.revision is None and lib.revision_source in REVISION_FALLBACKS:
        revision, kind, source = REVISION_FALLBACKS[lib.revision_source](root)
        facts.revision, facts.revision_kind, facts.revision_source = (
            revision,
            kind,
            source,
        )
        if revision is None:
            warnings.append(f"could not read a revision from {lib.revision_source}")

    if facts.revision is None and lib.has_upstream:
        warnings.append("vendored revision is not recorded in-tree; do not invent one")

    if facts.vendor_dir is None:
        facts.vendor_dir = lib.paths[0]

    if not facts.bug_component:
        product, component, source = resolve_bug_component(root, lib.paths[0])
        if component:
            facts.bug_product, facts.bug_component = product, component
            facts.bug_component_source = source
        else:
            facts.bug_product, facts.bug_component = "Core", "Audio/Video"
            facts.bug_component_source = "assumed — verify with ./mach file-info"
            warnings.append("Bugzilla component assumed; verify before filing")

    patch_dir = root / (os.path.dirname(lib.moz_yaml) if lib.moz_yaml else lib.paths[0])
    if patch_dir.is_dir():
        facts.local_patches = tuple(sorted(p.name for p in patch_dir.glob("*.patch")))

    facts.warnings = tuple(warnings)
    return facts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--library", help="library id (see --list)")
    parser.add_argument("--path", help="tree path to resolve to a library id")
    parser.add_argument("--firefox", help="checkout root (default: walk up from cwd)")
    parser.add_argument("--list", action="store_true", help="list known library ids")
    parser.add_argument(
        "--all", action="store_true", help="emit facts for every library"
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.list:
        for name in sorted(channel_policy.LIBRARIES):
            print(name)
        return 0

    root = find_checkout(args.firefox)
    if root is None and not args.json:
        print("WARNING: no Firefox checkout found; emitting policy data only")

    if args.all:
        targets = sorted(channel_policy.LIBRARIES)
    else:
        token = args.library or args.path
        library_id, note = channel_policy.resolve_library(token)
        if library_id is None:
            print(f"ERROR: {note}", file=sys.stderr)
            print(
                "Known ids: " + ", ".join(sorted(channel_policy.LIBRARIES)),
                file=sys.stderr,
            )
            return 2
        targets = [library_id]

    results = [collect(name, root) for name in targets]

    if args.json:
        payload = [dataclasses.asdict(f) for f in results]
        print(json.dumps(payload if args.all else payload[0], indent=2, sort_keys=True))
        return 0

    for facts in results:
        print(f"library:    {facts.library_id}")
        print(
            f"revision:   {facts.revision} ({facts.revision_kind}) <- {facts.revision_source}"
        )
        print(f"repo:       {facts.repo_url} [{facts.forge}]")
        print(f"vendor dir: {facts.vendor_dir}")
        print(
            f"bugzilla:   {facts.bug_product} :: {facts.bug_component} <- {facts.bug_component_source}"
        )
        print(f"channels:   {', '.join(facts.channels)}")
        print(f"intake:     {facts.intake}")
        if facts.cc_external:
            print(f"cc:         {', '.join(facts.cc_external)}")
        if facts.local_patches:
            print(f"patches:    {', '.join(facts.local_patches)}")
        if facts.notes:
            print(f"notes:      {facts.notes}")
        for warning in facts.warnings:
            print(f"WARNING:    {warning}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
