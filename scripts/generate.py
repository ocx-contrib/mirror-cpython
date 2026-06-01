# /// script
# requires-python = ">=3.13"
# dependencies = ["ocx-mirror-sdk"]
#
# [tool.uv.sources]
# ocx-mirror-sdk = { url = "https://github.com/ocx-sh/ocx-mirror-sdk/releases/download/v0.4.0/ocx_mirror_sdk-0.4.0-py3-none-any.whl" }
# ///
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The OCX Authors
"""Generate url_index JSON for python-build-standalone CPython releases.

Single generator drives all mirrored CPython minors. Per-minor patch floor
is hard-coded below so first-run bootstrap does not mirror historical
patches all the way back to X.Y.0.

Release fetching goes through the ocx-mirror SDK (`github.list_releases`)
so auth, pagination, and retries are handled by the shared client.
"""

from __future__ import annotations

import re
import sys

from ocx_mirror_sdk import IndexBuilder, github

REPO = "astral-sh/python-build-standalone"

# Matches both the default (`install_only`) and slim (`install_only_stripped`)
# build flavors. Both asset names are emitted into the index under the same
# (version, build_date); mirror.yml variant patterns route each to its tag.
FILENAME_RE = re.compile(
    r"^cpython-(\d+\.\d+\.\d+)\+(\d+)-(.+)-install_only(?:_stripped)?\.tar\.gz$"
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
    # python-build-standalone carries thousands of assets per release; the
    # GitHub REST releases endpoint 504s under that load, so fetch over GraphQL.
    releases = list(
        github.list_releases(
            REPO,
            backend=github.Backend.GRAPHQL,
            include_prereleases=False,
            include_drafts=False,
        )
    )
    log(f"fetched {len(releases)} releases")

    index = IndexBuilder()
    emitted: set[str] = set()
    skipped_below_floor = 0
    for release in releases:
        # python-build-standalone tags upstream releases by build date and
        # ships every supported minor under the same tag. Group assets by
        # (python_version, build_date) so each emitted ocx_version owns only
        # its own platform tarballs.
        per_pair: dict[tuple[str, str], dict[str, str]] = {}
        for asset in release.assets:
            match = FILENAME_RE.match(asset.name)
            if match is None:
                continue
            ver, date, triple = match.group(1), match.group(2), match.group(3)
            if triple not in PLATFORMS:
                continue
            if below_floor(ver):
                skipped_below_floor += 1
                continue
            per_pair.setdefault((ver, date), {})[asset.name] = asset.browser_download_url
        for (py_version, build_date), assets in per_pair.items():
            ocx_version = f"{py_version}+{build_date}"
            if ocx_version in emitted:
                continue
            emitted.add(ocx_version)
            index.add_version(ocx_version, assets=assets, prerelease=False)
            log(f"  {release.tag_name} -> {ocx_version} ({len(assets)} assets)")

    if skipped_below_floor:
        log(f"skipped {skipped_below_floor} assets below per-minor floor")

    if not emitted:
        log("no versions generated")
        return 1

    index.emit()
    log(f"done — {len(emitted)} versions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
