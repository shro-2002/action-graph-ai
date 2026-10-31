# Requirements Traceability Matrix — Action Graph AI

Source: Product Space × Wispr Flow Agentic AI Hackathon 2026, Problem 03 "Meeting-to-execution agent".
Deadline: 31 Oct 2026, 23:59 IST.

| ID | Requirement (official) | Implementation | Verified by |
|----|------------------------|----------------|-------------|
| R1 | Natural speech via Wispr Flow is the main input; handle fillers, digressions, self-corrections | Capture box is the Wispr Flow dictation target. `app/cleanup.py` strips fillers and resolves self-corrections ("Friday, no wait, Monday" → "Monday"); LLM pass does the same with context | `tests/test_core.py::test_self_correction*`, `test_fillers_removed` |
| R2 | Transcript ingestion with speaker attribution | `cleanup.parse_speakers` handles `Name:` / `[00:12] Name:` lines and unlabeled dictation; LLM attributes unlabeled lines when key is present | `test_speaker_parsing` |
| R3 | Extract decisions, action items, owners, deadlines | `app/extract.py`: Claude tool-use with a strict JSON schema, plus a deterministic fallback extractor. Deadlines resolved by `app/dates.py` relative to the meeting date | `test_extracts_actions_owners_deadlines`, `evals/run_eval.py` |
| R4 | Detect conflicts with earlier decisions stored in memory | SQLite cross-meeting memory. `app/conflicts.py` uses PyTorch cosine similarity on hashed subject vectors to find candidates, then deterministic value comparison with an explanation | `test_conflict_detected_across_meetings`, `test_no_conflict_same_value` |
| R5 | Create tasks in a tracker through an integration | `app/tracker.py` creates real GitHub Issues (REST API via `gh` token) in `shro-2002/action-graph-ai` | Manual: issue URLs come back in the UI |
| R6 | Reminders before deadlines | Background loop + `POST /api/reminders/run` produces reminders for actions due within the window. Posting a reminder comment to the issue needs a click | `test_reminders_due_window` |
| R7 | Weekly digest per person | `GET /api/digest` groups by owner: overdue, due this week, decisions made, done | `test_digest_groups_by_owner` |
| R8 | Confirmation step before anything is posted | Every extracted item starts as `pending`. Nothing reaches GitHub until the user approves the item and confirms the posting dialog | `test_nothing_posted_without_approval` |
| R9 | Cross-meeting memory + conflict detection = "real system" | Approving a conflicting decision supersedes the older one; the memory timeline and the graph show the history | `test_supersede_on_approval` |

## Judging criteria mapping

| Criterion (weight) | Evidence |
|---|---|
| Wispr Flow usage (20%) | Built by dictating prompts; the product's main input is Wispr Flow dictation; messy-speech handling is shown in the demo |
| Prototype quality and UX (20%) | One-screen flow: dictate, agent trace, review, approve, post. Graph, memory, reminders, digests, scorecard |
| AI integration (20%) | Claude tool-use extraction + deterministic guardrails (date resolution, owner validation, conflict rules) |
| Problem understanding (15%) | Memory and conflict detection are first-class; the confirmation gate covers everything posted |
| Innovation (10%) | Action graph across meetings, explainable conflicts, measurable scorecard |

## Blockers / dependencies

- `ANTHROPIC_API_KEY` in `.env` (user provides). Without it the deterministic extractor runs.
- GitHub token comes from `gh auth token` or `GITHUB_TOKEN`.
