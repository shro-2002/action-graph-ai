# Action Graph AI

**Speak the meeting. Get execution, not a summary.**
A voice-first meeting-to-execution agent with cross-meeting memory, explainable conflict detection, a human approval gate, and real GitHub Issues integration.

Built for the Product Space × Wispr Flow Agentic AI Hackathon 2026, Problem 03: Meeting-to-execution agent.

## What it does

1. **Capture by voice.** You dictate the meeting (or paste a transcript) into the capture box with Wispr Flow. Fillers, repeated words and self-corrections are expected: "launch on Friday, no wait, Monday" becomes "launch on Monday".
2. **Attribute speakers.** `Name:` and `[00:12] Name:` labels are parsed, and unlabeled dictation continues the previous speaker.
3. **Extract.** Claude (tool use with a strict JSON schema) pulls out decisions (subject → value) and action items (owner, deadline). Deterministic guardrails then resolve relative dates against the meeting date and match owners to attendees. If no API key is set, or the call fails, a rule-based extractor runs instead. The UI always says which extractor ran.
4. **Check memory.** Every new decision is compared with approved decisions from past meetings. PyTorch cosine similarity over hashed n-gram vectors finds decisions about the same subject. Fixed rules then flag a clash when the values differ or one decision reverses the other. Each flag comes with a plain-English reason, e.g. "Contradicts 'Sprint planning' (2026-10-24, Priya): launch date was “November 14”, now “November 28”."
5. **Human approval.** Every item starts as *pending*. You can edit the owner, deadline or value, then approve or reject. Approving a conflicting decision marks the old one *superseded*.
6. **Post to the tracker.** A confirmation dialog lists exactly what will be created. Only then are GitHub Issues created. If a superseded decision already had an issue, that issue gets a back-link comment.
7. **Follow through.** Reminders for actions due within a window (or overdue) are generated every 5 minutes or on demand. Each one can be posted to its issue after a confirm. A weekly digest per person groups their work into overdue, due this week, coming up, done, and decisions made.

Views: Meeting workspace · Action graph (meetings, people, decisions, actions, conflict edges) · Decision memory timeline · Reminders · Weekly digest · Scorecard.

## Architecture

```
Wispr Flow dictation ─▶ FastAPI ─▶ cleanup (fillers, self-corrections, speakers)
                                 ─▶ extract (Claude tool-use │ rules fallback) ─▶ validate (dates, owners)
                                 ─▶ conflicts (PyTorch similarity + deterministic rules) ◀─ SQLite memory
                                 ─▶ pending queue ─▶ human approve/edit ─▶ confirm ─▶ GitHub Issues
                                 ─▶ reminder loop · weekly digest · action graph
```

It is a single agent with deterministic guardrails, by design. There is no multi-agent orchestration: the hard parts (memory, conflicts, approval) are state and rules, not more LLM calls.

| File | Role |
|---|---|
| `app/cleanup.py` | Filler removal, self-correction resolution, speaker parsing |
| `app/dates.py` | Spoken deadline → ISO date |
| `app/extract.py` | Claude extraction, rule fallback, validation guardrails |
| `app/conflicts.py` | PyTorch candidate retrieval + deterministic conflict rules |
| `app/service.py` | Pipeline, approval state machine, posting, reminders, digest, graph |
| `app/tracker.py` | GitHub Issues REST integration |
| `app/main.py` | FastAPI routes, reminder loop |
| `static/` | UI (vanilla JS + Cytoscape) |

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
cp .env.example .env   # add ANTHROPIC_API_KEY; GITHUB_REPO defaults to shro-2002/action-graph-ai
.venv/bin/uvicorn app.main:app --port 8765
```

Open http://localhost:8765. The GitHub token comes from `GITHUB_TOKEN` or `gh auth token`.

## Verify it

```bash
.venv/bin/python -m pytest -q          # 26 tests: cleanup, dates, extraction, conflicts, supersede, approval gate, double-submit, reminders, digest, CSRF + host checks
.venv/bin/python -m evals.run_eval     # precision/recall on labeled messy-speech cases (rules)
.venv/bin/python -m evals.run_eval --llm   # same cases through Claude
.venv/bin/python -m evals.run_eval --holdout [--llm]   # 18 held-out cases, never used for tuning
```

| Extractor | Dev set (6 cases, 7 items) | Held-out set (18 cases, 18 items) | Note |
|---|---|---|---|
| Claude (`claude-sonnet-5-5`) | P 0.857 / R 0.857 | P 1.0 / R 1.0 | Neither set was used to tune the prompt. Held-out cases were written by the same AI assistant family, so phrasing bias is possible |
| Rules fallback | P 1.0 / R 1.0 | P 0.50 / R 0.39 | Tuned on the dev set; the held-out score is its real accuracy. It is a degraded fallback, always labelled in the UI |

Decisions are scored the way the conflict engine compares them: subject similarity plus normalized values, so "Nov 28" equals "November 28". The set is small (6 cases, 7 expected items).

## Safety

- Nothing is posted without an approved item **and** an explicit `confirm: true` from the dialog. A test enforces this.
- State-changing API calls require an `X-Action-Graph` header (blocks cross-site requests) and the Host header must be allowlisted (blocks DNS rebinding). Every value shown in the UI is HTML-escaped. Inputs are length-limited with Pydantic. SQL is parameterized, and the editable columns are whitelisted.
- Secrets stay in `.env` (gitignored). The app ignores Claude Code's `ANTHROPIC_BASE_URL` and talks to the public API unless `ANTHROPIC_API_BASE` is set.

## Built with voice

The prompts and specs for this project were dictated to Claude Code with Wispr Flow. Wispr Flow is the product's input method, not a code dependency.
