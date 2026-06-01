# tests/smoke.star — stable across upstream releases.
# CPython ships PATH only (no non-PATH env var in metadata.json), so the
# contract is Tiers 1-3: liveness, version shape, and hermetic computation.
PY = "python.exe" if ocx.target_platform.os == ocx.os.Windows else "python3"

# Tier 1 + 2: liveness + version shape (digits are the contract, not "Python").
# python prints --version to stdout on modern releases; fall back to stderr.
r = ocx.run(PY, "--version")
expect.ok(r)
expect.matches(r.stdout + r.stderr, r"\d+\.\d+\.\d+")

# Tier 3: hermetic computation — exercises the real interpreter code path.
r = ocx.run(PY, "-c", "print(40 + 2)")
expect.ok(r)
expect.contains(r.stdout, "42")

# Tier 3: stdlib import + structured output — proves a usable runtime, not a stub.
r = ocx.run(PY, "-c", "import json,sys; sys.stdout.write(json.dumps({'ok': True, 'n': 7}))")
expect.ok(r)
expect.contains(r.stdout, "\"ok\": true")

# Tier 3: the _ssl extension module is present and links (a common breakage in
# relocatable builds). Assert the import succeeds, not any version string.
r = ocx.run(PY, "-c", "import ssl; print(ssl.OPENSSL_VERSION_NUMBER)")
expect.ok(r)
expect.matches(r.stdout, r"\d+")
