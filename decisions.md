# Technical decisions

Record at least 5 decisions. Include assumptions and limits.

## Decision
- Choice:
- Why:
- Alternative:
- Trade-off:
- Evidence / commit:
- Production improvement:

Cover your base image, health checks, networks, timeouts/retries, restart/resource settings,
storage and any other meaningful choices.
---
## Decision 1 — Fix the healthcheck URL, not add a new route
- Choice: corrected the healthcheck's probe path from /healthz to /health.
- Why: the task's required endpoint is /health; the app already implements it correctly.
- Alternative: add a /healthz alias route in server.py so both paths work.
- Trade-off: an alias would "work" but adds a redundant endpoint not in the required list, for no benefit.
- Evidence / commit: 5bcccd3ce87edad620e270919249cc1692f3c14b
- Production improvement: none needed here.
---
## Decision 2 — Bind the app to 0.0.0.0, rely on Docker networks for isolation
- Choice: changed APP_HOST from 127.0.0.1 to 0.0.0.0.
- Why: 0.0.0.0 is the app's own coded default in server.py; the frontend/backend network split already provides the actual isolation.
- Alternative: keep the app restricted at the socket level and route through some kind of local relay.
- Trade-off: binding to 0.0.0.0 means the app itself enforces no boundary of its own — it fully depends on the Docker network config being correct, which is standard practice but worth naming as an assumption.
- Evidence / commit: e3c1090550d2d9194fb7573ea6871631ca4a4e71
- Production improvement: none needed; this is the correct pattern.
---
## Decision 3 — Relabel bind mounts with :z instead of disabling SELinux
- Choice: added the :z mount flag to the nginx.conf and init.sql bind mounts.
- Why: :z fixes exactly the problem (container access to a specific host file) without weakening the host's overall security posture.
- Alternative: run setenforce 0 to put SELinux in permissive mode for development.
- Trade-off: :z is SELinux-specific (Fedora, here) — a harmless no-op on systems without SELinux, but worth documenting for anyone reproducing this on a different OS.
- Evidence / commit: a3cfb78dd99cdf3b760b6c871123291735ef7247
- Production improvement: document as a host requirement/README note for SELinux-enforcing environments.
---
## Decision 4 — Move the PostgreSQL password out of docker-compose.yml
- Choice: replaced the hard-coded POSTGRES_PASSWORD value in docker-compose.yml with a variable substitution, supplied via a local, gitignored env source, with a placeholder committed in .env.example.
- Why: task requires secrets out of Compose, with a safe .env.example provided.
- Alternative: leave it hard-coded, since this is a synthetic lab password anyway.
- Trade-off: none real — this is strictly safer and costs nothing in complexity.
- Evidence / commit: acf6103e3d010edb6491abc6c48e26aed31e27ff
- Production improvement: use a real secrets manager (Vault, AWS Secrets Manager, etc.) rather than any .env file, even a gitignored one.
---
## Decision 5 — Separate, longer nginx timeout for dependency-checking endpoints
- Choice: split nginx's proxy config into two location blocks — the default (/, /health, /instance) keeps a 3s proxy_read_timeout; /ready, /records, /counter get a longer one.
- Why: with postgres stopped, a real dependency-check request took ~8s to fail (DNS resolution for a stopped container's hostname doesn't fail fast), longer than nginx's original 3s — nginx was returning its own generic 504 before the app's correct 503 logic could run.
- Alternative: raise proxy_read_timeout globally for every route.
- Trade-off: a global increase would let a genuinely hung, non-dependency request hold a connection open much longer instead of failing fast; splitting by route keeps fast endpoints fast.
- Evidence / commit: aa7c7defa76eb9ddd5061d5e4ffa31386ca83958
- Production improvement: fix the DNS timeout at its source (resolver tuning or a short-circuiting health check) so every endpoint can stay on one tight timeout.   
---
## Decision 6 — Left nginx's upstream max_fails=0 unchanged
- Choice: did not change nginx.conf's max_fails=0 / proxy_next_upstream off settings after discovering they cause exactly half of requests to fail during a single-backend outage (confirmed via failure_test.py: 10/20 failed, all landing on the stopped app-01).
- Why: the task asks to measure traffic and errors during a failure, which implies errors are expected and worth capturing — not eliminated. Changing this would turn the failure test into a near-zero-error scenario, which is less informative as a demonstration.
- Alternative: set max_fails=1 fail_timeout=5s (or similar) so nginx actively ejects a failed backend from rotation after one failure, achieving near-zero-error failover.
- Trade-off: the current config makes real, visible errors during an outage (good for demonstrating detection), but it's not what a production reverse proxy would actually want — a real deployment should eject a failed backend automatically.
- Evidence / commit: dd1e8768233070e2767e6127ba7a7049bd2475bf
- Production improvement: set max_fails/fail_timeout (or move to active health-check-based upstream ejection) so nginx stops routing to a known-down backend instead of continuing to send it traffic.
