#!/usr/bin/env python3
"""Candidate deliverable: implement environment validation; this is not a solution."""
"""Validation for the BARQ assessment stack."""
#!/usr/bin/env python3
"""Environment validation for the BARQ assessment stack."""
import json
import os
import subprocess
import sys
import time
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

BASE_URL = os.environ.get("VALIDATE_URL", "http://127.0.0.1:8080")
TIMEOUT = 5
RETRIES = 10
RETRY_DELAY = 1

failures = []

def check(name, fn):
    try:
        fn()
        print(f"PASS: {name}")
    except Exception as exc:
        print(f"FAIL: {name} -> {exc}")
        failures.append(name)

def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker command failed")
    return result.stdout.strip()

def wait_for(path, expect_status=200):
    url = f"{BASE_URL}{path}"
    last_exc = None
    for _ in range(RETRIES):
        try:
            with urlopen(url, timeout=TIMEOUT) as resp:
                if resp.status == expect_status:
                    return json.loads(resp.read())
                raise RuntimeError(f"expected {expect_status}, got {resp.status}")
        except HTTPError as exc:
            if exc.code == expect_status:
                return json.loads(exc.read())
            last_exc = exc
        except URLError as exc:
            last_exc = exc
        time.sleep(RETRY_DELAY)
    raise RuntimeError(f"timed out waiting for {url}: {last_exc}")

def check_public_access():
    wait_for("/")

def check_health():
    body = wait_for("/health")
    assert body.get("status") == "alive", body

def check_ready():
    body = wait_for("/ready")
    deps = body.get("dependencies", {})
    assert deps.get("postgres") == "ready", deps
    assert deps.get("redis") == "ready", deps

def check_records():
    req = Request(f"{BASE_URL}/records",
                  data=json.dumps({"title": "validate-check"}).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=TIMEOUT) as resp:
        assert resp.status == 201, resp.status
    body = wait_for("/records")
    assert any(r["title"] == "validate-check" for r in body.get("records", [])), body

def check_counter():
    body = wait_for("/counter")
    assert isinstance(body.get("counter"), int), body

def check_both_backends():
    seen = set()
    for _ in range(10):
        body = wait_for("/instance")
        seen.add(body.get("instance_id"))
    assert seen == {"app-01", "app-02", "app-03"}, f"only saw: {seen}"

def check_isolation(target):
    try:
        result = subprocess.run(["docker", "exec", "nginx", "getent", "hosts", target],
                                capture_output=True, text=True, timeout=10)
    except subprocess.TimeoutExpired:
        return  
    if result.returncode == 0 and result.stdout.strip():
        raise RuntimeError(f"nginx can resolve {target}: {result.stdout.strip()}")

def check_no_published_ports():
    for name in ("postgres", "redis"):
        ports = json.loads(docker("inspect", name, "--format", "{{json .NetworkSettings.Ports}}"))
        for port, bindings in ports.items():
            if bindings:
                raise RuntimeError(f"{name} {port} is published to host: {bindings}")

def main():
    check("public access on /", check_public_access)
    check("/health", check_health)
    check("/ready (postgres + redis)", check_ready)
    check("/records create + list", check_records)
    check("/counter", check_counter)
    check("both backends respond via /instance", check_both_backends)
    check("nginx cannot resolve postgres", lambda: check_isolation("postgres"))
    check("nginx cannot resolve redis", lambda: check_isolation("redis"))
    check("no published db/cache ports", check_no_published_ports)

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)} check(s) failed: {', '.join(failures)})")
        sys.exit(1)
    print("RESULT: PASS (all checks passed)")
    sys.exit(0)

if __name__ == "__main__":
    main()
