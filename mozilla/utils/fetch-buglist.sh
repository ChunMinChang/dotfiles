#!/usr/bin/env bash
# Fetch all bugs from a Bugzilla buglist URL into a directory using bmo-to-md.
#
# Usage:
#   fetch-buglist.sh [options] <buglist-url> <output-dir>
#
# The script converts the buglist.cgi URL to a REST API query, extracts all
# bug IDs, then calls bmo-to-md for each one with attachments.
#
# Options:
#   --skip-assigned   Skip bugs assigned to someone (not nobody@mozilla.org)
#   --skip-existing   Skip bugs already fetched in <output-dir>
#   --dry-run         List bug IDs without fetching

set -euo pipefail

skip_assigned=false
skip_existing=false
dry_run=false

usage() {
    echo "Usage: $(basename "$0") [options] <buglist-url> <output-dir>"
    echo
    echo "Fetches all bugs from a Bugzilla buglist URL into <output-dir>."
    echo "Each bug gets its own bmo-<id>/ subdirectory with a markdown"
    echo "summary and downloaded attachments."
    echo
    echo "Options:"
    echo "  --skip-assigned   Skip bugs assigned to someone (not nobody@mozilla.org)"
    echo "  --skip-existing   Skip bugs already fetched in <output-dir>"
    echo "  --dry-run         List bug IDs without fetching"
    echo "  -h, --help        Show this help"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-assigned) skip_assigned=true; shift ;;
        --skip-existing) skip_existing=true; shift ;;
        --dry-run)       dry_run=true; shift ;;
        -h|--help)       usage ;;
        -*)              echo "Unknown option: $1"; usage ;;
        *)               break ;;
    esac
done

if [[ $# -ne 2 ]]; then
    usage
fi

buglist_url="$1"
output_dir="$2"

# Check that bmo-to-md is installed
if ! command -v bmo-to-md &>/dev/null; then
    echo "Error: bmo-to-md is not installed."
    echo
    echo "Install it with:"
    echo "  cargo install bmo-to-md"
    echo
    echo "Or build from source:"
    echo "  cd <path>/<to>/bmo-to-md && cargo install --path ."
    exit 1
fi

# Check that required tools are available
for cmd in curl jq; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: $cmd is required but not installed."
        exit 1
    fi
done

# Validate the URL looks like a buglist.cgi link
if [[ "$buglist_url" != *"buglist.cgi"* ]]; then
    echo "Error: URL does not look like a buglist.cgi link."
    echo "Expected something like: https://bugzilla.mozilla.org/buglist.cgi?..."
    exit 1
fi

# Extract the base instance URL and query string
base_url="${buglist_url%%/buglist.cgi*}"
query_string="${buglist_url#*buglist.cgi?}"

# Convert buglist.cgi URL to REST API bug search endpoint.
# Strip UI-only params (list_id, order) that the REST API doesn't use.
api_query=$(echo "$query_string" \
    | sed 's/&list_id=[^&]*//g; s/&order=[^&]*//g; s/^list_id=[^&]*&//; s/^order=[^&]*&//')
include_fields="id"
if [[ "$skip_assigned" == true ]]; then
    include_fields="id,assigned_to"
fi
api_url="${base_url}/rest/bug?${api_query}&include_fields=${include_fields}"

echo "Querying Bugzilla REST API..."

# Fetch bug IDs from the REST API
response=$(curl -sf "$api_url") || {
    echo "Error: Failed to query Bugzilla API."
    echo "URL: $api_url"
    exit 1
}

# Extract bug IDs, optionally filtering out assigned bugs
if [[ "$skip_assigned" == true ]]; then
    mapfile -t bug_ids < <(echo "$response" \
        | jq -r '.bugs[] | select(.assigned_to == "nobody@mozilla.org") | .id' | sort -n)
    total=$(echo "$response" | jq '.bugs | length')
    assigned_count=$((total - ${#bug_ids[@]}))
    echo "Skipped ${assigned_count} assigned bugs."
else
    mapfile -t bug_ids < <(echo "$response" | jq -r '.bugs[].id' | sort -n)
fi

# Filter out bugs already fetched in output dir
if [[ "$skip_existing" == true ]]; then
    filtered=()
    for bug_id in "${bug_ids[@]}"; do
        if [[ -d "${output_dir}/bmo-${bug_id}" ]]; then
            echo "Skipping bug ${bug_id} (already fetched)"
        else
            filtered+=("$bug_id")
        fi
    done
    skipped_count=$((${#bug_ids[@]} - ${#filtered[@]}))
    bug_ids=("${filtered[@]+"${filtered[@]}"}")
    echo "Skipped ${skipped_count} already-fetched bugs."
fi

if [[ ${#bug_ids[@]} -eq 0 ]]; then
    echo "No bugs to fetch."
    exit 0
fi

echo "Bugs to fetch (${#bug_ids[@]}): ${bug_ids[*]}"
echo

if [[ "$dry_run" == true ]]; then
    echo "(dry run — not fetching)"
    exit 0
fi

# Create output directory
mkdir -p "$output_dir"

# Fetch each bug
failed=()
for bug_id in "${bug_ids[@]}"; do
    echo "--- Fetching bug $bug_id ---"
    if bmo-to-md -o "$output_dir" -a "$bug_id"; then
        echo "  OK"
    else
        echo "  FAILED (exit code $?)"
        failed+=("$bug_id")
    fi
    echo
done

# Summary
echo "=== Done ==="
echo "Fetched $((${#bug_ids[@]} - ${#failed[@]}))/${#bug_ids[@]} bugs to $output_dir"
if [[ ${#failed[@]} -gt 0 ]]; then
    echo "Failed: ${failed[*]}"
    exit 1
fi
