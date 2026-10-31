# Judge-readiness audit — 31 Oct 2026, ~17:50 IST

Scope: everything below was run today against the real app (Claude `claude-sonnet-5-5` extraction, real GitHub Issues in `shro-2002/action-graph-ai`). An isolated database (`data/audit.db`, port 8766) was used so the demo database was not touched. Nothing here is mocked unless it says so.

**Caveat on requirements.** I could not find the official problem statement online, and it is not in the repo. The requirement list below is the one recorded in `RTM.md` ("Problem 03: Meeting-to-execution agent"). Re-check it against the official brief before you submit.

## 1. Traceability matrix

| ID | Requirement | Where | Evidence from today | Tests | Status |
|---|---|---|---|---|---|
| R1 | Natural speech via Wispr Flow is the input; fillers, digressions, self-corrections | `app/cleanup.py`, Claude system prompt in `app/extract.py` | Browser run: "seven days, no sorry, ten days" became 10 days; football and laptop small talk produced no items. Held-out set: 18/18 with Claude, including owner and deadline corrections | `test_self_correction*`, `test_fillers_removed`, held-out eval | **Partial.** Code path passes. Live Wispr Flow dictation **not tested** (an agent cannot dictate) |
| R2 | Transcript ingestion with speaker attribution | `cleanup.parse_speakers`, Claude `utterances` | 6 utterances and 3 speakers attributed correctly. Unlabeled dictation case passed on held-out | `test_speaker_parsing` | Pass |
| R3 | Extract decisions, actions, owners, deadlines | `app/extract.py`, `app/dates.py` | Meeting 1: 4/4 items correct (Thursday → 2026-10-29, next Monday → 2026-11-02). Held-out with Claude: P 1.0 / R 1.0 (18 items). Rules fallback on held-out: **P 0.50 / R 0.39** | `test_extracts_actions_owners_deadlines`, `evals/` | Pass with Claude. Fallback is weak |
| R4 | Detect conflicts with earlier decisions in memory | `app/conflicts.py`, `service.memory()` | Meeting 2 flagged both contradictions with reasons: "$9 → $12 per seat" and "14 days → 10 days", each citing the earlier meeting, date and speaker | `test_conflict_detected_across_meetings`, `test_no_conflict_same_value` | Pass |
| R5 | Create tasks in a tracker through an integration | `app/tracker.py`, `service.post()` | Real issues #12–17 and #20 created from the UI. **Bug found and fixed:** two concurrent posts of one item created duplicates (#18, #19). Repo is **private** | `test_nothing_posted_without_approval`, new `test_concurrent_post_creates_one_issue` | Pass (after fix). Judges cannot see private issues |
| R6 | Reminders before deadlines | `service.run_reminders`, 5-minute loop | "Overdue: Dev …" and "Due soon: Karan …" generated as of 1 Nov. One posted as a real GitHub comment after confirmation | `test_reminders_due_window` | **Partial.** Not delivered to the person (no email/Slack). One reminder per item ever, so a "due soon" never becomes "overdue" |
| R7 | Weekly digest per person | `service.digest`, Digest tab | Correct buckets for weeks of 26 Oct and 2 Nov (overdue, due this week, coming up, decisions made) | `test_digest_groups_by_owner` | **Partial.** Delivery is copy-to-clipboard only |
| R8 | Confirmation before anything is posted | `PostIn.confirm`, status gate | `confirm:false` → 400. Pending item → "not approved". Rejected item excluded from the dialog and never posted | `test_nothing_posted_without_approval` | Pass |
| R9 | Cross-meeting memory as a real system | SQLite memory, supersede on approve | Memory tab shows both subjects with the superseded value. Old issues #12 and #14 got "Superseded by #16/#17" comments | `test_supersede_on_approval` | Pass. Superseded issues are commented, not closed |

| Judging criterion | Evidence | Status |
|---|---|---|
| Wispr Flow usage (20%) | README claims voice-built. No recording, screenshots or transcript of Wispr use exist in the repo | **Not evidenced** |
| Prototype quality / UX (20%) | Full flow works in the browser. Mobile has no horizontal scroll. Loading shows a step trace. Errors show as toasts | Pass, with cosmetic issues (section 4) |
| AI integration (20%) | Claude tool-use plus deterministic date, owner and conflict guardrails. Held-out P/R measured | Pass |
| Problem understanding (15%) | Memory, conflicts, approval gate, supersede back-links | Pass |
| Innovation (10%) | Action graph, explainable conflicts, scorecard | Pass |

## 2. Browser end-to-end walkthrough (first-time judge path)

