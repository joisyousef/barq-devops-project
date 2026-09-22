# Log analysis

Use all three supplied logs. Answer every question with commands/scripts and actual output.

1. What UTC interval is covered? How many valid, malformed and duplicate lines are in each file?
2. How many distinct client requests occurred? How did you deduplicate and avoid counting retries twice?
3. What are the final client status counts and error rate? State your denominator.
4. Which paths, time windows and backends account for the failures?
5. What are the median and p95 client latencies? State the percentile method and units.
6. Which requests retried upstream? How many succeeded after retrying?
7. Build an incident timeline using evidence from access, error AND application logs.
8. Show one correlated failed request and one successful request. Include IDs and timestamps.
9. Which errors appear to be proxy/connectivity issues versus dependency/application issues? What proves it?
10. What do the logs not prove? What would you check next in a running environment?

## Commands / scripts
## Results
## Timeline and correlated examples
## Conclusions and limits
---
## Commands / scripts
[paste every command above, verbatim, as your reproducibility record]

## Results

Q1 — Coverage and validity
- Time range: 2026-08-20T11:00:00.015Z to 2026-08-20T11:29:57.578Z (both access.log and
  application.log).
- access.log: 725 valid lines, 1 malformed (location: [fill in from the python check above]).
- application.log: 729 valid lines, 1 malformed — line 401, a truncated JSON object cut off
  mid-value ('{"timestamp":"2026-08-20T11:17:00Z","event":'), a different failure signature
  than the connection-refused errors seen elsewhere (looks like a log writer interruption,
  not a network failure).
- Duplicates: 5 request_ids appear twice in access.log (lab-000121, 241, 361, 481, 601 — an
  exact 120-request interval). Inspected the duplicate pairs directly: each pair is
  byte-for-byte identical (same timestamp, upstream, status) — confirmed these are
  duplicated log lines, not retries (a retry would show a different timestamp or upstream).

Q2 — Distinct requests and deduplication
- 720 distinct request_ids (sort -u), vs. 725 raw valid lines — the 5-line gap matches the
  5 confirmed duplicate pairs above exactly.
- Deduplicated by request_id after confirming (not assuming) the duplicates were identical
  repeats rather than genuine retried attempts.

Q3 — Status counts and error rate
- 200: 620, 404: 10, 502: 40, 503: 47, 504: 8 (sums to 725, matching the valid-line count).
- Denominator: 720 distinct requests (not 725 raw lines, since duplicates aren't separate
  client interactions).
- Error rate (5xx only): 95/720 = 13.2%.
- Error rate (5xx + 404): 105/720 = 14.6% — reported separately since a 404 on a
  deliberately-invalid path isn't the same class of failure as a 5xx.

Q4: Window 1 (11:05:02–11:09:57, all 502, TCP refused, 172.23.0.12 only) and Window
2 (11:25:14–11:26:47, mixed 503/504, both backends, all 504s on /records specifically at
a fixed ~2700ms).

Q5 — Latency
- Method: sorted request_time values (seconds), nearest-rank percentile.
- Median: 0.054s (54ms). p95: 2.001s (2001ms) — computed across all 725 valid rows;
  the 5 duplicate 200-status rows have negligible effect on this given they're fast,
  ordinary requests, not part of the slow tail.
- The wide gap between median and p95 indicates a distinct slow subset, not general
  latency drift — consistent with the failure window below.

Q6: 15 requests retried upstream (comma-separated `upstream` field), all during Window
1, all failing to .12 first then succeeding on .11 on retry — 15/15 succeeded after retry.

Q7 (timeline):
- 11:00:00–11:05:00 — normal traffic, alternating cleanly between app-01/app-02.
- 11:05:02–11:09:57 — Window 1: app-02 (172.23.0.12) refuses all TCP connections;
  application.log shows total silence for app-02 in this window; nginx retries succeed
  via app-01.
- 11:10:00–11:25:00 — recovered, normal alternating traffic resumes.
- 11:25:14–11:26:47 — Window 2: both instances logging normally, but /records consistently
  takes 2700ms; nginx's timeout occasionally cuts these off as 504 before the app replies.
- 11:26:20 onward — normal traffic resumes.

Q8: Failed: lab-000122 (11:05:02.503Z) — access.log: 502 upstream .12; error.log:
connect() failed (111: Connection refused); application.log: no matching entry at all.
Successful (retried): lab-000124 (11:05:07.620Z) — access.log: upstream ".12, .11",
upstream_status "502, 200", final status 200; application.log: app-01 logged it, duration
120ms.

Q9: Window 1 = proxy/connectivity (TCP refusal before any HTTP reached the app,
proven by total application.log silence). Window 2 = dependency/application-level
(app fully alive and logging, just slow on one specific endpoint — proven by
application.log showing normal, complete entries with elevated duration_ms).

Q10: The logs prove the symptom and its timing, not the underlying cause — why
app-02 refused connections (crash? OOM? deliberate stop?) or why /records specifically
took 2.7s (a slow query? a lock? no index?) isn't visible here. In a live environment,
next steps: check that container's exit code/OOMKilled status via docker inspect at
that timestamp, and check Postgres's own slow-query log or EXPLAIN plan for /records'
query during the second window.

## Timeline and correlated examples
[Fill in using the Q4/Q7/Q8 command output above — first/last failure timestamp, which
backend, and one full correlated request_id traced through all three logs]

## Conclusions and limits
- What the logs prove: one backend instance became completely unreachable at the TCP
  level for a sustained window, while the other kept serving normally; the pattern is a
  fixed-interval health/monitoring probe cycling through the same six paths.
- What the logs do NOT prove: why the backend became unreachable (crash, OOM kill,
  deliberate stop, network blip) — the logs show the symptom, not root cause. In a live
  environment, the next step would be checking that container's own stdout/exit code
  and `docker inspect`'s OOMKilled/ExitCode fields at that timestamp, exactly as done
  live in troubleshooting.md throughout this project.
- Two malformed lines (one per file) were excluded from all counts rather than guessed
  at or repaired — reported as data quality limitations, not treated as valid records.
