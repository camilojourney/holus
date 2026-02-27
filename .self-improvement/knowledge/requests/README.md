# Knowledge Request Queue

Any agent can file a knowledge gap request here. Expert agents process these on startup.

## Request Format

Filename: `YYYY-MM-DD-<slug>.md`

Fields:
- **Filed by:** agent name
- **Priority:** low | medium | high
- **Related topic:** existing knowledge file
- **What I Need to Know:** description of the gap
- **Why I Need It:** what was blocked

Expert agents delete resolved requests after writing findings to `current/<topic>.md`.