1. **Pricing review, 26 Oct.** Typed into the capture box (Nisha, Dev, Karan, with fillers and a sports digression). Claude returned 2 decisions and 2 actions, all correct, in about 15 s. Approved all four. The confirmation dialog listed exactly those 4. Confirm created GitHub #12–15, checked with `gh`.
2. **Pricing follow-up, 2 Nov.** Price changed to $12, trial "seven, no sorry, ten days", a vague "might look into a churn dashboard" (correctly not extracted), and one real action. Two red conflict cards appeared with reasons. Approved both decisions and rejected the action. The dialog showed only the 2 decisions. Posted #16 and #17. Rejected item: status `rejected`, no issue.
3. **Memory** tab: $9 and 14 days marked superseded; $12 and 10 days current.
4. **Action graph**: 11 nodes, conflict edges present. The first screenshot was blank because it was taken before layout finished; the second rendered.
5. **Reminders** as of 1 Nov 09:00: one overdue and one due soon. "Post to issue" created a real comment. The native `confirm()` was stubbed in the test browser because the automation cannot click native dialogs; the code calls it.
6. **Weekly digest** and **Scorecard**: values consistent with the above.

## 3. Held-out extraction challenge

`evals/holdout_cases.json`: 18 new scenarios (vague intent, missing owners, owner and value corrections, a conflict resolved inside the meeting, mixed relative dates, an action restated 3×, a decision restated 3×, social chatter with "I'll grab coffee", hypotheticals, a request nobody accepted, unlabeled dictation, a Friday-relative weekday, a reversal). Expectations were written before running. Scoring code is unchanged.

| Extractor | Precision | Recall | TP / FP / FN |
|---|---|---|---|
| Claude `claude-sonnet-5-5` | 1.00 | 1.00 | 18 / 0 / 0 |
| Rules fallback | 0.50 | 0.39 | 7 / 7 / 11 |

Raw Claude output was spot-checked on 4 cases: null owner kept null, Zeplin chosen over Figma, EU decision deduplicated, "not in Q1" plus Sara's action. Rules failures: missing-owner tasks dropped; "Sam, sorry, not Sam, Priya" → Sam; "end of next week" → Mon 9 Nov; "I'll grab coffee" became a task; restated decision became an action; unlabeled dictation, the "Tuesday next week" correction and the second owner in a sentence were all missed.

Limits: 18 cases is small, and I wrote them. I am the same model family as the extractor, so subject wording may line up more easily than with human-written labels. Claude ran once (no variance measured).

## 4. UI and tracker audit

