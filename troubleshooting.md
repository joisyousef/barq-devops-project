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
## Entry 1 — 2026-09-19 - 00:54:31
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
## Entry 2 — 2026-09-19 - 02:34:24
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
- Related commit: e3c1090550d2d9194fb7573ea6871631ca4a4e71
- Remaining uncertainty: still need to check nginx can actually reach
  app-01.
---
## Entry 3 — 2026-09-19 - 03:15:20
- Symptom: hitting nginx repeatedly gave inconsistent results — some
  requests worked, some didn't, no obvious pattern at first.
- Hypothesis: nginx round-robins between app-01 and app-02, so if only
  one of them is misconfigured in the upstream block, it'd explain
  intermittent failures.
- Command: docker exec nginx wget -qO- http://localhost/health, run
  several times in a row.
- Actual output: alternating success and failure — consistent with
  every other request (the app-01 ones) failing.
- Failed attempt: initially thought it was still the APP_HOST bug,
  but that was already fixed and verified in entry 2. checked
  nginx.conf next instead.
- Root cause: nginx.conf upstream block pointed app-01 at port 8081.
  app-01 actually listens on 8080 (matches Dockerfile EXPOSE and
  APP_PORT). app-02's entry already correctly said 8080.
- Fix: changed app-01's upstream port from 8081 to 8080 in
  nginx/nginx.conf.
- Retest: ran the wget loop again, all requests succeeded this time.
- Related commit: 5587a0d8697dc3d0a2c1d93a07a70ac569211f04
- Remaining uncertainty: nginx's own published port (81 vs its
  actual listen 80) is still broken, so this only proves nginx can
  reach app-01 internally — haven't proven external access works yet.
  and I seem to have an issue is SELinux on my Fedora it is blocking Docker bind mounts.
  I will fix it in the next commit.
---
## Entry 4 — 2026-09-20 
- Symptom: docker compose up starts containers, but postgres and nginx keep exiting with “Permission denied”. 
  ls: /docker-entrypoint-initdb.d/01-init.sql: Permission denied 
  nginx: [emerg] open() "/etc/nginx/nginx.conf" failed (13: Permission denied)
- Hypothesis: SELinux on my Fedora is blocking Docker bind mounts for the init SQL and nginx.conf files, not Unix permissions.
- Command or test: docker compose logs postgres --tail=50, docker compose logs nginx --tail=20, 
  namei -l /home/yousef/Documents/ProjectBARQ/BARQ-Academy/nginx/nginx.conf
- Actual output: Repeated Permission denied inside containers for bind-mounted files. 
  namei showed normal Unix permissions (-rw-r--r-- yousef yousef nginx.conf).
- Failed attempt and what changed your thinking: Everytime I do docker-compose up --build,
  I see the selinux notification pop up, and the Permission denied” pattern got me thinking of selinux immediately.
- Root cause: SELinux preventing containers from accessing host files bind-mounted into postgres and nginx because the mounts lacked an SELinux relabel flag.
- Fix: edited docker-compose.yml to add :z to the problematic bind mounts: 
  ./database/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro,z 
  ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro,z
- Retest evidence: docker compose logs postgres --tail=50 no longer shows Permission denied for 01-init.sql. 
  docker compose logs nginx --tail=20 no longer shows open() "/etc/nginx/nginx.conf" failed (13: Permission denied). 
  docker compose ps -a shows postgres and nginx staying up (not repeatedly exiting).
- Related commit: a3cfb78dd99cdf3b760b6c871123291735ef7247
- Remaining uncertainty: none on this specific issue.
---
## Entry 5 — 2026-09-20
- Symptom: both app-01 and app-02 report instance_id "app-01" in logs
  and /instance responses.
- Hypothesis: app-02's environment override in docker-compose.yml
  still says INSTANCE_ID "app-01" — looks like a copy-paste leftover
  from when app-02 was created off app-01's block.
- Command: docker exec app-02 env | grep INSTANCE_ID
- Actual output: INSTANCE_ID=app-01
- Failed attempt: none.
- Root cause: app-02's service block in docker-compose.yml sets
  INSTANCE_ID to "app-01" instead of "app-02".
- Fix: changed the value to "app-02".
- Retest: force-recreated app-02, docker exec app-02 env | grep
  INSTANCE_ID now shows app-02.
- Related commit: <hash>
- Remaining uncertainty: none for this one.
