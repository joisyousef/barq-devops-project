# Troubleshooting journal

Keep chronological entries. Copy this block for each meaningful investigation.

## Entry / date / time
- Symptom:
- Hypothesis:
- Command or test:
- Actual output:
- Failed attempt and what changed your thinking:
- Root cause:
- Fix:
- Retest evidence:
- Related commit:
- Remaining uncertainty:

Do not fabricate a failed attempt just to fill the template. Record actual attempts.
---
## Entry 1 — 2026-09-19, ~20:30-21:45 UTC
- Symptom: ran docker compose up --build and both apps kept spamming
  404s on /healthz, like every 5 seconds, forever.
- Hypothesis: figured it's the healthcheck hitting the wrong path.
  task says the endpoint should be /health not /healthz, so probably
  just a typo in the compose file.
- Command: docker compose up --build, then docker compose logs app-01
  to see it clearly. also checked server.py to make sure the app
  really doesn't have a /healthz route (it doesn't, just /health).
- Actual output: {"path": "/healthz", "status": 404} on repeat, both
  containers.
- Failed attempt: none really, got it right first try on this one.
- Root cause: x-app healthcheck in docker-compose.yml was checking
  /healthz, app only has /health.
- Fix: changed the healthcheck url to /health.
- Retest: reran the build, now getting 200s on /health from both
  app-01 and app-02.
- Related commit: <hash after committing>
- Remaining uncertainty: app-02 still says instance_id "app-01" in
  the logs — separate bug, not touching it here. also want to check
  later whether /health is supposed to be this simple or if I'm
  missing something about what "liveness" means vs /ready.
