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
## Entry 1 — 2026-09-19
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
- Related commit: 5bcccd3ce87edad620e270919249cc1692f3c14b
- Remaining uncertainty: app-02 still says instance_id "app-01" in
  the logs — separate bug, not touching it here. also want to check
  later whether /health is supposed to be this simple or if I'm
  missing something about what "liveness" means vs /ready.
---
## Entry 2 — 2026-09-19
- Symptom: nothing outside app-01's own container could reach it, even
  other containers on the same network.
- Hypothesis: APP_HOST is set to 127.0.0.1 in the compose environment
  block, which overrides the app's own default of 0.0.0.0 (saw this in
  server.py). binding to loopback means only the process itself can
  connect, not other containers.
- Command: docker exec app-02 python -c "import urllib.request;
  print(urllib.request.urlopen('http://app-01:8080/health',
  timeout=2).status)"
- Actual output: connection refused / timeout, before the fix.
- Failed attempt: none, first try worked.
- Root cause: docker-compose.yml x-app.environment sets APP_HOST to
  127.0.0.1, overriding server.py's safe default of 0.0.0.0.
- Fix: changed APP_HOST to 0.0.0.0 in the x-app anchor.
- Retest: same command now returns 200. also force-recreated app-01
  and app-02 since env vars don't update on a plain restart.
- Related commit: <hash>
- Remaining uncertainty: still need to check nginx can actually reach
  app-01.
