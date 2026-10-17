#!/usr/bin/env python3
"""git-restack — fast-forward a base branch from its upstream, then rebase
the branches stacked on top of it.

Installed as `git-restack` on PATH, so it runs as `git restack`.

The base (default: the remote's default branch, else main/master) is
fast-forwarded from the remote named `upstream` if there is one (even when
the base tracks a fork), else from what it tracks. Then every *layer*
(long-lived branches kept on top of the base, configured per repository;
none by default) and every requested branch (default: the current one)
is rebased onto the fresh tip of its parent. Parents are detected *before* anything moves:
a branch containing any commit a layer ever pointed at (its reflog, like
`git rebase --fork-point`) was built on that layer, so it still finds the
layer after the layer was rewritten and is moved with
`--onto <new parent> <old fork point>`. The stale layer commits are not
replayed.

Reflogs expire and vanish with a deleted branch, so each run also notes
in .git/restack-tips the layers' tips and where each branch was placed,
and consults those too. An entry is dropped as soon as no other local
branch still contains it, so the file tracks live branches, not time;
deleting it is always safe. A branch placed on the base that
carries a commit titled like a layer's gets a warning with the command
to move it by hand.

Only the current branch gets a real `git rebase`. Branches that are not
checked out anywhere are rebased in memory with `git merge-tree` (git >=
2.40), so the working tree is touched once, not once per branch. Branches
checked out in another worktree are rebased there if that worktree is
clean.

Configuration (per repository, all optional):
    restack.base      base branch (default: what upstream/HEAD or
                      origin/HEAD points to, else main, else master)
    restack.upstream  <remote>[/<branch>] the base is fast-forwarded to
                      (default: upstream/<base> once fetched, else what
                      the base tracks, else origin/<base>)
    restack.layer     multi-valued; branches always rebased onto the base
    restack.push      true / false / <remote>: push the base after updating
"""

import argparse
import os
import re
import subprocess
import sys

USAGE = """git restack [<options>] [<branch>...]"""

EPILOG = """\
With no <branch>, the current branch is restacked. Stacks among the given
branches (A on B on a layer) are detected, so name them all to move them
together.

examples:
  git restack                  update the base, rebase layers and current branch
  git restack --push           ... and push the base to <base>@{push}
  git restack --push=origin    ... and push the base to origin
  git restack A B              restack branches A and B as well as the layers
  git restack -n               show the plan without changing anything

optional per-repository setup, e.g. a fork with branches kept on main:
  git config restack.base main
  git config --add restack.layer my-local-tweaks
  git config restack.push origin
"""

# `git merge-tree --write-tree --merge-base` landed in 2.40.
MIN_MERGE_TREE_VERSION = (2, 40)


class RestackError(Exception):
    """A failure that should stop the run with a message, not a traceback."""


# ---------------------------------------------------------------------------
# git plumbing
# ---------------------------------------------------------------------------