Fixed today:
- **Critical:** duplicate GitHub issues on concurrent submit. Fixed with a process-wide post lock (`app/service.py`). Regression test added. Re-verified live: 2 parallel posts → 1 issue (#20) + "not approved (status posted)".
- **Honesty:** the scorecard showed the tuned rules set as "100% / 100%" with no label. Every P/R tile now says "dev set (rules tuned on it)" or "held-out set (never tuned on)".

Verified working: a tracker rejection (GitHub 404, bad repo) shows "0 posted, 1 failed: GitHub 404: Not Found", the item stays `approved` and can be retried. A sequential retry of a posted item is refused. No API key shows a "Rules-only extraction" pill and "· rules" in the trace.

Open, not fixed (lower priority):
- The failure toast disappears after 3.5 s; the card itself shows no error.
- If GitHub creates the issue but the response times out (20 s), the item stays `approved` and a retry duplicates it. Rare.
- An LLM failure mid-run is shown only by a toast plus "· rules" in the trace.
- Graph labels overlap (Karan's label sits under a decision label).
- The rules extractor leaves "by Friday" inside the task text.

## 5. Startup, security, reproducibility

- A fresh `git clone` of the remote, venv, `pip install -r requirements.txt` and `pytest` → 25 passed (remote HEAD, before today's fix); the server booted and `/` returned 200. Locally, with today's changes: 26 passed.
- No secrets in git history (searched for `sk-ant`, `ghp_`, `github_pat`, and filled `ANTHROPIC_API_KEY=`). `.env` is gitignored and `/static/../.env` → 404.
- Host `evil.com` → 400. POST without `X-Action-Graph` → 403.
- **No deployment exists.** Judges must run it locally with their own Anthropic key and a GitHub token. I did not deploy (needs your approval and money).
- README does not pin a Python version (tested on 3.13).

## 6. Blockers for submission, in priority order

| # | Blocker | Who | Fix |
|---|---|---|---|
| 1 | Repo `shro-2002/action-graph-ai` is **private**: judges cannot open the code or the issues | You | Make it public (history scan found no secrets) or add judges as collaborators |
| 2 | **No Wispr Flow evidence** (20% of the score) | You | Record a live dictation in the demo plus the checklist below |
| 3 | Today's fixes are **uncommitted** (lock fix, held-out eval, scorecard labels, README) | You approve, I commit | Commit and push |
| 4 | Demo state is dirty: issues #1–20 include test and audit issues and a duplicate (#19); `data/actiongraph.db` holds old runs | You approve | Close test issues (or use a fresh demo repo); start the demo from an empty DB |
| 5 | Official submission requirements not confirmed (deployed URL? video length? form fields?) | You | Check the brief. If a live URL is required, decide on hosting (costs; a hosted app posting with your token needs locking down) |
| 6 | Reminders and digest are generated but not delivered | Optional | Say so in the video: "posted to the issue on confirm / copied to Slack" |

## 7. Three-minute demo script (scenario verified end-to-end today)

Before recording: empty DB, server on 8765, the GitHub issues tab open, Wispr Flow running. Pre-run meeting 1 if you want to save 15 s.

| Time | Do | Say |
|---|---|---|
| 0:00–0:15 | Landing screen | "Meetings produce decisions that get lost, and quietly contradict each other. Action Graph turns spoken meetings into tracked work, and remembers what you decided." |
| 0:15–0:50 | Meeting 1 "Pricing review", 26 Oct. **Dictate with Wispr Flow**: *"Nisha: Okay so um, for the paid tier we're going with seat-based pricing, nine dollars per seat. Dev: I'll, uh, update the pricing page copy by Thursday. Karan: And the free trial stays at fourteen days. Nisha: Karan, can you set up the Stripe test products by next Monday?"* → Run agent | "Real speech, fillers and all. Claude pulls out two decisions and two actions, with owners and actual dates." |
| 0:50–1:10 | Approve all → Review & post → Confirm → switch to the GitHub tab | "Nothing leaves without my approval and an explicit confirm. There are the issues." |
| 1:10–1:50 | Meeting 2 "Pricing follow-up", 2 Nov. **Dictate**: *"Nisha: Finance came back, we're changing the paid tier to twelve dollars per seat. Karan: And the trial, we're cutting it to seven days, no sorry, ten days. Dev: I might look into a churn dashboard at some point."* → Run | "I changed my mind mid-sentence, and someone said something vague. Watch." Point at: 10 days, not 7; no task for the vague remark; two red conflict cards. |
| 1:50–2:15 | Read one conflict reason → Approve both → Post → open old issue #N, show the "Superseded by" comment | "It checked memory: we said nine dollars on the 26th. Approving supersedes the old decision, and the tracker stays consistent." |
| 2:15–2:35 | Memory tab, then Action graph | "Every decision's history across meetings, and who owns what." |
| 2:35–2:50 | Reminders: check as of 1 Nov → one overdue, one due soon → Post to issue. Digest → Copy | "Follow-through: reminders and a weekly digest per person." |
| 2:50–3:00 | Scorecard, held-out tile | "Measured, not claimed: 18 held-out messy-speech cases. Built by voice with Wispr Flow." |

## 8. Wispr Flow evidence checklist

- [ ] Demo video shows the Wispr Flow hotkey or overlay visibly active while text appears in the capture box (not pasted).
- [ ] At least one live self-correction ("no sorry") and filler in the dictated text, with the corrected result visible.
- [ ] Screenshot of the Wispr Flow history or dashboard showing today's dictation sessions for this project.
- [ ] 2–3 screenshots or a short clip of dictating prompts to Claude Code while building (supports "built by voice").
- [ ] One sentence in the README and the submission saying where Wispr Flow was used (input method plus dev workflow); keep it factual.
- [ ] If the form asks for Wispr usage stats (words dictated, sessions), copy them from the Wispr app.

## 9. Final submission checklist

- [ ] Commit and push today's fixes; `pytest` green (26).
- [ ] Repo public, or judges given access; README renders.
- [ ] Test and audit issues closed, or a clean demo repo used; `GITHUB_REPO` set accordingly.
- [ ] Fresh `data/actiongraph.db` for recording.
- [ ] Record the 3-minute video (section 7) with live Wispr Flow; upload; link works logged out.
- [ ] Submission text: problem, what it does, architecture, held-out metrics (state the caveats), Wispr Flow usage.
- [ ] Re-check the official brief for any mandatory item not in this matrix.
- [ ] Submit well before 23:59 IST; keep a screenshot of the confirmation.
