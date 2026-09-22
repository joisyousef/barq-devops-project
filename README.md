# BARQ Assessment — DevOps Internship Task

Two Flask instances (plus a third added live) behind NGINX, with PostgreSQL and Redis on
an isolated backend network. See `troubleshooting.md` for the full investigation,
`decisions.md` for design choices, and `security_review.md` for known risks.

## Setup

```bash
git clone https://github.com/joisyousef/barq-devops-project
cd barq-devops-project
cp .env.example .env
cp config/app.env.example config/app.env
```

Edit `.env` and `config/app.env` if you want your own local password instead of the
placeholder — both files must use the same value.

## Build and start

```bash
docker compose build
docker compose up -d
docker compose ps          # all 5 services should show (healthy) within ~30s
```

## Test

```bash
curl -i http://127.0.0.1:8080/
curl -i http://127.0.0.1:8080/health
curl -i http://127.0.0.1:8080/ready
curl -H 'Content-Type: application/json' -d '{"title":"test"}' http://127.0.0.1:8080/records
curl http://127.0.0.1:8080/records
curl http://127.0.0.1:8080/counter
curl http://127.0.0.1:8080/instance   # run repeatedly, alternates app-01/app-02

# full automated check:
python3 validate.py
```

## Failure test

```bash
python3 failure_test.py
```
Stops app-01, sends 20 requests to `/instance`, restarts app-01, confirms it serves again.
Expect roughly half the requests to fail while app-01 is down — nginx's upstream config
(`max_fails=0`) keeps routing to it rather than ejecting it (see `decisions.md` Decision 12).

## Backup and restore

```bash
./backup.sh                                    # writes backups/barq_tasks_<timestamp>.dump
./restore.sh backups/barq_tasks_<timestamp>.dump   # restores into a throwaway test DB and verifies
```

`restore.sh` never touches the live database — it restores into `barq_restore_test`, checks
the data came back, then drops that test database.

## Persistence proof

```bash
curl -s -X POST http://localhost:8080/records -H "Content-Type: application/json" -d '{"title":"persistence-check"}'
docker compose up -d --force-recreate app-01 app-02 postgres
curl -s http://localhost:8080/records   # the record is still there
```

## Stop / cleanup

```bash
docker compose down          # stops and removes containers, keeps volumes (data survives)
docker compose down -v       # also removes volumes — use only when you want a clean slate
```

## CI

`.github/workflows/ci.yml` runs on every push and pull request: checkout, recreate env files
from the committed examples, validate compose syntax, build, start, wait for all 5 services
to report healthy, then run `validate.py`. A failing validation fails the build.

## Key questions

**What failed first, and what proved it?** The healthcheck was probing `/healthz`, a path
the app never implements — proven by the app's own 404 logs, not a guess.

**How do requests flow?** Client → nginx (only nginx is published, on the host port) → one
of the app instances (round-robin, both on the `frontend` network) → PostgreSQL/Redis (on
the `backend` network, marked `internal: true`, unreachable from nginx or the host).

**Why these timeouts?** `/`, `/health`, `/instance` never touch a database, so they keep a
tight 3s `proxy_read_timeout`. `/ready`, `/records`, `/counter` do touch PostgreSQL/Redis,
and a real test showed a dependency failure can take ~8s to resolve (DNS lookup for a
stopped container doesn't fail fast) — so those routes get 10s, enough for the app's own
503 to actually reach the client instead of nginx generating its own generic error.

**What does green CI prove — and not prove?** It proves the stack builds, starts, and passes
every scripted check from a completely fresh checkout with placeholder credentials. It does
NOT prove the live video's manual steps (stopping a backend, the port change, adding a third
instance, the historical log finding) — those are only proven by the recording itself.

**Remaining single points of failure:** a single nginx instance and a single PostgreSQL
instance. In production: multiple nginx replicas behind a load balancer, and a managed or
replicated PostgreSQL setup rather than one container.

**How was AI-assisted work verified?** Every fix in `troubleshooting.md` was tested against
real command output before being accepted — see `AI_USAGE.md` for specifics, including one
case where an AI's first hypothesis was wrong and got corrected by evidence.

## Recorded challenge

Use the supplied video_challenge.sh unchanged. Read its code if needed; do not run it early.
After repairing the environment, run it once, for the first time in the video working copy,
during the continuous 12-18 minute recording. The script requires healthy services, both
initial instances and the target network layout. Preflight failures make no runtime changes.

```bash
./video_challenge.sh
```

If you deliberately changed the project name, pass --project YOUR_PROJECT.
An organizer-approved alternate local URL can be passed with --url http://127.0.0.1:PORT.
The script touches only matching Compose-owned lab containers/networks.
Keep the receipt in .assessment/challenge.json for the evidence index. Do not delete the
one-run marker to retry. A local marker is not tamper-proof; ownership is judged from evidence.
Do not use docker compose down to reset the runtime challenge.

## Stop safely

Outside the recorded challenge, docker compose -p barq-assessment down stops this lab.
Do not use --volumes during persistence tests. Avoid global Docker prune/cleanup commands.
Back up anything you need before removing containers; investigate whether data actually persists.