def git(*args, cwd=None, check=True, env=None, input=None):
    """Run git and return its stripped stdout. Raises RestackError on failure."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        input=input,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    if check and result.returncode != 0:
        raise RestackError(
            "git {} failed:\n{}".format(" ".join(args), result.stderr.strip())
        )
    return result.stdout.strip() if check else result


def git_ok(*args, cwd=None):
    """Return True when the git command exits 0 (output discarded)."""
    return git(*args, cwd=cwd, check=False).returncode == 0


def run(*args, cwd=None):
    """Run a git command that changes state, echoing it. Returns True on success."""
    where = " (in {})".format(cwd) if cwd else ""
    print("+ git {}{}".format(" ".join(args), where), flush=True)
    return subprocess.run(["git", *args], cwd=cwd).returncode == 0


def git_version():
    out = git("version")
    match = re.search(r"(\d+)\.(\d+)", out)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def current_branch():
    return git("symbolic-ref", "--short", "-q", "HEAD", check=False).stdout.strip()


def rev(ref):
    return git("rev-parse", "--verify", "--quiet", ref + "^{commit}")


def ref_exists(ref):
    return git_ok("show-ref", "--verify", "--quiet", ref)


def branch_exists(name):
    return ref_exists("refs/heads/" + name)


def config_get(key):
    result = git("config", "--get", key, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def config_get_all(key):
    result = git("config", "--get-all", key, check=False)
    return result.stdout.split() if result.returncode == 0 else []


def worktree_branches():
    """Map each checked-out branch to the worktree path holding it."""
    branches = {}
    path = None
    for line in git("worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree ") :]
        elif line.startswith("branch refs/heads/"):
            branches[line[len("branch refs/heads/") :]] = path
    return branches


def operation_in_progress(cwd=None):
    """Name the rebase/merge/cherry-pick left half-done in a worktree, if any."""
    markers = {
        "rebase-merge": "rebase",
        "rebase-apply": "rebase",
        "MERGE_HEAD": "merge",
        "CHERRY_PICK_HEAD": "cherry-pick",
        "REVERT_HEAD": "revert",
    }
    for marker, name in markers.items():
        path = git("rev-parse", "--git-path", marker, cwd=cwd)
        if not os.path.isabs(path):
            path = os.path.join(cwd or os.getcwd(), path)
        if os.path.exists(path):
            return name
    return None


def is_dirty(cwd=None):
    """Tracked changes only; untracked files never block a rebase."""
    return bool(git("status", "--porcelain", "--untracked-files=no", cwd=cwd))


# ---------------------------------------------------------------------------
# Argument resolution
# ---------------------------------------------------------------------------


def split_remote_ref(value, remotes):
    """Split `<remote>/<branch>` using the known remote names.

    Branch names may contain slashes, so the longest matching remote wins.
    A bare remote name yields (remote, None).
    """
    for remote in sorted(remotes, key=len, reverse=True):
        if value == remote:
            return remote, None
        if value.startswith(remote + "/"):
            return remote, value[len(remote) + 1 :]
    return None, None


def default_base(remotes):
    """The branch a remote calls its default (`<remote>/HEAD`, which clone
    sets), else main, else master. `upstream` and `origin` are asked first."""
    preferred = [r for r in ("upstream", "origin") if r in remotes]
    for remote in preferred + [r for r in remotes if r not in preferred]:
        head = git(
            "symbolic-ref",
            "--short",
            "-q",
            "refs/remotes/{}/HEAD".format(remote),
            check=False,
        ).stdout.strip()
        name = head[len(remote) + 1 :] if head.startswith(remote + "/") else ""
        if name and branch_exists(name):
            return name
    for name in ("main", "master"):
        if branch_exists(name):
            return name
    return None


def tracking_branch(base):
    """The (remote, branch) `base` tracks, or None (unset or a local branch)."""
    remote = config_get("branch.{}.remote".format(base))
    merge = config_get("branch.{}.merge".format(base))
    if remote and merge and remote != ".":
        return remote, re.sub(r"^refs/heads/", "", merge)
    return None


def resolve_upstream(arg, base, remotes):
    """Return (remote, branch) the base is fast-forwarded to.

    --upstream, else restack.upstream, else the tracking branch, else
    `upstream` then `origin` with the base's name. A remote named `upstream`
    (the fork convention, as in default_base()) beats a tracking branch on
    another remote: cloning a fork leaves the base tracking the fork, which
    nobody syncs, so following it restacks onto a stale base and calls it
    up to date. Only once `upstream/<base>` has been fetched, since the
    upstream may name the branch differently.
    """
    source = "--upstream"
    if not arg:
        arg = config_get("restack.upstream")
        source = "restack.upstream"
    if arg:
        remote, branch = split_remote_ref(arg, remotes)
        if remote is None:
            raise RestackError(
                "{} {!r}: not <remote>/<branch> for any remote ({})".format(
                    source, arg, ", ".join(remotes) or "none configured"
                )
            )
        return remote, branch or base

    tracked = tracking_branch(base)
    if (
        tracked
        and tracked[0] != "upstream"
        and "upstream" in remotes
        and ref_exists("refs/remotes/upstream/" + base)
    ):
        return "upstream", base  # the base tracks a fork
    if tracked:
        return tracked
    # No tracking branch: prefer `upstream`, then `origin`, same branch name.
    for remote in ("upstream", "origin"):
        if remote in remotes:
            return remote, base
    raise RestackError(
        "{0} has no upstream; pass --upstream <remote>/<branch> or run\n"
        "  git branch --set-upstream-to=<remote>/{0} {0}".format(base)
    )


def parse_bool_or_remote(value):
    """restack.push is a git bool or a remote name. Returns None/""/remote."""
    lowered = value.lower()
    if lowered in ("true", "yes", "on", "1"):
        return ""
    if lowered in ("false", "no", "off", "0", ""):
        return None
    return value


def push_destination(base, upstream):
    """Where a plain `git push` from `base` goes, i.e. <base>@{push}.

    Worked out from config rather than `rev-parse <base>@{push}`, which
    fails until the remote-tracking ref exists (a fork never fetched).
    """
    remote = (
        config_get("branch.{}.pushRemote".format(base))
        or config_get("remote.pushDefault")
        or config_get("branch.{}.remote".format(base))
    )
    if not remote or remote == ".":
        return None
    mode = config_get("push.default") or "simple"
    if mode == "upstream" and remote == upstream[0]:
        return remote, upstream[1]
    return remote, base


def resolve_push(arg, base, upstream, remotes):
    """Return (remote, branch) to push the base to, or None to skip pushing.

    `arg` is None (unspecified), False (--no-push), "" (--push) or a remote.
    """
    if arg is None:
        configured = config_get("restack.push")
        arg = parse_bool_or_remote(configured) if configured is not None else False
    if arg is None or arg is False:
        return None

    if arg:
        remote, branch = split_remote_ref(arg, remotes)
        if remote is None:
            raise RestackError("--push={}: no such remote".format(arg))
        target = (remote, branch or base)
    else:
        target = push_destination(base, upstream)
        if target is None:
            raise RestackError(
                "cannot work out where {}@{{push}} goes; use --push=<remote>".format(
                    base
                )
            )

    if target == upstream:
        # Pushing back to the branch we just pulled from is either a no-op or,
        # far more likely, a misconfiguration (main@{push} falls back to
        # branch.main.remote when remote.pushDefault is unset).
        others = [r for r in remotes if r != target[0]]
        fork = "origin" if "origin" in others else (others or ["<remote>"])[0]
        raise RestackError(
            "refusing to push {0} to its own upstream {1}/{2}.\n"
            "Use --push=<remote>, or point {0}@{{push}} elsewhere:\n"
            "  git config remote.pushDefault {3}".format(base, *target, fork)
        )
    return target


# ---------------------------------------------------------------------------
# Remembered tips (.git/restack-tips)
# ---------------------------------------------------------------------------

TIPS_FILE = "restack-tips"
TIPS_HEADER = (
    "# git restack: <sha> <branch> [<dependent>]: <sha> was a tip of <branch>\n"
    "# (that <dependent> was placed on). Used to find what an old branch was\n"
    "# built on once reflogs are gone. Self-pruning; safe to delete.\n"
)


def tips_path():
    """The record lives in the common git dir, so all worktrees share it."""
    return os.path.join(
        os.path.abspath(git("rev-parse", "--git-common-dir")), TIPS_FILE
    )


def load_record(path):
    """Read the record as [(sha, branch, dependent or None)]. Missing is empty."""
    entries = []
    try:
        with open(path) as f:
            for line in f:
                parts = line.split()
                if line.startswith("#") or len(parts) not in (2, 3):
                    continue
                entries.append(
                    (parts[0], parts[1], parts[2] if len(parts) == 3 else None)
                )
    except OSError:
        pass
    return list(dict.fromkeys(entries))


def save_record(path, entries, base):
    """Write `entries` back, dropping the ones no branch needs any more.

    An entry is kept while its sha is still its branch's tip, or while some
    local branch other than that one and the base contains it, i.e. while
    a branch may still be sitting on that old version. The base is
    excluded because ancestry of the base is found without the record.
    """
    heads = {}
    for line in git(
        "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"
    ).splitlines():
        ref, sha = line.split(" ", 1)
        heads[ref] = sha

    containers = {}

    def needed(sha, branch):
        if heads.get("refs/heads/" + branch) == sha:
            return True
        if sha not in containers:
            result = git(
                "for-each-ref",
                "--contains",
                sha,
                "--format=%(refname)",
                "refs/heads",
                check=False,
            )
            # A failure means the commit itself is gone.
            containers[sha] = (
                set(result.stdout.split()) if result.returncode == 0 else set()
            )
        return bool(containers[sha] - {"refs/heads/" + branch, "refs/heads/" + base})

    kept = [
        " ".join(field for field in entry if field) + "\n"
        for entry in dict.fromkeys(entries)
        if needed(entry[0], entry[1])
    ]
    if not kept:
        if os.path.exists(path):
            os.remove(path)
        return
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(TIPS_HEADER)
        f.writelines(kept)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Stack detection
# ---------------------------------------------------------------------------


def layer_tips(layer, record):
    """Every commit `layer` is known to have pointed at: reflog plus record."""
    result = git("reflog", "show", "--format=%H", "refs/heads/" + layer, check=False)
    shas = result.stdout.split() if result.returncode == 0 else []
    return shas + [sha for sha, branch, _ in record if branch == layer]


def detect_parents(base, layers, targets, tips, record):
    """Map each layer/target to (parent, old fork point on that parent).

    Candidates are the base, the layers, and (for targets) the other
    targets. What counts as "the branch sits on this candidate at X":

      base    X = merge-base. The base only fast-forwards.
      layer   X = any commit the layer ever pointed at (current tip,
              reflog, record) that the branch contains. Layers are not
              made from feature branches, so a former layer tip inside the
              branch means it was built on that layer, even after the layer
              was rewritten, deleted or recreated.
      target  X = its current tip, or where restack last placed this branch
              on it (record). Never its reflog: `git checkout -b b a`
              writes a's tip into b's reflog, so a reflog cannot tell
              "b was made from a" from "a was made from b".

    The parent is the candidate with the deepest X. Ties go to the
    lower-ranked candidate (base, then layers, then targets in order),
    because a tie means the higher one contributes no commits. A candidate
    that currently contains the branch can only be its parent when both
    point at the same commit, and only if it ranks lower, which keeps the
    result acyclic.
    """
    rank = {name: i for i, name in enumerate([base, *layers, *targets])}
    known = {layer: layer_tips(layer, record) for layer in layers}
    parents = {}
    for branch in [*layers, *targets]:
        pool = [base, *layers] + (targets if branch in targets else [])
        base_mb = git("merge-base", tips[base], tips[branch])
        span = "{}..{}".format(base_mb, tips[branch])
        reachable = set(git("rev-list", span).split())
        best = (0, -rank[base]), base, base_mb
        for candidate in pool:
            if candidate in (base, branch):
                continue
            if tips[candidate] == tips[branch]:
                if rank[candidate] > rank[branch]:
                    continue
            elif git_ok("merge-base", "--is-ancestor", tips[branch], tips[candidate]):
                continue
            if candidate in known:
                shas = known[candidate]
            else:
                shas = [s for s, b, d in record if b == candidate and d == branch]
            for point in dict.fromkeys([tips[candidate], *shas]):
                if point not in reachable:
                    continue
                span = "{}..{}".format(base_mb, point)
                key = (int(git("rev-list", "--count", span)), -rank[candidate])
                if key > best[0]:
                    best = (key, candidate, point)
        parents[branch] = (best[1], best[2])
    return parents


def lookalike_warnings(base, layers, parents, tips):
    """Warn about branches carrying a commit titled like a layer's commit
    while placed on something other than that layer.

    That is the signature of a branch built on a layer version that neither
    the reflog nor the record knows about: it will be restacked with its
    stale copy of the layer commit. Detection is left alone; the warning
    says how to move the branch by hand.
    """
    subjects = {
        layer: set(git("log", "--format=%s", "{}..{}".format(base, layer)).splitlines())
        for layer in layers
    }
    warnings = []
    for branch, (parent, point) in parents.items():
        own = git("log", "--format=%h %s", "{}..{}".format(point, tips[branch]))
        own = [line.split(" ", 1) for line in own.splitlines() if " " in line]
        for layer in layers:
            if layer in (parent, branch):
                continue
            # git log is newest first: the first match is the topmost copy.
            match = next((c for c in own if c[1] in subjects[layer]), None)
            if match:
                warnings.append(
                    'warning: {0} sits on {1} but has commit {2} "{3}", like '
                    "layer {4}.\n  If it was built on an older {4}, move it after "
                    "this run with:\n    git rebase --onto {4} {2} {0}".format(
                        branch, parent, match[0], match[1], layer
                    )
                )
    return warnings


def restack_order(parents, rank, deferred):
    """Topologically order branches, parents first, `deferred` ones as late as possible."""
    order = []
    pending = list(parents)
    while pending:
        ready = [b for b in pending if parents[b][0] not in pending]
        if not ready:
            raise RestackError("branches form a cycle: {}".format(", ".join(pending)))
        ready.sort(key=lambda b: (b in deferred, rank[b]))
        order.append(ready[0])
        pending.remove(ready[0])
    return order


# ---------------------------------------------------------------------------
# Rebasing without a checkout
# ---------------------------------------------------------------------------


AUTHOR_RE = re.compile(r"^author (.*) <(.*)> (\d+) ([+-]\d{4})$", re.MULTILINE)


def recommit(commit, tree, parent):
    """Create a copy of `commit` with a new tree and parent, as rebase would."""
    raw = git("cat-file", "commit", commit)
    headers, _, message = raw.partition("\n\n")
    author = AUTHOR_RE.search(headers)
    env = dict(os.environ)
    env.update(
        GIT_AUTHOR_NAME=author.group(1),
        GIT_AUTHOR_EMAIL=author.group(2),
        GIT_AUTHOR_DATE="@{} {}".format(author.group(3), author.group(4)),
    )
    # `git` strips the output; commit-tree reads the message verbatim from stdin.
    return git("commit-tree", tree, "-p", parent, env=env, input=message + "\n")


def tree_of(commit):
    return git("rev-parse", commit + "^{tree}")


def replay_in_memory(old_base, tip, onto):
    """Replay old_base..tip onto `onto` with merge-tree. Returns the new tip.

    Mirrors `git rebase` defaults: commits that become empty are dropped,
    commits that were empty to begin with are kept. Raises RestackError on
    a conflict or a merge commit, leaving every ref untouched.
    """
    span = "{}..{}".format(old_base, tip)
    if git("rev-list", "--min-parents=2", span):
        raise RestackError("contains merge commits")
    head = onto
    for commit in git("rev-list", "--reverse", "--topo-order", span).split():
        result = git(
            "merge-tree",
            "--write-tree",
            "--merge-base",
            commit + "^",
            head,
            commit,
            check=False,
        )
        if result.returncode != 0:
            subject = git("log", "-1", "--format=%h %s", commit)
            raise RestackError("conflict replaying {}".format(subject))
        tree = result.stdout.split("\n", 1)[0].strip()
        was_empty = tree_of(commit) == tree_of(commit + "^")
        if tree == tree_of(head) and not was_empty:
            continue
        head = recommit(commit, tree, head)
    return head


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="git restack",
        usage=USAGE,
        description=(
            "Fast-forward the base branch from its upstream, then rebase the "
            "layers and the given branches (default: current) onto it."
        ),
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "branches", nargs="*", metavar="<branch>", help="branches to restack"
    )
    parser.add_argument(
        "--base",
        metavar="<branch>",
        help="branch to fast-forward (default: restack.base, else the "
        "remote's default branch, else main or master)",
    )
    parser.add_argument(
        "-u",
        "--upstream",
        metavar="<remote>[/<branch>]",
        help="where the base comes from (default: restack.upstream, else "
        "upstream/<base> if fetched, else <base>@{upstream}, else origin)",
    )
    parser.add_argument(
        "-l",
        "--layer",
        action="append",
        metavar="<branch>",
        help="branch kept on top of the base; repeatable, replaces restack.layer",
    )
    parser.add_argument("--no-layers", action="store_true", help="ignore restack.layer")
    push = parser.add_mutually_exclusive_group()
    push.add_argument(
        "--push",
        nargs="?",
        const="",
        metavar="<remote>",
        help="push the base to <remote> (written --push=<remote>), "
        "or to <base>@{push} (default: restack.push)",
    )
    push.add_argument(
        "--no-push", dest="push", action="store_false", help="do not push"
    )
    parser.add_argument(
        "--autostash",
        action="store_true",
        help="stash local changes around rebasing the current branch",
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="show the plan, change nothing"
    )
    parser.set_defaults(push=None)
    return parser


def normalize_argv(argv):
    """Make `--push` take a value only as `--push=<remote>`, like git's own
    optional-value flags, so `git restack --push topic` restacks `topic`."""
    out = []
    for arg in argv:
        if arg == "--push":
            out.append("--push=")
        else:
            out.append(arg)
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(normalize_argv(argv))

    if git("rev-parse", "--is-inside-work-tree", check=False).stdout.strip() != "true":
        raise RestackError("not inside a git working tree")

    toplevel = git("rev-parse", "--show-toplevel")
    current = current_branch()
    remotes = git("remote").split()
    base = args.base or config_get("restack.base") or default_base(remotes)
    if not base:
        raise RestackError(
            "cannot tell which branch is the base. Pass --base <branch>, or:\n"
            "  git config restack.base <branch>\n"
            "  git remote set-head origin --auto   # records origin's default"
        )
    if not branch_exists(base):
        raise RestackError("base branch {!r} does not exist".format(base))

    if args.no_layers:
        layers = []
    elif args.layer:
        layers = args.layer
    else:
        layers = config_get_all("restack.layer")
    missing = [b for b in layers if not branch_exists(b)]
    for name in missing:
        print("warning: layer {!r} does not exist; skipping".format(name))
    layers = [b for b in dict.fromkeys(layers) if b not in missing and b != base]

    targets = args.branches or ([current] if current else [])
    for name in targets:
        if not branch_exists(name):
            raise RestackError("no such branch: {}".format(name))
    targets = [b for b in dict.fromkeys(targets) if b != base and b not in layers]

    upstream = resolve_upstream(args.upstream, base, remotes)
    push_target = resolve_push(args.push, base, upstream, remotes)

    in_progress = operation_in_progress()
    if in_progress:
        raise RestackError(
            "a {} is in progress here; finish or abort it first".format(in_progress)
        )

    tips = {b: rev(b) for b in [base, *layers, *targets]}
    record_path = tips_path()
    record = load_record(record_path)
    parents = detect_parents(base, layers, targets, tips, record)
    worktrees = worktree_branches()
    here = {
        b
        for b, path in worktrees.items()
        if os.path.exists(path) and os.path.samefile(path, toplevel)
    }
    rank = {name: i for i, name in enumerate([base, *layers, *targets])}
    order = restack_order(parents, rank, deferred=here)
    in_memory = git_version() >= MIN_MERGE_TREE_VERSION

    print("==> Plan")
    print("  {} <- {}/{}".format(base, *upstream))
    tracked = tracking_branch(base)
    chosen = args.upstream or config_get("restack.upstream")
    if tracked and tracked != upstream and not chosen:
        print(
            "  note: {} tracks {}/{}; set restack.upstream to use that "
            "instead".format(base, *tracked)
        )
    for branch in order:
        parent, point = parents[branch]
        print(
            "  {} onto {}  (forked at {})".format(
                branch, parent, git("rev-parse", "--short", point)
            )
        )
    if push_target:
        print("  push {} -> {}/{}".format(base, *push_target))
    for warning in lookalike_warnings(base, layers, parents, tips):
        print(warning)

    # Refuse before the base moves. After the plan, so -n still shows it.
    dirty = is_dirty()
    if dirty and not args.autostash and any(b in here for b in order):
        raise RestackError(
            "{} has local changes; commit or stash them, or pass --autostash".format(
                current
            )
        )
    if dirty and not in_memory and any(b not in worktrees for b in order):
        raise RestackError(
            "git < 2.40 must check out each branch to rebase it; "
            "commit or stash local changes first"
        )
    if args.dry_run:
        return 0

    # Note where everything sits before it moves: each layer's tip, and
    # each branch's place on a non-base parent. Saved even if the run fails.
    entries = record + [(tips[layer], layer, None) for layer in layers]
    entries += [(pt, par, b) for b, (par, pt) in parents.items() if par != base]
    try:
        # 1. Fast-forward the base. update-ref works whether or not it is
        # checked out somewhere, but a checked-out base needs its worktree
        # moved too.
        print("==> Updating {} from {}/{}".format(base, *upstream))
        if not run("fetch", upstream[0], "refs/heads/" + upstream[1]):
            raise RestackError("fetch failed")
        fetched = rev("FETCH_HEAD")
        if not git_ok("merge-base", "--is-ancestor", tips[base], fetched):
            raise RestackError(
                "{} has commits not in {}/{}; cannot fast-forward".format(
                    base, *upstream
                )
            )
        if fetched == tips[base]:
            print("{} is up to date".format(base))
        elif base in worktrees:
            if not run("merge", "--ff-only", fetched, cwd=worktrees[base]):
                raise RestackError("could not fast-forward {}".format(base))
        elif not run(
            "update-ref",
            "-m",
            "restack: fast-forward to {}/{}".format(*upstream),
            "refs/heads/" + base,
            fetched,
            tips[base],
        ):
            raise RestackError("could not update {}".format(base))

        # 2. Push it.
        failed = False
        if push_target:
            print("==> Pushing {} to {}/{}".format(base, *push_target))
            if not run(
                "push",
                push_target[0],
                "refs/heads/{}:refs/heads/{}".format(base, push_target[1]),
            ):
                print("error: push failed; continuing with the rebases")
                failed = True

        # 3. Rebase layers and targets, parents first.
        results = {}
        moved_away = False  # the git < 2.40 fallback checks out other branches
        for branch in order:
            parent, point = parents[branch]
            if results.get(parent, "ok") not in ("ok", "up to date"):
                results[branch] = "skipped: {} was not restacked".format(parent)
                continue
            onto = rev(parent)
            if point == onto:
                results[branch] = "up to date"
                continue
            print("==> Rebasing {} onto {}".format(branch, parent))
            results[branch] = restack_one(
                branch, parent, point, onto, worktrees, here, in_memory, args.autostash
            )
            if results[branch] == "ok" and parent != base:
                entries.append((onto, parent, branch))
            if not in_memory and branch not in worktrees:
                if results[branch] != "ok":
                    moved_away = False  # mid-rebase on another branch; stay there
                    break
                moved_away = True

        if moved_away and current and current_branch() != current:
            run("checkout", current)

        print("==> Summary")
        for branch in order:
            result = results.get(branch, "not reached")
            print("  {:<30} {}".format(branch, result))
            failed = failed or result not in ("ok", "up to date")
        return 1 if failed else 0
    finally:
        try:
            save_record(record_path, entries, base)
        except OSError as e:
            print("warning: could not update {}: {}".format(record_path, e))


def restack_one(branch, parent, point, onto, worktrees, here, in_memory, autostash):
    """Move branch's commits from point..branch onto `onto`. Returns a status."""
    if branch in here:
        # Name the branch: the git < 2.40 fallback may have switched away.
        cmd = ["rebase", "--onto", onto, point, branch]
        if autostash:
            cmd.insert(1, "--autostash")
        if run(*cmd):
            return "ok"
        print(
            "Resolve the conflicts, then `git rebase --continue`, and rerun "
            "`git restack` for any branches stacked on {}.".format(branch)
        )
        return "conflict (rebase in progress here)"

    if branch in worktrees:
        path = worktrees[branch]
        busy = operation_in_progress(path)
        if busy or is_dirty(path):
            return "skipped: worktree {} is {}".format(path, busy or "dirty")
        if run("rebase", "--onto", onto, point, cwd=path):
            return "ok"
        run("rebase", "--abort", cwd=path)
        return "conflict (aborted in {}); rebase it there by hand".format(path)

    if not in_memory:
        if run("rebase", "--onto", onto, point, branch):
            return "ok"
        return "conflict (rebase in progress here)"

    old = rev(branch)
    try:
        new = replay_in_memory(point, old, onto)
    except RestackError as e:
        return "conflict: {}; run `git checkout {} && git rebase --onto {} {}`".format(
            e, branch, parent, git("rev-parse", "--short", point)
        )
    if not run(
        "update-ref",
        "-m",
        "restack: onto {}".format(parent),
        "refs/heads/" + branch,
        new,
        old,
    ):
        return "failed to update ref"
    return "ok"


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RestackError as e:
        sys.stdout.flush()  # keep the plan above the error when piped
        print("error: {}".format(e), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
