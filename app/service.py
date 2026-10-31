"""Agent pipeline and state transitions. Routes in main.py stay thin."""
from datetime import date, datetime, timedelta

from app import db, tracker
from app.conflicts import Memory, find_conflict
from app.extract import extract

ACTIVE_DECISION = "('approved','posted','done')"
OPEN_ACTION = "('approved','posted')"


class NotFound(LookupError):
    pass


class InvalidState(ValueError):
    pass


def memory(exclude_meeting: int | None = None) -> list[Memory]:
    found = db.rows(
        f"""SELECT i.id, i.subject, i.value, i.text, i.speaker, m.title, m.date FROM items i
            JOIN meetings m ON m.id = i.meeting_id
            WHERE i.kind='decision' AND i.status IN {ACTIVE_DECISION} AND i.meeting_id != ?""",
        (exclude_meeting or -1,),
    )
    return [Memory(r["id"], r["subject"] or r["text"], r["value"], r["text"], r["title"], r["date"], r["speaker"]) for r in found]


def ingest(title: str, meeting_date: date, transcript: str, attendees: list[str]) -> dict:
    remembered = memory()
    result = extract(transcript, meeting_date, attendees, sorted({m.subject for m in remembered}))
    meeting_id = db.execute(
        "INSERT INTO meetings (title, date, raw_transcript, extractor, created_at) VALUES (?,?,?,?,?)",
        (title, meeting_date.isoformat(), transcript, result.extractor, db.now_iso()),
    )
    for idx, u in enumerate(result.utterances):
        db.execute("INSERT INTO utterances (meeting_id, idx, speaker, text) VALUES (?,?,?,?)", (meeting_id, idx, u.speaker, u.text))
    conflicts = 0
    for it in result.items:
        clash = find_conflict(it.subject or it.text, it.value, it.text, meeting_date, remembered) if it.kind == "decision" else None
        conflicts += bool(clash)
        db.execute(
            """INSERT INTO items (meeting_id, kind, text, owner, deadline, subject, value, speaker, source_quote,
               confidence, conflict_with, conflict_reason, conflict_score, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (meeting_id, it.kind, it.text, it.owner, it.deadline, it.subject, it.value, it.speaker, it.source_quote,
             it.confidence, clash and clash.memory_id, clash and clash.reason, clash and clash.similarity, db.now_iso()),
        )
    db.log_event("ingest", {"meeting_id": meeting_id, "items": len(result.items), "conflicts": conflicts, "extractor": result.extractor})
    return meeting(meeting_id) | {"notes": result.notes}


def meeting(meeting_id: int) -> dict:
    m = db.one("SELECT * FROM meetings WHERE id=?", (meeting_id,))
    if not m:
        raise NotFound(f"meeting {meeting_id}")
    m["utterances"] = db.rows("SELECT speaker, text FROM utterances WHERE meeting_id=? ORDER BY idx", (meeting_id,))
    m["items"] = items(meeting_id=meeting_id)
    return m


def items(meeting_id: int | None = None, status: str | None = None) -> list[dict]:
    sql = """SELECT i.*, m.title AS meeting_title, m.date AS meeting_date,
             c.text AS conflict_text, c.status AS conflict_status
             FROM items i JOIN meetings m ON m.id=i.meeting_id LEFT JOIN items c ON c.id=i.conflict_with WHERE 1=1"""
    params: list = []
    if meeting_id is not None:
        sql, params = sql + " AND i.meeting_id=?", params + [meeting_id]
    if status:
        sql, params = sql + " AND i.status=?", params + [status]
    return db.rows(sql + " ORDER BY m.date, i.id", tuple(params))


def _item(item_id: int) -> dict:
    it = db.one("SELECT * FROM items WHERE id=?", (item_id,))
    if not it:
        raise NotFound(f"item {item_id}")
    return it


EDITABLE = ("text", "owner", "deadline", "subject", "value")


def approve(item_id: int, edits: dict) -> dict:
    it = _item(item_id)
    if it["status"] != "pending":
        raise InvalidState(f"item {item_id} is {it['status']}")
    changed = {k: v for k, v in edits.items() if k in EDITABLE and v != it[k]}
    for key, val in changed.items():
        db.execute(f"UPDATE items SET {key}=? WHERE id=?", (val or None, item_id))  # key is whitelisted above
    db.execute("UPDATE items SET status='approved' WHERE id=?", (item_id,))
    if it["kind"] == "decision" and it["conflict_with"]:
        db.execute("UPDATE items SET status='superseded' WHERE id=?", (it["conflict_with"],))
    db.log_event("approve", {"item_id": item_id, "edited": sorted(changed), "superseded": it["conflict_with"]})
    return _item(item_id)


def reject(item_id: int) -> dict:
    if _item(item_id)["status"] != "pending":
        raise InvalidState(f"item {item_id} is not pending")
    db.execute("UPDATE items SET status='rejected' WHERE id=?", (item_id,))
    db.log_event("reject", {"item_id": item_id})
    return _item(item_id)


def complete(item_id: int) -> dict:
    if _item(item_id)["status"] not in ("approved", "posted"):
        raise InvalidState("only approved or posted actions can be completed")
    db.execute("UPDATE items SET status='done' WHERE id=?", (item_id,))
    db.log_event("done", {"item_id": item_id})
    return _item(item_id)


def _issue_body(it: dict, m: dict) -> str:
    lines = [f"**{it['kind'].title()}** from meeting *{m['title']}* ({m['date']})", ""]
    if it["owner"]:
        lines.append(f"- **Owner:** {it['owner']}")
    if it["deadline"]:
        lines.append(f"- **Due:** {it['deadline']}")
    if it["kind"] == "decision" and it["value"]:
        lines.append(f"- **Decided:** {it['subject']} → {it['value']}")
    if it["conflict_reason"]:
        lines.append(f"- **Supersedes earlier decision:** {it['conflict_reason']}")
    lines += ["", f"> {it['source_quote'] or it['text']}", f"> — {it['speaker'] or 'unknown'}", "",
              "_Created by Action Graph AI after human approval._"]
    return "\n".join(lines)


def post(item_ids: list[int]) -> list[dict]:
    """Create tracker issues. Only items a human approved are eligible."""
    results = []
    for item_id in item_ids:
        it = _item(item_id)
        if it["status"] != "approved":
            results.append({"id": item_id, "error": f"not approved (status {it['status']})"})
            continue
        m = db.one("SELECT title, date FROM meetings WHERE id=?", (it["meeting_id"],))
        prefix = f"[{it['owner']}] " if it["owner"] else "[Decision] "
        due = f" (due {it['deadline']})" if it["deadline"] else ""
        try:
            url = tracker.create_issue(prefix + it["text"] + due, _issue_body(it, m), ["action-graph", it["kind"]])
        except tracker.TrackerError as exc:
            results.append({"id": item_id, "error": str(exc)})
            continue
        db.execute("UPDATE items SET status='posted', tracker_url=? WHERE id=?", (url, item_id))
        db.log_event("post", {"item_id": item_id, "url": url})
        old = db.one("SELECT tracker_url FROM items WHERE id=?", (it["conflict_with"],)) if it["conflict_with"] else None
        if old and old["tracker_url"]:
            try:
                tracker.comment(old["tracker_url"], f"🔁 Superseded by {url}\n\n{it['conflict_reason']}")
            except tracker.TrackerError as exc:  # the new issue exists; a missing back-link must not fail the post
                results.append({"id": item_id, "warning": f"could not link old issue: {exc}"})
        results.append({"id": item_id, "url": url})
    return results


def run_reminders(now: datetime, window_hours: int = 48) -> list[dict]:
    """Create one reminder per open action due within the window (or overdue)."""
    horizon = (now + timedelta(hours=window_hours)).date().isoformat()
    due = db.rows(
        f"""SELECT i.* FROM items i LEFT JOIN reminders r ON r.item_id=i.id
            WHERE i.kind='action' AND i.status IN {OPEN_ACTION} AND i.deadline IS NOT NULL
            AND i.deadline <= ? AND r.id IS NULL""",
        (horizon,),
    )
    for it in due:
        overdue = it["deadline"] < now.date().isoformat()
        msg = f"{'⚠️ Overdue' if overdue else '⏰ Due soon'}: {it['owner'] or 'Unassigned'} — {it['text']} (due {it['deadline']})"
        db.execute("INSERT INTO reminders (item_id, message, created_at) VALUES (?,?,?)", (it["id"], msg, db.now_iso()))
    return reminders()


def reminders() -> list[dict]:
    return db.rows("""SELECT r.*, i.tracker_url, i.owner, i.deadline FROM reminders r
                      JOIN items i ON i.id=r.item_id ORDER BY i.deadline""")


def post_reminder(reminder_id: int) -> dict:
    r = db.one("SELECT r.*, i.tracker_url FROM reminders r JOIN items i ON i.id=r.item_id WHERE r.id=?", (reminder_id,))
    if not r:
        raise NotFound(f"reminder {reminder_id}")
    if not r["tracker_url"]:
        raise InvalidState("item has no tracker issue yet; post it first")
    url = tracker.comment(r["tracker_url"], r["message"] + "\n\n_Reminder from Action Graph AI._")
    db.execute("UPDATE reminders SET posted_url=? WHERE id=?", (url, reminder_id))
    return {"id": reminder_id, "url": url}


def digest(week_start: date) -> list[dict]:
    week_end = week_start + timedelta(days=6)
    people: dict[str, dict] = {}

    def bucket(name: str) -> dict:
        return people.setdefault(name, {"person": name, "overdue": [], "due_this_week": [], "later": [], "done": [], "decisions": []})

    for it in items():
        if it["status"] in ("rejected", "pending"):
            continue
        if it["kind"] == "decision":
            if it["speaker"] and week_start.isoformat() <= it["meeting_date"] <= week_end.isoformat():
                bucket(it["speaker"])["decisions"].append(it)
            continue
        b = bucket(it["owner"] or "Unassigned")
        if it["status"] == "done":
            b["done"].append(it)
        elif it["deadline"] and it["deadline"] < week_start.isoformat():
            b["overdue"].append(it)
        elif it["deadline"] and it["deadline"] <= week_end.isoformat():
            b["due_this_week"].append(it)
        else:
            b["later"].append(it)
    return sorted(people.values(), key=lambda p: p["person"])


def graph() -> dict:
    nodes, edges, seen = [], [], set()

    def node(nid: str, label: str, kind: str, **extra) -> None:
        if nid not in seen:
            seen.add(nid)
            nodes.append({"id": nid, "label": label, "kind": kind, **extra})

    for m in db.rows("SELECT id, title, date FROM meetings"):
        node(f"m{m['id']}", f"{m['title']}\n{m['date']}", "meeting")
    for it in items():
        if it["status"] == "rejected":
            continue
        nid = f"i{it['id']}"
        node(nid, it["text"][:34] + ("…" if len(it["text"]) > 34 else ""), it["kind"], status=it["status"])
        edges.append({"source": f"m{it['meeting_id']}", "target": nid, "kind": "produced"})
        person = it["owner"] if it["kind"] == "action" else it["speaker"]
        if person:
            node(f"p{person}", person, "person")
            edges.append({"source": f"p{person}", "target": nid, "kind": "owns" if it["kind"] == "action" else "decided"})
        if it["conflict_with"]:
            edges.append({"source": nid, "target": f"i{it['conflict_with']}", "kind": "conflicts"})
    return {"nodes": nodes, "edges": edges}


def stats() -> dict:
    events = db.rows("SELECT kind, payload FROM events")
    import json

    approvals = [json.loads(e["payload"]) for e in events if e["kind"] == "approve"]
    total = db.one("SELECT COUNT(*) n FROM items")["n"]
    return {
        "meetings": db.one("SELECT COUNT(*) n FROM meetings")["n"],
        "items_extracted": total,
        "conflicts_flagged": db.one("SELECT COUNT(*) n FROM items WHERE conflict_with IS NOT NULL")["n"],
        "approved": len(approvals),
        "approved_without_edits": sum(1 for a in approvals if not a["edited"]),
        "rejected": sum(1 for e in events if e["kind"] == "reject"),
        "posted": sum(1 for e in events if e["kind"] == "post"),
        "superseded": db.one("SELECT COUNT(*) n FROM items WHERE status='superseded'")["n"],
    }
