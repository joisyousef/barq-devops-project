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
## Entry 4 — 2026-09-20 - 03:44:08
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
## Entry 5 — 2026-09-20 - 06:31:03
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
- Related commit: f748027512529a176eca2e869b9190f722aa5d75
- Remaining uncertainty: none for this one.
---
## Entry 7 — 2026-09-20 - 16:58:32
- Symptom: nginx was on both frontend and backend networks, meaning
  it had a direct path to postgres and redis even though it only
  ever needs to talk to app-01/app-02.
- Hypothesis: task requires nginx to have no path to the databases,
  dropping backend from its networks list should remove that path
  entirely since Docker's DNS only resolves names within a shared
  network.
- Command: docker exec nginx getent hosts postgres
           docker exec nginx getent hosts redis
- Actual output: 172.18.0.2 postgres postgres
                 172.18.0.3 redis redis
These results showed that NGINX could resolve both backend services.
- Failed attempt: none for this fix specifically. Also tried curl -i
  http://localhost:8080/health as an extra check and got "Connection
  reset by peer" — but that's the separate.
- Root cause: nginx service in docker-compose.yml listed backend in
  its networks, which it never needed for its actual job (proxying
  to app-01/app-02, both reachable via frontend).
- Fix: removed backend from nginx's networks list.
- Retest evidence:
   docker exec nginx getent hosts postgres
  (no output)
   docker exec nginx getent hosts redis
  (no output)
  Empty output means DNS resolution failed for both — nginx can no
  longer see either hostname, confirming it has no path to them.
- Related commit: 3b7a19d64db5a53026e5c81c4571bb1f0d16b3c6
- Remaining uncertainty: curl to :8080 still fails, but
  that's the known, unfixed nginx port-mapping bug
---
## Entry 8 — 2026-09-20 - 18:02:54
- Symptom: curl -i http://localhost:8080/health from the host returned
  "Recv failure: Connection reset by peer" even after fixing
  APP_HOST, the upstream port, and nginx's network membership.
- Hypothesis: docker-compose.yml maps host 8080 to container port 81,
  but nginx.conf's server block listens on 80 — nothing is actually
  listening on 81 inside the container.
- Command: curl -i http://localhost:8080/health, before and after.
- Actual output: curl: (56) Recv failure: Connection reset by peer
- Failed attempt: none new — this was already flagged when first
  reading the files, just hadn't been fixed yet.
- Root cause: nginx service's port mapping pointed at container port
  81 nginx.conf listens on 80.
- Fix: changed the compose port mapping to forward to container
  port 80.
- Retest evidence: 
    HTTP/1.1 200 OK
    Server: nginx/1.28.3
    Date: Sun, 20 Sep 2026 15:01:31 GMT
    Content-Type: application/json
    Content-Length: 81
    Connection: keep-alive
    X-Instance-ID: app-01
    X-Request-ID: 437dd1479f36ecf1861eb2545758b11b
    Cache-Control: no-store

    {"instance_id":"app-01","service":"barq-api","status":"alive","version":"2.0.0"}
- Related commit: e757fbc13f5131b8116a2c435523c3236da61e8f
- Remaining uncertainty: none
---
## Entry 9 — 2026-09-20 - 18:51:26
- Symptom: containers run as root even though the Dockerfile creates
  a dedicated non-root user.
- Hypothesis: Dockerfile creates the app user and chowns files to it,
  but then sets USER root right before CMD, undoing it.
- Command: docker exec app-01 whoami
- Actual output: "root"
- Failed attempt: none.
- Root cause: Dockerfile had USER root as the final USER directive
  before CMD.
- Fix: removed USER root, replaced with USER app.
- Retest evidence: docker exec app-01 whoami 
  results: "app"
  cbd88cad72ce   barq-assessment-app-01   "python -m app.server"   43 minutes ago   Up 43 minutes (healthy)   8080/tcp                 app-01
  7f5ebc04374f   barq-assessment-app-02   "python -m app.server"   43 minutes ago   Up 43 minutes (healthy)   8080/tcp                 app-02
- Related commit: 3cc0a84b3a358a0f7445856bb4d9046c62d76040
- Remaining uncertainty: none 
---
## Entry 10 — 2026-09-20 - 19:40:04
- Symptom: Dockerfile copies config/app.env (with the real Postgres
  password) directly into the image.
