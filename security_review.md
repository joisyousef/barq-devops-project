# Security and production-readiness review

Record at least 8 concrete risks or improvements relevant to your final solution.
This is a review requirement, not the number of hidden faults.

For each finding:
- Risk and evidence:
- Impact:
- Implemented fix / commit:
- Production follow-up:
- How to verify:

Cover secrets, ports, container user, image selection, networks, persistence/backup,
logging/monitoring and availability. Separate completed work from planned improvements.
---
## Finding 1 — Secrets baked into the built image (category: secrets)
- Risk and evidence: Dockerfile had COPY config/app.env /srv/app.env, copying the real Postgres password into a permanent image layer.
- Impact: anyone with the built image could extract the plaintext password from its layer history, even after the source file changed.
- Implemented fix / commit: d36e114870a5a60d259922baf8901c51235e4540
- Production follow-up: use a real secrets manager rather than any .env file, even a gitignored one.
- How to verify: docker exec app-01 ls /srv/app.env → No such file or directory.
---
## Finding 2 — PostgreSQL password hard-coded directly in docker-compose.yml (category: secrets)
- Risk and evidence: POSTGRES_PASSWORD was a literal string in docker-compose.yml, which is typically committed to version control.
- Impact: the password was visible to anyone with read access to the repo, in the file itself.
- Implemented fix / commit: acf6103e3d010edb6491abc6c48e26aed31e27ff — replaced with a variable pulled from a local, gitignored source, with .env.example providing the placeholder shape.
- Production follow-up: rotate this credential and use a managed secrets store note that git history prior to this commit still contains the old plaintext value (git log/git blame would reveal it) — low real-world risk since it's synthetic lab data, but the same mistake with a real secret would require history rewriting (BFG/git filter-repo) and immediate rotation, not just a forward fix.
- How to verify: git grep POSTGRES_PASSWORD docker-compose.yml returns no literal value git ls-files | grep app.env shows only .env.example tracked.
---
## Finding 3 — Database and cache ports published to the host (category: ports)
- Risk and evidence: postgres and redis both published their ports to 127.0.0.1, despite the task explicitly disallowing this.
- Impact: any local process could connect directly to the database or cache, bypassing the app entirely.
- Implemented fix / commit: redis — 7b4a39bfef6ac4aa749889899ad04251ef24603a.
- Production follow-up: use docker exec + psql/redis-cli, or a short-lived SSH tunnel, for any debugging access instead.
- How to verify: docker inspect postgres/redis --format '{{json .NetworkSettings.Ports}}' returns null for both.
---
## Finding 4 — Application container ran as root (category: container user)
- Risk and evidence: Dockerfile created a dedicated non-root app user and chowned files to it, then set USER root right before CMD, undoing it.
- Impact: a compromised app process would have had root inside the container, widening the blast radius of any container-escape vulnerability.
- Implemented fix / commit: 3cc0a84b3a358a0f7445856bb4d9046c62d76040
- Production follow-up: consider --read-only and dropped Linux capabilities at the compose level for further hardening.
- How to verify: docker exec app-01 whoami → app.
---
## Finding 5 — nginx had a direct network path to Postgres and Redis (category: networks)
- Risk and evidence: nginx's networks: list originally included both frontend and backend.
- Impact: violated the task's required isolation and unnecessarily widened what a compromised nginx process could reach.
- Implemented fix / commit: 3b7a19d64db5a53026e5c81c4571bb1f0d16b3c6
- Production follow-up: in a larger deployment, apply equivalent segmentation via Kubernetes NetworkPolicies or cloud security groups.
- How to verify: docker exec nginx getent hosts postgres and redis both fail to resolve.
---
## Finding 6 — PostgreSQL data directory had no real persistence (category: persistence/backup)
- Risk and evidence: the named volume was mounted at /var/lib/postgresql/backup, not Postgres's real data directory the real directory was overridden by tmpfs, wiped on every recreate.
- Impact: any data written via /records would not have survived a container recreate — directly contradicting the task's required persistence proof.
- Implemented fix / commit: 3a48c7a23f2fe0cb96f6a434dca3fb67c67acb8a
- Production follow-up: implement scheduled off-host backups.
- How to verify: create a record via /records, docker compose up -d --force-recreate app-01 app-02 postgres, confirm the record is still returned.
---
## Finding 7 — No automatic restart, single instance of nginx/Postgres (category: availability)
- Risk and evidence: every service originally had restart: "no" or no policy at all there is also only ever one nginx and one postgres instance.
- Impact: an unexpected crash left a service down until manual intervention nginx and postgres are each single points of failure with no redundancy.
- Implemented fix / commit: b2b907d47b633bb4e173491d68ce5143445e82c2 — restart: unless-stopped added across services. Redundancy itself is out of scope for this exercise's architecture.
- Production follow-up: run Postgres with real HA (managed database or a replicated setup) and multiple nginx replicas behind a load balancer.
- How to verify: docker kill <container> and confirm it restarts on its own docker compose ps shows restart policy applied.
---
## Finding 8 — No centralized log aggregation or alerting (category: logging/monitoring)
- Risk and evidence: nginx and the app both emit structured JSON logs to stdout, viewable via docker compose logs, but nothing collects or retains them beyond the container's own buffer.
- Impact: logs are lost if a container is removed or the host restarts no automated alerting on an error-rate spike.
- Implemented fix / commit: N/A — out of scope for this exercise, documented as a known gap.
- Production follow-up: ship logs to a centralized store (Loki, ELK, or a managed logging service) with retention and error-rate alerting.
- How to verify: N/A until implemented.
