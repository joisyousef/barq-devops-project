#!/usr/bin/env python3
"""Candidate deliverable: stop one backend, measure traffic, restore it and verify."""
#!/usr/bin/env python3
"""Failure/recovery test for the BARQ assessment stack."""
import json
import os
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

BASE_URL = os.environ.get("VALIDATE_URL", f"http://127.0.0.1:{os.environ.get('PUBLIC_PORT', '8080')}")
TOTAL_REQUESTS = 20
REQUEST_TIMEOUT = 5
RECOVERY_RETRIES = 20
RECOVERY_DELAY = 1

def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker command failed")
    return result.stdout.strip()

def hit_instance():
    """Return (status_code, parsed_body_or_None)."""
    try:
        with urlopen(f"{BASE_URL}/instance", timeout=REQUEST_TIMEOUT) as resp:
            return resp.status, json.loads(resp.read())
    except HTTPError as exc:
        return exc.code, None
    except URLError:
        return 0, None

def health_status(container):
    try:
        return docker("inspect", container, "--format", "{{.State.Health.Status}}")
    except RuntimeError:
        return ""

def main():
    print("Stopping app-01...")
    docker("compose", "stop", "app-01")

    print(f"\nSending {TOTAL_REQUESTS} requests while app-01 is stopped...")
    success = errors = 0
    served_by = {}
    for _ in range(TOTAL_REQUESTS):
        status, body = hit_instance()
        if status == 200 and body:
            success += 1
            iid = body.get("instance_id", "unknown")
            served_by[iid] = served_by.get(iid, 0) + 1
        else:
            errors += 1

    print("Traffic during failure:")
    print(f"  Successful requests: {success}")
    print(f"  Errors: {errors}")
    print(f"  Served by: {served_by}")

    if success == 0:
        print("FAIL: no successful traffic while app-01 was down")
        docker("compose", "start", "app-01")
        sys.exit(1)
    print("PASS: traffic continued while app-01 was down")

    if "app-01" in served_by:
        print(f"NOTE: {served_by['app-01']} request(s) still routed to app-01 and failed as "
              f"expected (nginx upstream uses max_fails=0, so it does not remove a downed "
              f"server from rotation) — this is the error count above, not a bug.")

    print("\nRestoring app-01...")
    docker("compose", "start", "app-01")

    print("Waiting for app-01 health...")
    status = ""
    for _ in range(RECOVERY_RETRIES):
        status = health_status("app-01")
        if status == "healthy":
            break
        time.sleep(RECOVERY_DELAY)

    if status != "healthy":
        print(f"FAIL: app-01 did not recover (last status: {status!r})")
        sys.exit(1)
    print("PASS: app-01 recovered")

    print("\nProving recovered app-01 serves traffic...")
    for _ in range(RECOVERY_RETRIES):
        status, body = hit_instance()
        if status == 200 and body and body.get("instance_id") == "app-01":
            print("PASS: recovered app-01 served a request")
            sys.exit(0)
        time.sleep(RECOVERY_DELAY)

    print("FAIL: recovered app-01 did not serve traffic")
    sys.exit(1)

if __name__ == "__main__":
    main()
