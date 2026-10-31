# 3-minute demo script

Final configuration: Claude `claude-sonnet-5-5`, commit `1f7f6ec` or later, empty `data/demo.db`, http://localhost:8765. Every step below was dry-run on 31 Oct against a throwaway database with these exact transcripts (speakers 8/8, all items correct, both conflicts flagged).

## Before you record

1. Open http://localhost:8765. The header must read **Claude extraction on** and **0 meetings**. If not, stop: the server is not the demo server.
2. Second tab: `https://github.com/shro-2002/action-graph-ai/issues?q=is%3Aissue+sort%3Acreated-desc`. Issues #1–26 are earlier test runs (#21–26 titled `[E2E TEST]`); your demo creates #27 onward.
3. Wispr Flow running. Rehearse in any text box: say "Nisha colon hello". If Wispr does not write `Nisha:`, type each `Nisha: ` label yourself and dictate only the words after it.
4. All deadlines below are spoken as explicit dates, so nothing depends on the day you record. Reminders show Dev **overdue** and Karan **due soon** if you record on 31 Oct, 1 Nov or 2 Nov.
5. Do not press **Run agent** twice. Wait for the trace (about 5–15 s).

## Meeting 1: fields and dictation

- Title: `Pricing review`
- Date: **24 Oct 2026**
- Attendees: `Nisha, Dev, Karan`
- Dictate:

> Nisha: Okay so um, for the paid tier we're going with seat-based pricing, nine dollars per seat. Dev: I'll, uh, update the pricing page copy by October twenty-ninth. Karan: And the free trial stays at fourteen days. Nisha: Karan, can you set up the Stripe test products by November second?

Expected: 2 decisions ($9 per seat, 14 days), 2 actions (Dev, 2026-10-29; Karan, 2026-11-02).

## Meeting 2: fields and dictation

- Title: `Pricing follow-up`
- Date: **31 Oct 2026**
- Attendees: `Nisha, Dev, Karan`
- Dictate:

> Nisha: Finance came back, we're changing the paid tier to twelve dollars per seat. Karan: And the trial, we're cutting it to seven days, no sorry, ten days. Karan: I'll announce the new price on LinkedIn by November sixth. Dev: I might look into a churn dashboard at some point.

Expected: 2 decisions, both with red conflict cards ($9 → $12, 14 → 10 days); 1 action (Karan, 2026-11-06); no item for the churn dashboard.

## Script

| Time | Do | Say |
|---|---|---|
| 0:00–0:15 | Landing screen | "Decisions made in meetings get lost, and they quietly contradict each other. Action Graph turns a spoken meeting into tracked work, and remembers what you decided." |
| 0:15–0:50 | Fill meeting 1 fields. Click the transcript box, hold the Wispr Flow hotkey, dictate meeting 1. **Run agent**. Open **Cleaned, speaker-attributed transcript** for a second | "Real speech, fillers and all. Claude splits it by speaker and pulls out two decisions and two actions, each with an owner and a date." |
| 0:50–1:10 | **Approve** all four → **Review & post to GitHub** → read the dialog → **Confirm & create issues** → GitHub tab, refresh | "Nothing leaves without my approval and an explicit confirmation. There are the issues." |
| 1:10–1:45 | Back to the app. Change title and date, dictate meeting 2, **Run agent** | "I changed my mind mid-sentence, and someone said something vague." Point at: ten days, not seven; no churn task; two red conflict cards. |
| 1:45–2:10 | Read the $9 → $12 conflict reason. **Approve** both decisions. **Reject** the LinkedIn action. **Review & post** → the dialog lists only the 2 decisions → **Confirm**. GitHub tab: open the $9 issue, scroll to the "Superseded by" comment | "It checked memory: Nisha set nine dollars on the 24th. I approve the change and reject the announcement until finance signs off. The rejected item never reaches GitHub, and the old issue now points to the new one." |
| 2:10–2:30 | **Memory** tab, then **Action graph** (wait 2 s for layout) | "Each decision's history across meetings, and who owns what, with the conflict edges." |
| 2:30–2:50 | **Reminders** → **Check deadlines** (leave "as of" empty). Dev is overdue, Karan due soon. **Post to issue** on Dev's → OK. **Weekly digest** → week starting **26 Oct 2026** → **Build digests** → point at Dev's card | "The checker also runs every five minutes. I post a reminder to the issue as a comment, and each person gets their own digest that I can copy or email." |
| 2:50–3:00 | **Scorecard** | "Measured: one hundred percent precision and recall on 18 held-out messy-speech cases with Claude. Built by voice with Wispr Flow." |

## Say only what is true

- Reminders: generated automatically every 5 minutes; delivered as a GitHub issue comment after a confirm click. Automatic delivery exists (`AUTO_POST_REMINDERS=1`) but is not used or shown in this demo.
- Digest: built per person in the app; you send it (Copy or Email opens your mail app). The app does not send email.
- Do not click **Email** while recording unless you want your mail app on screen.
