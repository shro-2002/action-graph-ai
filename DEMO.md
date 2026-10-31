# 3-minute demo script

Setup before recording: start from an empty `data/actiongraph.db`, open http://localhost:8765, have Wispr Flow running and the GitHub repo issues page open in a second tab.

| Time | Show | Say |
|---|---|---|
| 0:00–0:15 | Landing screen | "Decisions made in meetings get lost, and worse, they quietly contradict each other. Action Graph turns spoken meetings into tracked execution, and remembers what you decided last week." |
| 0:15–0:45 | Load **sprint planning** sample → Run agent → approve all → **Review & post** → confirm | "Last week's planning meeting. The agent finds three decisions and three actions with owners and real dates. Nothing goes anywhere until I approve it and confirm." Switch tab: the GitHub issues are there. |
| 0:45–1:25 | Click the transcript box, **dictate with Wispr Flow** live: *"Priya: Um so the agency needs more time, we're moving the launch date to November 21, no wait, November 28. Arjun: Uh, we're going with MongoDB for the database. Arjun: I'll migrate the staging data by Tuesday, actually Monday."* → Run agent | "This is real speech: fillers, a self-correction, a changed mind." Point at the trace and the cleaned transcript: Monday, not Tuesday; November 28, not 21. |
| 1:25–1:55 | The red conflict cards | "Here's what a summarizer can't do. It checked memory: the launch date was November 14, and the database was Postgres, decided by Arjun on the 24th. It tells me exactly what conflicts and why." Approve: "Approving supersedes the old decision." |
| 1:55–2:15 | Post → GitHub: new issue, plus the "Superseded by" comment on the old issue | "The tracker stays consistent too." |
| 2:15–2:35 | **Action graph** tab, then **Memory** | "Every meeting, person, decision and action, with the conflict edges. Memory shows the history of each decision." |
| 2:35–2:50 | **Reminders**: set the date to Nov 1 → Check. **Weekly digest** → Copy | "Overdue and due-soon reminders, posted to the issue only after I confirm. A weekly digest per person." |
| 2:50–3:00 | **Scorecard** | "It measures itself: approval-without-edit rate, conflicts caught, and precision/recall on a labeled messy-speech set. Built entirely by voice with Wispr Flow." |
