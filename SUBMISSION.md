# Submission readiness — 31 Oct 2026, ~18:40 IST (deadline 23:59 IST)

## Links

| What | Link |
|---|---|
| Problem statement (Problem 03) | https://theproductspace.in/ai-hackathon-details/problem-statement |
| Submission form | https://theproductspace.in/user-dashboard/submissions/agentic-ai-hackathons (needs your login; fields not checked) |
| Code and tracker repo | https://github.com/shro-2002/action-graph-ai (**private**) |
| Demo script | [DEMO.md](DEMO.md) |
| Earlier audit | [AUDIT.md](AUDIT.md) (unchanged evidence, `data/audit.db`) |

## Official brief vs. implementation

Read from the official page today. The brief's seven items match `RTM.md`.

| Brief item | Status | Evidence (today) |
|---|---|---|
| Transcript ingestion with speaker attribution | **Pass** | Fixed: one-paragraph dictation (`Priya: … Arjun: …` on one line) used to collapse into one speaker on the rules path. Now split on known names. Live Claude run on one paragraph: 3 utterances, Priya/Arjun/Priya. Test `test_inline_speaker_labels_from_one_paragraph_dictation` |
| Decisions, actions, owners, deadlines | Pass | Same live run: "Monday, no wait, Tuesday" → 2026-11-03, owner Arjun. Held-out with Claude P 1.0 / R 1.0 (18 cases, see AUDIT.md) |
| Conflicts with earlier decisions in memory | Pass | AUDIT.md §2; unchanged code |
| Tasks in a tracker via integration | Pass | Real GitHub issues #12–17, #20 (AUDIT.md). Fixed today: timed-out creates no longer duplicate (hidden per-item marker, looked up before failing). Network errors now return a 502 with a message instead of a 500 |
| Reminders before deadlines | **Pass, with a stated limit** | Scheduled: server checks every 5 min. Fixed: due-soon now escalates once to overdue and can be re-delivered. Delivered: GitHub issue comment (confirmed click, or automatic with `AUTO_POST_REMINDERS=1`), @mentioning the owner when `OWNER_GITHUB` maps them. Verified in browser: 2 Nov → "⏰ Due soon", 4 Nov → "⚠️ Overdue". Limit: no email/Slack of its own; GitHub's notification is the delivery channel |
| Weekly digest per person | **Pass, with a stated limit** | Per-person cards (overdue, due this week, coming up, done, decisions). New **Email** button opens a prefilled email; Copy as Markdown. Not sent automatically |
| Confirmation before anything is posted | Pass | `confirm:true` required, approved-only; rejected items never posted (AUDIT.md). Auto reminders are off by default and only comment on issues a human already confirmed |

Also fixed: API errors now stay on screen until **Dismiss** (verified: still visible after 4.5 s, dismiss works). LLM-fallback notes also stay up.

## Verified vs. not verified

Verified by me today: 30/30 tests (`pytest -q`); rules dev eval P 1.0 / R 1.0 unchanged; one live Claude extraction on the new paragraph handling; reminder escalation and Email link in the browser against an isolated DB (deleted afterwards); a read-only GitHub call for the marker lookup (20 issues visible, no false match); a failed post (bad repo) shows a sticky error and the item stays retryable.

**Not verified:**
- Wispr Flow dictation. You do this. I have not tested voice input.
- A live issue **create** with the new body marker. Same API call as before plus an HTML comment; your first demo post will show it. If it fails, the item stays approved and the error stays on screen.
- Automatic reminder delivery against real GitHub (covered by a unit test with a stubbed tracker only).
- Whether Wispr turns a spoken "colon" into `:`. Rehearse once (DEMO.md step 3).

## Remaining blockers

| # | Blocker | Needs | Recommendation |
|---|---|---|---|
| 1 | Repo is **private**; judges can't see code or issues | Your decision | Make `shro-2002/action-graph-ai` public. History was scanned for secrets in the audit (none found); `.env` is gitignored. Old issues #1–20 stay as history; demo issues get new numbers |
| 2 | Last 2 commits (`d969111`, `1c65386`) and the docs commit are **not pushed** | Your OK | `git push origin main` |
| 3 | No Wispr Flow evidence yet (20% of score) | You | Record per DEMO.md and capture the checklist below |
| 4 | No hosted URL | Optional | Not required by the brief text. Judges run it locally or watch the video |
| 5 | Submission form fields unknown (behind login) | You | Open the form early; fill repo link, video link, short description |

Separate public demo repo: not needed if you make the main repo public. If you'd rather keep code and test issues private, the alternative is a new public repo (e.g. `shro-2002/action-graph-ai-demo`) used only as the tracker (`GITHUB_REPO=…` in `.env`, restart server) plus a public copy of the code. That is more moving parts tonight. I have not created or changed any repo.

## Recording steps

1. Rehearse once on a throwaway DB: `DB_PATH=data/rehearsal.db .venv/bin/uvicorn app.main:app --port 8766`, then delete `data/rehearsal.db`. Note: rehearsal posts create real issues too; skip posting in rehearsal.
2. Recording uses the running server on :8765 (`data/demo.db`, empty).
3. Screen recorder on, with the Wispr Flow overlay visible and mic audio on.
4. Follow DEMO.md. Keep it under 3:00.
5. Upload (YouTube unlisted or Loom), then open the link in a private window to confirm it plays logged out.

## Wispr Flow evidence checklist

- [ ] Video shows the Wispr hotkey or overlay active while text appears in the box (not pasted).
- [ ] At least one live self-correction and filler, with the corrected result visible.
- [ ] Screenshot of Wispr Flow history or dashboard showing today's sessions.
- [ ] 2–3 screenshots or a short clip of dictating prompts to Claude Code while building.
- [ ] Wispr usage stats from the app if the form asks.

## Final checklist

- [ ] Push (blocker 2). Make the repo public (blocker 1). Open the repo logged out to check.
- [ ] Record and upload video; link works logged out.
- [ ] Submit before 23:59 IST; screenshot the confirmation.
- [ ] LinkedIn posts: separate deadline, 1 Nov 23:59 IST.
