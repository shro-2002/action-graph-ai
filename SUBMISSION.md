# Release report — 31 Oct 2026, ~18:50 IST (deadline 23:59 IST)

## Links

| What | Link |
|---|---|
| Problem statement (Problem 03) | https://theproductspace.in/ai-hackathon-details/problem-statement |
| Submission form | https://theproductspace.in/user-dashboard/submissions/agentic-ai-hackathons (login required; fields not seen) |
| LinkedIn post submission | linked from https://theproductspace.in/ai-hackathon-details ("Submit posts"), due 1 Nov 23:59 IST |
| Repository | https://github.com/shro-2002/action-graph-ai (**private**, see blockers) |
| Demo script | [DEMO.md](DEMO.md) |

## End-to-end release run (real Claude, real GitHub)

Isolated database `data/e2e-release.db` on port 8766. The demo database `data/demo.db` was not touched (0 meetings). All test issues are titled from meetings prefixed **`[E2E TEST]`**.

| Check | Result |
|---|---|
| Cloud extraction, not fallback | Both meetings `llm:claude-sonnet-5-5` |
| Speaker attribution (one dictated paragraph) | 4/4 utterances to Nisha, Dev, Karan, Nisha; meeting 2: 4/4 |
| Decisions, actions, owners, deadlines | Meeting 1: 2 decisions + 2 actions, all correct. "by Thursday" → 2026-10-29, "November second" → 2026-11-02 |
| Self-correction | "seven days, no sorry, ten days" → 10 days |
| Vague remark not extracted | "I might look into a churn dashboard" → no item |
| Conflicts with memory | 2 flagged with reasons, e.g. "Contradicts '[E2E TEST] Pricing review' (2026-10-24, Nisha): paid tier pricing was “Seat-based, $9 per seat”, now “$12 per seat”." |
| Confirmation before posting | Dialog listed exactly the approved items; rejected item absent |
| Rejected action creates nothing | LinkedIn action rejected; GitHub search "LinkedIn" → 0 issues |
| Real GitHub issues | #21, #22, #23, #24 (meeting 1), #25, #26 (meeting 2). Body has owner, due date, quote, speaker and the hidden `<!-- action-graph-item:… -->` marker |
| Supersede back-link | #21 got "🔁 Superseded by …/issues/25" plus the reason |
| Retry does not duplicate | Item 3 reset to approved as if GitHub's reply was lost, posted again → returned existing #23, no new issue. Second retry refused ("not approved (status posted)") |
| Reminders | As of now: "⚠️ Overdue: Dev …" and "⏰ Due soon: Karan …". Posted one: https://github.com/shro-2002/action-graph-ai/issues/23#issuecomment-6543735769 |
| Weekly digest per person | Week of 26 Oct: Dev, Karan, Nisha cards with due items and decisions; Copy and Email work |
| Memory | $9 and 14 days marked superseded; $12 and 10 days current |
| Graph | 11 nodes, 14 edges, 2 conflict edges; renders |
| Scorecard | Consistent. "posted to GitHub" reads 7 for 6 issues because my forced retry logged a second post event for #23 |

UI fixes from this run: "1 actions" → "1 action"; scorecard labels no longer say "rules tuned on it" next to the Claude score.

## Not verified

- Wispr Flow dictation, and whether it turns a spoken "colon" into `:`. You must test.
- Automatic reminder delivery (`AUTO_POST_REMINDERS=1`) against real GitHub; unit-tested only.
- Whether the submission form requires a deployed URL. The public brief and the hackathon page do not mention one; the form is behind login.
- The README line "prompts and specs were dictated to Claude Code with Wispr Flow" is your claim; I can't confirm it.

## Blockers needing you

| # | Blocker | Action |
|---|---|---|
| 1 | Repo is **private**: judges can't open the code or the issues | Approve making it public (`gh repo edit shro-2002/action-graph-ai --visibility public --accept-visibility-change-consequences`). History scan: no keys or tokens; only your commit author email `ghoshshroddha@gmail.com` is in commit metadata |
| 2 | Wispr Flow evidence (20% of score) | Record the demo with Wispr visible; capture the checklist below |
| 3 | Form fields unknown | Log in and open the form now |
| 4 | Test issues #1–26 are visible once public | Leave them as history (titles of #21–26 say `[E2E TEST]`), or approve closing them. Nothing was deleted |

## Video requirements (inferred, the form may say more)

- 3 minutes max per our plan; show the product working and Wispr Flow in use (judges score "how you used your voice", 20%).
- Upload as YouTube unlisted or Loom; open the link in a private window to check it plays logged out.

## Wispr Flow and LinkedIn evidence checklist

- [ ] Video: Wispr hotkey or overlay visible while text appears in the capture box.
- [ ] Video: one live self-correction and filler, with the corrected result on screen.
- [ ] Screenshot of the Wispr Flow history or dashboard with today's sessions.
- [ ] 2–3 screenshots or a clip of dictating prompts to Claude Code while building.
- [ ] LinkedIn post 1 (after kickoff): building with voice, the problem you took.
- [ ] LinkedIn post 2 (while building): a screenshot or clip of Wispr Flow in action plus one learning.
- [ ] LinkedIn post 3 (by 1 Nov): the demo video, how voice changed your work, the takeaway. Tag Product Space.
- [ ] Submit post links plus a likes/comments screenshot by 1 Nov 23:59 IST.
