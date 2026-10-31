# Action Graph AI

**Speak the meeting. Get execution, not a summary.**
A voice-first meeting-to-execution agent with cross-meeting memory, explainable conflict detection, a human approval gate, and real GitHub Issues integration.

Built for the Product Space × Wispr Flow Agentic AI Hackathon 2026, Problem 03: Meeting-to-execution agent.

## What it does

1. **Capture by voice.** You dictate the meeting (or paste a transcript) into the capture box with Wispr Flow. Fillers, repeated words and self-corrections are expected: "launch on Friday, no wait, Monday" becomes "launch on Monday".
2. **Attribute speakers.** `Name:` and `[00:12] Name:` labels are parsed, including several labels inside one dictated paragraph. Unlabeled dictation continues the previous speaker.
3. **Extract.** Claude (tool use with a strict JSON schema) pulls out decisions (subject → value) and action items (owner, deadline). Deterministic guardrails then resolve relative dates against the meeting date and match owners to attendees. If no API key is set, or the call fails, a rule-based extractor runs instead. The UI always says which extractor ran.
4. **Check memory.** Every new decision is compared with approved decisions from past meetings. PyTorch cosine similarity over hashed n-gram vectors finds decisions about the same subject. Fixed rules then flag a clash when the values differ or one decision reverses the other. Each flag comes with a plain-English reason, e.g. "Contradicts 'Sprint planning' (2026-10-24, Priya): launch date was “November 14”, now “November 28”."
5. **Human approval.** Every item starts as *pending*. You can edit the owner, deadline or value, then approve or reject. Approving a conflicting decision marks the old one *superseded*.
6. **Post to the tracker.** A confirmation dialog lists exactly what will be created. Only then are GitHub Issues created. If a superseded decision already had an issue, that issue gets a back-link comment.
7. **Follow through.** Reminders for actions due within a window (or overdue) are checked every 5 minutes or on demand, and a due-soon reminder escalates to overdue. Delivery is a comment on the action's GitHub issue, after a confirm (or automatically with `AUTO_POST_REMINDERS=1`). A weekly digest per person groups their work into overdue, due this week, coming up, done, and decisions made; you send it with Email or Copy.

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

Optional settings:

| Variable | Default | Effect |
|---|---|---|
| `DB_PATH` | `data/actiongraph.db` | SQLite file; use a separate one per demo or audit run |
| `LLM_PROVIDER` | `anthropic` | `anthropic` (Claude, verified default) or `meta` (Meta Muse Spark via its OpenAI-compatible API, optional). An unknown value is an error. If the chosen provider fails, the rules extractor runs and is labelled `rules`; it never switches to the other LLM |
| `META_API_KEY` / `META_API_BASE` / `META_MODEL` | none / `https://api.meta.ai/v1` / `muse-spark-1.3` | Only used when `LLM_PROVIDER=meta` |
| `AUTO_POST_REMINDERS` | off | `1` delivers reminders automatically as comments on the action's GitHub issue (that issue was already human-confirmed). Off: each reminder is posted with a confirmed click |
| `OWNER_GITHUB` | none | `Dev=dev-login,Karan=karan-login`: reminder comments @mention the owner so GitHub notifies them |
| (reminder window) | 48 h | Reminders cover actions due within 48 h or overdue; a due-soon reminder escalates once to overdue |

## Verify it

```bash
.venv/bin/python -m pytest -q          # 31 tests: cleanup, inline speaker labels, dates, extraction, conflicts, supersede, approval gate, double-submit, timeout retry, marker spoofing, reminders + escalation + delivery, digest, CSRF + host checks
.venv/bin/python -m evals.run_eval     # precision/recall on labeled messy-speech cases (rules)
.venv/bin/python -m evals.run_eval --llm   # same cases through Claude
.venv/bin/python -m evals.run_eval --holdout [--llm]   # 18 held-out cases, never used for tuning
```

| Extractor | Dev set (6 cases, 7 items) | Held-out set (18 cases, 18 items) | Note |
|---|---|---|---|
| Claude (`claude-sonnet-5-5`) | P 0.857 / R 0.857 | P 1.0 / R 1.0 | Neither set was used to tune the prompt. Held-out cases were written by the same AI assistant family, so phrasing bias is possible |
| Rules fallback | P 1.0 / R 1.0 | P 0.50 / R 0.39 | Tuned on the dev set; the held-out score is its real accuracy. It is a degraded fallback, always labelled in the UI |

### Provider comparison (31 Oct 2026, same cases, same frozen scoring)

`python -m evals.compare_providers` with `LLM_PROVIDER=anthropic` or `meta`. Results after the shared transcript-cleaning prompt change: `evals/compare_*_v2.json`.

| | Claude `claude-sonnet-5-5` | Meta `muse-spark-1.3` |
|---|---|---|
| Dev P / R | 0.857 / 0.857 | 1.0 / 0.857 |
| Held-out P / R | **1.0 / 1.0** | 0.882 / 0.833 |
| Schema-valid responses | 24/24 | 24/24 |
| Deadlines correct | 16/16 | 14/16 |
| Speakers / contradictions (demo pair) | 8/8 / 2/2 | 8/8 / 2/2 |
| Fillers or corrections left in cleaned turns | 0 | 0 |
| Mean latency per case | 2.5–3.8 s | 6.8–7.7 s (max 21 s) |
| Cost of 24 cases | $0.13 | $0.19 (reasoning tokens bill as output) |

Claude stays the default; Muse is an optional provider.

Decisions are scored the way the conflict engine compares them: subject similarity plus normalized values, so "Nov 28" equals "November 28". The set is small (6 cases, 7 expected items).

## Safety

- Nothing is posted without an approved item **and** an explicit `confirm: true` from the dialog. A test enforces this.
- State-changing API calls require an `X-Action-Graph` header (blocks cross-site requests) and the Host header must be allowlisted (blocks DNS rebinding). Every value shown in the UI is HTML-escaped. Inputs are length-limited with Pydantic. SQL is parameterized, and the editable columns are whitelisted.
- Secrets stay in `.env` (gitignored). The app ignores Claude Code's `ANTHROPIC_BASE_URL` and talks to the public API unless `ANTHROPIC_API_BASE` is set.

## Built with voice

The prompts and specs for this project were dictated to Claude Code with Wispr Flow. Wispr Flow is the product's input method, not a code dependency.
