# Submission package — Action Graph AI

Product Space × Wispr Flow Agentic AI Hackathon 2026 · Problem 03: Meeting-to-execution agent · Deadline 31 Oct 2026, 23:59 IST

## Links

| What | Link |
|---|---|
| Problem statement | https://theproductspace.in/ai-hackathon-details/problem-statement |
| Submission form (login required) | https://theproductspace.in/user-dashboard/submissions/agentic-ai-hackathons |
| LinkedIn post submission (due 1 Nov 23:59 IST) | "Submit posts" on https://theproductspace.in/ai-hackathon-details |
| Repository | https://github.com/shro-2002/action-graph-ai (private until you approve) |
| Demo script and transcripts | [DEMO.md](DEMO.md) |

## Requirements check (official brief, Problem 03)

| Brief item | Status | Evidence |
|---|---|---|
| Transcript ingestion with speaker attribution | Met | Release run and dry run: 8/8 speakers from one dictated paragraph |
| Decisions, action items, owners, deadlines | Met | Held-out set with Claude: precision 1.0, recall 1.0 (18 cases) |
| Conflicts with earlier decisions in memory | Met | Both contradictions flagged with reasons in every run |
| Tasks in a tracker through an integration | Met | Real GitHub issues #21–26 created in the release check |
| Reminders before deadlines | Met, with a limit | Checked every 5 min; delivered as an issue comment after a confirm click |
| Weekly digest per person | Met, with a limit | Built per person; the user sends it (Copy or Email link) |
| Confirmation before anything is posted | Met | Dialog plus `confirm: true` server check; rejected items never posted |

The public pages do not mention a deployed URL. The submission form is behind login, so its fields are unverified: **open it first**.

## Copy-paste fields

**Title**
Action Graph AI: speak the meeting, get execution with memory

**Problem (one paragraph)**
Decisions made in meetings get lost, and later meetings quietly contradict them. Notes and summaries record what was said, but nobody checks a new decision against what the team already agreed, and action items never reach the tracker with an owner and a date.

**Solution**
You dictate a meeting with Wispr Flow, fillers and self-corrections included. Claude turns it into speaker-attributed decisions and action items with owners and real dates. Every new decision is checked against approved decisions from earlier meetings, and contradictions are flagged with a plain-English reason ("paid tier pricing was $9 per seat on 24 Oct, now $12"). Nothing leaves the app until a person approves each item and confirms. Approved items become GitHub issues; a superseded decision's old issue gets a back-link. Reminders flag overdue and due-soon actions, and each person gets a weekly digest.

**Architecture**
Wispr Flow dictation → FastAPI → Claude extraction with a strict JSON schema (rules extractor as a labelled fallback) → deterministic guardrails (dates, owners) → conflict check against SQLite decision memory (PyTorch n-gram similarity plus deterministic rules) → human approval → confirmation → GitHub Issues REST API. A background loop builds reminders; the UI shows memory, an action graph, reminders, digests and a scorecard. One agent with deterministic guardrails, not a multi-agent system.

**Tech stack**
Python 3.13, FastAPI, Pydantic, SQLite, Anthropic API (Claude Sonnet 5.5), PyTorch (CPU), GitHub REST API, vanilla JavaScript with Cytoscape.js, pytest. Optional provider: Meta Muse Spark 1.3 (`LLM_PROVIDER=meta`).

**Key differentiators**
- Cross-meeting decision memory with explainable conflict detection, not a summarizer.
- A human approval gate and explicit confirmation before any external write; rejected items never leave.
- Real GitHub issues with supersede back-links, idempotent against retries and double clicks.
- Measured, not claimed: 18 held-out messy-speech cases (Claude P 1.0 / R 1.0), plus a side-by-side comparison with Meta Muse Spark (P 0.88 / R 0.83, slower and costlier, kept optional).
- Never hides which model ran: a failed provider falls back to the rules extractor, labelled as such, never to another LLM.

**Honest limitations**
- Runs locally; there is no hosted deployment. Judges need their own Anthropic key and GitHub token to run it.
- Reminder delivery is a GitHub issue comment after a confirm click. Fully automatic delivery exists behind a setting but was not shown or tested against GitHub.
- Digests are not sent by the app; the user copies or emails them.
- The held-out set is small (18 cases) and was written by an AI assistant from the same model family, so phrasing bias is possible.
- The rules fallback is much weaker (held-out P 0.50 / R 0.39) and is always labelled.
- Graph labels can overlap on busy graphs.

## Repository security check (31 Oct, before going public)

- Searched all commits and tracked files for Anthropic, GitHub, Meta and AWS keys, bearer tokens and private keys: none found.
- No `.env`, database or log file has ever been committed; `.env` and `*.db` are gitignored.
- Personal data: your name `shro-2002` and email address appear as the author of every commit, and the email also appears in an older committed version of this file. Making the repo public exposes them. Rewriting history to remove them is possible but not recommended tonight.
- Test data that becomes visible: issues #1–26 (titles mention fictional people Priya, Nisha, Dev, Karan); #21–26 are titled `[E2E TEST]`.

## Final checklist

**Recording (see DEMO.md)**
- [ ] Header reads "Claude extraction on" and "0 meetings" before you start.
- [ ] Rehearse "Nisha colon" in Wispr Flow once.
- [ ] Screen recorder on with mic audio; Wispr overlay visible while you dictate.
- [ ] Follow the script; keep it under 3:00.

**Wispr Flow evidence (20% of score)**
- [ ] Video shows dictation appearing in the capture box live.
- [ ] Screenshot of the Wispr Flow history or dashboard with today's sessions.
- [ ] 2–3 screenshots or a short clip of dictating prompts to Claude Code while building.
- [ ] Wispr usage stats from the app, if the form asks.

**Upload and links**
- [ ] Upload as YouTube unlisted or Loom.
- [ ] Open the video link in a private browser window; it plays logged out.
- [ ] Approve making the repo public; then open it in a private window and check the README renders.

**Submit**
- [ ] Fill the form with the fields above, the repo link and the video link.
- [ ] Submit before 23:59 IST and screenshot the confirmation.
- [ ] LinkedIn: 3 posts (kickoff, while building, final demo), tag Product Space, submit links plus an engagement screenshot by 1 Nov 23:59 IST.
