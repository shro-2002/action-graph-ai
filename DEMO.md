# 3-minute demo script

Covers every item in the official brief for Problem 03 (Meeting-to-execution agent): speaker attribution, extraction, conflicts with memory, tracker integration, reminders, weekly digest per person, confirmation before posting.

## Before you record

1. Server: `DB_PATH=data/demo.db .venv/bin/uvicorn app.main:app --port 8765` (already running; `data/demo.db` is empty). The old database is untouched at `data/actiongraph.db`, with a copy at `data/actiongraph-pre-demo-2026-10-31.db`. Audit evidence stays in `data/audit.db`.
2. Tabs: http://localhost:8765 and the GitHub issues page of the tracker repo, filtered to new issues (`is:issue sort:created-desc`). Issues #1–20 are earlier test and audit runs and stay as history.
3. Wispr Flow running. **Rehearse one line first**: say "Nisha colon okay so…" and check whether Wispr writes `Nisha:`. If it does not, type each `Name:` label and dictate only what that person says. Both give speaker attribution; one long paragraph is fine.
4. Leave the meeting **Date** field set per step below. Reminders use today's date (31 Oct), so no clock tricks are needed.

## Script

| Time | Do | Say |
|---|---|---|
| 0:00–0:15 | Landing screen | "Decisions made in meetings get lost, and they quietly contradict each other. Action Graph turns a spoken meeting into tracked work, and remembers what you decided." |
| 0:15–0:50 | Title "Pricing review", date **24 Oct**, attendees `Nisha, Dev, Karan`. Click the transcript box, **hold the Wispr Flow hotkey** and say: *"Nisha: Okay so um, for the paid tier we're going with seat-based pricing, nine dollars per seat. Dev: I'll, uh, update the pricing page copy by Thursday. Karan: And the free trial stays at fourteen days. Nisha: Karan, can you set up the Stripe test products by November second?"* → **Run agent** | "That's real speech, fillers and all. Claude splits it by speaker and pulls out two decisions and two actions, each with an owner and a real date." Open **Cleaned, speaker-attributed transcript** for one second. |
| 0:50–1:10 | **Approve** all four → **Review & post to GitHub** → read the dialog → **Confirm** → switch to the GitHub tab | "Nothing leaves without my approval and an explicit confirmation. There are the issues." |
| 1:10–1:45 | New meeting: title "Pricing follow-up", date **31 Oct**. Dictate: *"Nisha: Finance came back, we're changing the paid tier to twelve dollars per seat. Karan: And the trial, we're cutting it to seven days, no sorry, ten days. Karan: I'll announce the new price on LinkedIn by Friday. Dev: I might look into a churn dashboard at some point."* → **Run agent** | "I changed my mind mid-sentence and someone said something vague." Point at: ten days, not seven; no task for the vague remark; two red conflict cards. |
| 1:45–2:10 | Read one conflict reason aloud. **Approve** both decisions. **Reject** the LinkedIn announcement. **Post** → Confirm. Open the old $9 issue and show the "Superseded by" comment | "It checked memory: Nisha set nine dollars on the 24th, so this contradicts it, and it says why. I approve the change, and I reject the announcement because finance hasn't signed off. The rejected item never reaches GitHub, and the old issue now points at the new one." |
| 2:10–2:30 | **Memory** tab, then **Action graph** | "Each decision's history across meetings, and who owns what, including the conflict edges." |
| 2:30–2:50 | **Reminders** → **Check deadlines** (leave "as of" empty = now). Dev's item shows **Overdue**, Karan's **Due soon**. Click **Post to issue** on one → confirm → open the comment. Then **Weekly digest** → week of 26 Oct → point at Dev's card → **Email** | "The checker runs every five minutes. A reminder goes to the GitHub issue as a comment, and the owner's digest is one click to send." |
| 2:50–3:00 | **Scorecard**, held-out tile | "Measured, not claimed: 18 held-out messy-speech cases. And I built it by voice with Wispr Flow." |

If the extractor ever shows "· rules" in the trace, Claude failed and the fallback ran; stop and re-run rather than record that take.

## What to say about delivery (be accurate)

- Reminders are **scheduled** (checked every 5 min) and **delivered** as a GitHub issue comment. GitHub emails people watching the issue. With `OWNER_GITHUB=Dev=<login>,...` the comment @mentions the owner, so GitHub notifies them directly. With `AUTO_POST_REMINDERS=1` delivery happens without a click; in the demo it is a confirmed click.
- The weekly digest is built per person and **sent by you** via the Email button or Copy. The app does not send email itself.