- Hypothesis: redundant — compose's env_file already injects the
  same variables at runtime, so this COPY only exists to leak the
  secret into a permanent image layer.
- Command: docker exec app-01 ls -la /srv/app.env
- Actual output: -rw-r--r--. 1 root root 112 Sep 19 20:13 /srv/app.env
- Failed attempt: none.
- Root cause: unnecessary COPY config/app.env /srv/app.env line in
  the Dockerfile.
- Fix: deleted the line.
- Retest evidence: ls: cannot access '/srv/app.env': No such file or directory
  confirm app still starts and passes healthcheck via docker compose ps]
- Related commit: d36e114870a5a60d259922baf8901c51235e4540
- Remaining uncertainty: none
---
## Entry 11 — 2026-09-20 - 20:11:04
- Symptom: needed to check whether Postgres data survives a
  container recreate, since the task requires it to.
- Hypothesis: the named volume was mounted at
  /var/lib/postgresql/backup, not Postgres's real data directory —
  and the real data dir, /var/lib/postgresql/data, was overridden by
  tmpfs, which is memory-backed and wiped on every restart.
- Command: created a test row, force-recreated postgres, checked if
  the row survived. $ docker exec postgres psql -U barq_app -d barq_tasks -c "CREATE TABLE IF NOT EXISTS selftest(id serial primary key, val text); INSERT INTO selftest(val) VALUES ('test-persistence');"
- Actual output: $ docker exec postgres psql -U barq_app -d barq_tasks -c "SELECT * FROM selftest;"
ERROR:  relation "selftest" does not exist
LINE 1: SELECT * FROM selftest;
                      ^
- Failed attempt: none.
- Root cause: postgres-data volume mounted to the wrong path
  the real data directory sat on tmpfs.
- Fix: remounted postgres-data to /var/lib/postgresql/data, removed
  the tmpfs override.
- Retest evidence: docker exec postgres psql -U barq_app -d barq_tasks -c "SELECT * FROM selftest;"
 id |    val    
----+-----------
  1 | test-persistence
(1 row)
- Related commit: 3a48c7a23f2fe0cb96f6a434dca3fb67c67acb8a
- Remaining uncertainty: none
---
## Entry 12 — 2026-09-20 - 02:45:46
- Symptom: /ready reported redis "unavailable"; /counter failed with
  {"error":"redis_unavailable"}.
- Hypothesis: REDIS_URL in config/app.env used port 6380; redis
  actually listens on 6379.
- Command: curl /ready and /counter before and after the fix +
  force-recreate.
- Actual output (before): {"dependencies":{"redis":"unavailable",...}},
  {"error":"redis_unavailable",...}
- Failed attempt: initially ran the same curls right after editing
  the file but before force-recreating app-01/app-02 — got identical
  failing output, which confirmed (again) that env var edits don't
  apply without a recreate.
- Root cause: config/app.env's REDIS_URL pointed at port 6380 instead
  of redis's actual port, 6379.
- Fix: corrected the port in REDIS_URL to 6379.
- Retest evidence: after docker compose up -d --force-recreate app-01
  app-02, /ready shows "redis":"ready"; /counter returns
  {"counter":1,"instance_id":"app-02",...}.
- Related commit: 17faaf64f96bc323c3fd6047f4063508a5c29d07
- Remaining uncertainty: none for redis specifically. Postgres, edited
  in the same file at the same time, is still unavailable — tracked
  separately below since it's a distinct, unresolved problem.
---
## Entry 13 — 2026-09-20 - 02:45:46
- Symptom: after correcting the last character of the password in
  config/app.env's DATABASE_URL and force-recreating app-01/app-02,
  /ready still reports postgres "unavailable" and /records still
  fails with {"error":"postgres_unavailable"}.
- Hypothesis: not sure yet — could still be an auth mismatch, could
  be something else entirely. Need the actual log line to know
  which.
- Command or test: corrected the password digit, force-recreated
  app-01 and app-02, reran curl /ready and /records.
- Actual output: dependencies.postgres still "unavailable" after the
  fix — no change from before.
- Failed attempt and what changed your thinking: assumed the wrong
  password digit was the only problem, since that's what
  docker compose config revealed. Fixing it alone didn't resolve
  the connection, so there's something else going on — haven't
  checked postgres's own logs yet for the actual rejection reason.
- Root cause: not yet confirmed.
- Fix: not yet applied.
- Retest evidence: pending.
- Related commit: none yet — investigation only.
- Remaining uncertainty: need to check docker compose logs postgres
  for the actual error (auth failure vs. connection refused vs.
  something else) before guessing further.
