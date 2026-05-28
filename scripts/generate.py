#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Generate url_index JSON for python-build-standalone CPython releases.

Single generator drives all mirrored CPython minors. Per-minor patch floor
is hard-coded below so first-run bootstrap does not mirror historical
patches all the way back to X.Y.0.

Pure stdlib (urllib + json). No third-party deps so the workflow does not
need uv or a mirror SDK — just a system python3.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

FILENAME_RE = re.compile(
    r"^cpython-(\d+\.\d+\.\d+)\+(\d+)-(.+)-install_only\.tar\.gz$"
)

PLATFORMS = {
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
    "x86_64-pc-windows-msvc",
}

# Per-minor patch floor. Versions below this are skipped so a fresh mirror
# does not bootstrap historical patches. Bump these when retiring older
# patches that are no longer worth advertising.
#
# Format: "<minor>": (major, minor, min_patch)
MINOR_FLOORS: dict[str, tuple[int, int, int]] = {
    "3.12": (3, 12, 13),
    "3.13": (3, 13, 13),
    "3.14": (3, 14, 4),
}


def log(message: str) -> None:
    sys.stderr.write(f"generate: {message}\n")


def fetch_releases(owner: str, repo: str) -> list[dict]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ocx-mirror-generate",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    per_page = 10
    max_attempts = 12
    releases: list[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page={per_page}&page={page}"
        request = urllib.request.Request(url, headers=headers)
        payload = None
        for attempt in range(1, max_attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    payload = json.load(response)
                break
            except urllib.error.HTTPError as error:
                if error.code >= 500 and attempt < max_attempts:
                    delay = min(30, 2 ** attempt)
                    log(f"page {page} attempt {attempt}: {error.code} {error.reason}; retrying in {delay}s")
                    time.sleep(delay)
                    continue
                log(f"GitHub API error on page {page}: {error.code} {error.reason}")
                raise
            except (urllib.error.URLError, http.client.IncompleteRead, ConnectionError, TimeoutError) as error:
                if attempt < max_attempts:
                    delay = min(30, 2 ** attempt)
                    log(f"page {page} attempt {attempt}: {type(error).__name__}: {error}; retrying in {delay}s")
                    time.sleep(delay)
                    continue
                raise
        if payload is None or not payload:
            break
        releases.extend(payload)
        if len(payload) < per_page:
            break
        page += 1
        if page > 200:
            log("aborting after 200 pages")
            break
    return releases


def below_floor(py_version: str) -> bool:
    """Return True when py_version is below the floor configured for its minor."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", py_version)
    if match is None:
        return True
    major, minor, patch = (int(p) for p in match.groups())
    floor = MINOR_FLOORS.get(f"{major}.{minor}")
    if floor is None:
        return True
    return (major, minor, patch) < floor


def main() -> int:
    releases = fetch_releases("astral-sh", "python-build-standalone")
    log(f"fetched {len(releases)} releases")

    versions: dict[str, dict] = {}
    skipped_below_floor = 0
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        # python-build-standalone tags upstream releases by build date and
        # ships every supported minor under the same tag. Group assets by
        # (python_version, build_date) so each emitted ocx_version owns only
        # its own platform tarballs.
        per_pair: dict[tuple[str, str], dict[str, str]] = {}
        for asset in release.get("assets", []):
            match = FILENAME_RE.match(asset["name"])
            if match is None:
                continue
            ver, date, triple = match.group(1), match.group(2), match.group(3)
            if triple not in PLATFORMS:
                continue
            if below_floor(ver):
                skipped_below_floor += 1
                continue
            per_pair.setdefault((ver, date), {})[asset["name"]] = asset["browser_download_url"]
        for (py_version, build_date), assets in per_pair.items():
            ocx_version = f"{py_version}+{build_date}"
            if ocx_version in versions:
                continue
            versions[ocx_version] = {"prerelease": False, "assets": assets}
            log(f"  {release['tag_name']} -> {ocx_version} ({len(assets)} assets)")

    if skipped_below_floor:
        log(f"skipped {skipped_below_floor} assets below per-minor floor")

    if not versions:
        log("no versions generated")
        return 1

    json.dump({"versions": versions}, sys.stdout)
    log(f"done — {len(versions)} versions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
