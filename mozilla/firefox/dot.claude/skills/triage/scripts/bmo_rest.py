#!/usr/bin/env python3
"""Stdlib REST wrapper for bugzilla.mozilla.org.

Auth uses an API key sent in the ``X-BUGZILLA-API-KEY`` header. The key
is discovered from $BMO_API_KEY first, then ~/.config/bmo/api_key, and
is never echoed in logs or exception reprs.

Anonymous reads of public bugs work without a key. Write helpers
require a key and raise BMOError("API key required for writes") before
hitting the network if one isn't supplied.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BMO_BASE = "https://bugzilla.mozilla.org/rest"
API_KEY_HEADER = "X-BUGZILLA-API-KEY"
USER_AGENT = "firefox-triage-skill/1 (mozilla)"
DEFAULT_TIMEOUT = 30.0

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class BMOError(Exception):
    """REST call failed.

    Attributes:
      status_code: HTTP status (0 for network errors).
      body:        Parsed JSON body or raw text.
      retry_after: Float seconds from a Retry-After header, or None.
    """

    def __init__(self, message, status_code=0, body=None, retry_after=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.retry_after = retry_after

    def __repr__(self):
        return "BMOError(status={}, retry_after={}, msg={!r})".format(
            self.status_code, self.retry_after, str(self)
        )


# ---------------------------------------------------------------------------
# API key discovery
# ---------------------------------------------------------------------------


def get_api_key():
    """Return the API key from env var or config file, else None.

    Resolution order:
      1. $BMO_API_KEY
      2. ~/.config/bmo/api_key (single line)
      3. None
    """
    key = os.environ.get("BMO_API_KEY")
    if key:
        return key.strip()

    path = os.path.join(os.path.expanduser("~"), ".config", "bmo", "api_key")
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return None
    except OSError as e:
        sys.stderr.write("bmo_rest: cannot stat {}: {}\n".format(path, e))
        return None

    if st.st_mode & 0o077:
        sys.stderr.write(
            "bmo_rest: warning — {} is group/world readable; "
            "chmod 600 recommended\n".format(path)
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.readline().strip() or None
    except OSError as e:
        sys.stderr.write("bmo_rest: cannot read {}: {}\n".format(path, e))
        return None


def _redact(headers):
    """Return a copy of headers with the API key value masked."""
    safe = {}
    for k, v in (headers or {}).items():
        if k.lower() == API_KEY_HEADER.lower():
            safe[k] = "***redacted***"
        else:
            safe[k] = v
    return safe


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------


def _build_url(path, params=None):
    """Join BMO_BASE + path, encode params. ``path`` may be absolute or rel."""
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        url = BMO_BASE + (path if path.startswith("/") else "/" + path)
    if params:
        # Drop None values so callers can pass kwargs cleanly.
        clean = [(k, v) for (k, v) in params.items() if v is not None]
        if clean:
            url = (
                url
                + ("&" if "?" in url else "?")
                + urllib.parse.urlencode(clean, doseq=True)
            )
    return url


def _request(
    method, path, params=None, body=None, api_key=None, timeout=DEFAULT_TIMEOUT
):
    """Issue one REST call. Returns parsed JSON dict.

    Raises BMOError on non-2xx or transport failure. The API key is sent
    in a header (never the URL) and is redacted from any error path.
    """
    url = _build_url(path, params)
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if api_key:
        headers[API_KEY_HEADER] = api_key

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return json.loads(raw) if raw else {}
            except (json.JSONDecodeError, ValueError) as e:
                raise BMOError(
                    "non-JSON response from {} {}: {}".format(method, path, e),
                    status_code=resp.status,
                    body=raw,
                )
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover - defensive
            pass
        body_parsed = body_text
        try:
            body_parsed = json.loads(body_text)
        except (json.JSONDecodeError, ValueError):
            pass
        retry_after = None
        ra = e.headers.get("Retry-After") if e.headers else None
        if ra:
            try:
                retry_after = float(ra)
            except (TypeError, ValueError):
                retry_after = None
        raise BMOError(
            "{} {} failed: HTTP {}".format(method, path, e.code),
            status_code=e.code,
            body=body_parsed,
            retry_after=retry_after,
        )
    except urllib.error.URLError as e:
        raise BMOError(
            "{} {} transport error: {}".format(method, path, e.reason),
            status_code=0,
        )


def _require_key(api_key):
    if not api_key:
        raise BMOError("API key required for writes", status_code=0)


# ---------------------------------------------------------------------------
# Read helpers
# ---------------------------------------------------------------------------


def get_bug(bug_id, api_key=None, timeout=DEFAULT_TIMEOUT):
    """GET /bug/{id}. Returns the first bug dict from the response."""
    resp = _request(
        "GET", "/bug/{}".format(int(bug_id)), api_key=api_key, timeout=timeout
    )
    bugs = resp.get("bugs") or []
    if not bugs:
        raise BMOError(
            "bug {} not found or inaccessible".format(bug_id),
            status_code=404,
            body=resp,
        )
    return bugs[0]


def get_bug_history(bug_id, api_key=None, timeout=DEFAULT_TIMEOUT):
    """GET /bug/{id}/history. Returns the raw response dict."""
    return _request(
        "GET", "/bug/{}/history".format(int(bug_id)), api_key=api_key, timeout=timeout
    )


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


def post_comment(bug_id, comment, api_key, is_private=False, timeout=DEFAULT_TIMEOUT):
    """POST /bug/{id}/comment. Returns the response dict."""
    _require_key(api_key)
    body = {"comment": comment, "is_private": bool(is_private)}
    return _request(
        "POST",
        "/bug/{}/comment".format(int(bug_id)),
        body=body,
        api_key=api_key,
        timeout=timeout,
    )


def set_fields(bug_id, fields, api_key, timeout=DEFAULT_TIMEOUT):
    """PUT /bug/{id} bundling field changes.

    Accepted ``fields`` keys (all optional):
      priority, severity, status, resolution, dupe_of,
      product, component,
      keywords / cc / blocks / see_also  — pass as {"add": [...], "remove": [...]}.
    Unknown keys are forwarded as-is so callers can use less-common fields.
    """
    _require_key(api_key)
    if not fields:
        raise ValueError("set_fields: no fields supplied")
    return _request(
        "PUT",
        "/bug/{}".format(int(bug_id)),
        body=dict(fields),
        api_key=api_key,
        timeout=timeout,
    )


def set_needinfo(bug_id, requestee, api_key, timeout=DEFAULT_TIMEOUT):
    """PUT /bug/{id} with a needinfo flag for the requestee."""
    _require_key(api_key)
    body = {"flags": [{"name": "needinfo", "status": "?", "requestee": requestee}]}
    return _request(
        "PUT",
        "/bug/{}".format(int(bug_id)),
        body=body,
        api_key=api_key,
        timeout=timeout,
    )
