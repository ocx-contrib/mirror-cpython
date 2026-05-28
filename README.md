# mirror-cpython

OCX mirror for [python-build-standalone](https://github.com/astral-sh/python-build-standalone) CPython 3.12.x – 3.14.x. Publishes self-contained CPython builds to `ocx.sh/cpython` with cascade tags after a smoke test per `(version, platform)`.

This repository consolidates the former `mirror-python-3.12`, `mirror-python-3.13`, and `mirror-python-3.14` into a single spec. A per-minor patch floor in `scripts/generate.py` keeps first-run bootstrap small.

## Editing

| File | Edit | Regenerate after |
|------|------|------------------|
| `mirror.yml` | hand | `ocx-mirror pipeline generate ci` |
| `scripts/generate.py` | hand | — |
| `tests/smoke.star` | hand | — |
| `metadata.json`, `metadata-windows.json`, `CATALOG.md`, `logo.svg` | hand | — |
| `.github/workflows/*.yml` | generated | re-run when `mirror.yml` changes |

`scripts/generate.py` is pure stdlib — it queries the GitHub releases API
for `astral-sh/python-build-standalone` and emits a `url_index` JSON
document filtered against `MINOR_FLOORS`. Bump that map to retire older
patches or add a new minor.

CI fails on drift via `ocx-mirror pipeline generate ci --check`.

## Required secrets

| Secret | Use |
|--------|-----|
| `OCX_MIRROR_REGISTRY_TOKEN` + `OCX_MIRROR_REGISTRY_USER` | `ocx package push` to `ocx.sh` |
| `OCX_MIRROR_DISCORD_HOOK` | notify-stage Discord webhook URL |

## License

Apache-2.0 — see [`LICENSE`](LICENSE). Upstream assets (Python logo,
mirrored CPython binaries) are out of scope; see [`NOTICE.md`](NOTICE.md).
