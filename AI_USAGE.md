# AI usage disclosure

Write None if no AI was used. Otherwise record each use:

- Tool/model:
- Purpose:
- Files or decisions affected:
- What you changed or rejected:
- How you independently verified it:
- Related commit:

You may use AI and external resources. You must understand and demonstrate the work.
---
- Tool/model: Claude (Anthropic), claude.ai chat
- Purpose: Asked how to structure troubleshooting.md entries consistently and
  what format to use for commit messages so they'd match across every fix.
- Files or decisions affected: troubleshooting.md, commit message format used across the project.
- What you changed or rejected: adopted the suggested entry structure
  (symptom/hypothesis/command/output/root cause/fix/retest/commit) and the
  commit message format (one-line summary + symptom/root cause/fix/verified
  body). I wrote the actual content of every entry myself, based on commands
  I ran and output I actually saw — the AI only suggested the shape, not the
  content.
- How you independently verified it: every entry only contains commands I
  ran myself and real output I copied from my terminal. 
- Related commit: N/A 
---
- Tool/model: Claude (Anthropic), claude.ai chat
- Purpose: Asked how to test that the backend is inaccessable 
  after removing 'backend' from nginx network
- Files or decisions affected: docker-compose.yml
- What you changed or rejected: none
- How you independently verified it: I run the commands it gave me which are 
  docker exec nginx getent hosts postgres
  docker exec nginx getent hosts redis  
- Related commit: 3b7a19d64db5a53026e5c81c4571bb1f0d16b3c6
---
- Tool/model: Claude (Anthropic), claude.ai chat
- Purpose: asked why stopping postgres produced nginx's own 504 error instead of the app's documented 503 response.
- Files or decisions affected: nginx/nginx.conf, troubleshooting.md.
- What you changed or rejected: the first suggested theory was that the app had no connection timeout configured.
- How you independently verified it: ran the actual stop-postgres/curl/logs sequence myself and read the real duration_ms value before accepting any explanation.
- Related commit: aa7c7defa76eb9ddd5061d5e4ffa31386ca83958
---
- Tool/model: Claude (Anthropic), claude.ai chat
- Purpose: asked for an implementation of both scripts against the task's stated
  requirements (bounded waits, PASS/FAIL, non-zero exit).
- Files or decisions affected: validate.py, failure_test.py.
- What you changed or rejected: ran both scripts as given found and fixed a real bug
  myself in CI where the isolation check needed to also treat a timeout as proof of
  isolation, since the GitHub runner's DNS behaves differently than my local machine.
- How you independently verified it: ran both scripts locally with real PASS/FAIL output
  before ever relying on them in CI.
- Related commit: dd1e8768233070e2767e6127ba7a7049bd2475bf / 47910e3126539abfef9fa74e8d18cc2e14d9410e
---