---
## Entry 14 — 2026-09-20 (continued)
- Actual output: after checking postgres's logs (no connection
  attempts logged at all) and confirming nginx/network/TCP reachability
  weren't the issue, went back to config/app.env and compared every
  value in DATABASE_URL against the postgres service block again.
  Found DATABASE_URL still said port 5433 — postgres actually listens
  on 5432. Had fixed the password and the redis port earlier but
  missed this one.
- Failed attempt and what changed your thinking: first assumed the
  password digit was the only wrong value. Fixing it and recreating
  didn't help. Checked postgres's logs next and saw no connection
  attempts at all, which pointed away from an auth failure and back
  toward the connection string itself — that's when I re-checked
  every value instead of just the one I'd already touched.
- Root cause: config/app.env's DATABASE_URL used port 5433; postgres
  listens on 5432.
- Fix: corrected the port to 5432.
- Retest evidence:
  GET /ready → {"dependencies":{"postgres":"ready","redis":"ready"},
  "status":"ready",...}
  POST /records → {"record":{"id":4,"title":"Persistence proof"},...}
  GET /records → returns all 4 records including the new one
  GET /counter → {"counter":10,...}
  GET /instance → 200 OK, alternating instance_id between app-01/app-02
  All previously-unavailable endpoints now succeed end-to-end.
- Related commit: 7cc142b7357a87a578859359dbeae381054a6711
- Remaining uncertainty: none — every value in config/app.env now
  matches the actual service configuration.
---
## Entry 15 — 2026-09-21 - 13:41:49
- Symptom: redis ran with --save "" --appendonly no and no volume —
  any recreate would wipe all data.
- Hypothesis: task asks for persistence "where appropriate"; the
  counter should survive restarts the same way postgres records do.
- Command: docker exec redis redis-cli CONFIG GET appendonly
- Actual output: appendonly no
- Failed attempt: none.
- Root cause: --save "" --appendonly no explicitly disabled and /data had no backing volume anyway.
- Fix: enabled appendonly, added a named redis-data volume at /data.
- Retest evidence: docker exec redis redis-cli SET selftest hello
  OK
  docker compose up -d --force-recreate redis
  [+] up 1/1
  ✔ Container redis Started
  docker exec redis redis-cli GET selftest
   hello
- Related commit: fdb96c56630bc2b3088386071ec366d4b7e9578f
- Remaining uncertainty: none.
---
## Entry 16 — 2026-09-21
- Symptom: redis's port 6379 was published to the host at
  127.0.0.1:16379, which the task disallows.
- Hypothesis: straightforward — remove ports:, service-name access
  on the backend network is unaffected.
- Command: docker inspect redis --format '{{json .NetworkSettings.Ports}}'
- Actual output: showed a host mapping before the fix (confirmed via
  docker compose config's resolved ports: block).
- Failed attempt: none.
- Root cause: unnecessary ports: mapping on the redis service.
- Fix: removed the ports: line entirely.
- Retest evidence: docker inspect redis --format
  '{{json .NetworkSettings.Ports}}' now returns {"6379/tcp":null} —
  no host mapping. docker compose config confirms no ports: entry
  under the redis service.
- Related commit: <hash>
- Remaining uncertainty: none
---
## Entry 17 — 2026-09-21
- Symptom: Services lacked explicit restart policies/resource limits, and NGINX had no independent liveness endpoint.
- Hypothesis: Add restart: unless-stopped, CPU/memory limits, and an NGINX-only healthcheck.
- Command:
  docker compose config -q
  docker compose up -d --build --force-recreate
  docker compose ps
  docker exec nginx wget -qO- http://127.0.0.1/nginx-health
  docker inspect nginx --format '{{.State.Health.Status}}'
- Actual output: Compose validation succeeded; all 5 containers started. /nginx-health returned ok; NGINX health status was healthy.
- Failed attempt: None.
- Root cause: Required operational controls were missing from the service configuration.
- Fix: Added unless-stopped restart policies, CPU/memory limits, and the /nginx-health endpoint with a Compose healthcheck.
- Retest evidence: NGINX healthcheck returned ok and status healthy. Restart policies/resource limits still need separate runtime verification.
- Related commit: [hash]
- Remaining uncertainty: Resource-limit values should be tuned using real production usage.
---
