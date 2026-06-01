PY = "python.exe" if str(ocx.target_platform.os) == "windows" else "python3"

r_version = ocx.run(PY, "--version")
expect.ok(r_version)
expect.eq(r_version.exit_code, 0)
expect.contains(r_version.stdout + r_version.stderr, "Python 3.")

r_math = ocx.run(PY, "-c", "print(40 + 2)")
expect.eq(r_math.exit_code, 0)
expect.contains(r_math.stdout, "42")

r_json = ocx.run(PY, "-c", "import json,sys; sys.stdout.write(json.dumps({'ok': True, 'n': 7}))")
expect.eq(r_json.exit_code, 0)
expect.contains(r_json.stdout, "\"ok\": true")

r_ssl = ocx.run(PY, "-c", "import ssl; print(ssl.OPENSSL_VERSION)")
expect.eq(r_ssl.exit_code, 0)
expect.contains(r_ssl.stdout, "OpenSSL")
