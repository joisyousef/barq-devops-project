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
