from datetime import date, datetime
from pathlib import Path

import pytest

from app import db, service
from app.cleanup import clean_text, parse_speakers
from app.dates import parse_deadline

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)  # tests exercise the deterministic path
    db.connect(":memory:")


@pytest.mark.parametrize("raw,expected", [
    ("Launch on Friday, no wait, Monday.", "Launch on Monday."),
    ("We go with postgres, actually mongodb.", "We go with mongodb."),
    ("Priya owns pricing, sorry I mean Arjun owns pricing.", "Arjun owns pricing."),
    ("Moving it to November 21. No wait, November 28.", "Moving it to November 28."),
    ("It is actually fine.", "It is actually fine."),
])
def test_self_correction(raw, expected):
    assert clean_text(raw) == expected


def test_fillers_removed():
    assert clean_text("Um so, uh, Ravi will, will send the deck, you know.") == "So, Ravi will send the deck."


def test_speaker_parsing():
    utts = parse_speakers("[00:01] Priya: hi team\ncontinuing here\nRavi: I will do it")
    assert [(u.speaker, u.text) for u in utts] == [("Priya", "Hi team Continuing here"), ("Ravi", "I will do it")]


def test_inline_speaker_labels_from_one_paragraph_dictation():
    utts = parse_speakers("Priya: launch is Nov 14. Arjun: I'll set up staging. Note: not a person. Priya: thanks.",
                          speakers=["Priya", "Arjun"])
    assert [u.speaker for u in utts] == ["Priya", "Arjun", "Priya"]
    assert utts[1].text == "I'll set up staging. Note: not a person."


@pytest.mark.parametrize("phrase,expected", [
    ("by Friday", "2026-11-06"), ("next Tuesday", "2026-11-10"), ("Nov 15", "2026-11-15"),
    ("15th November", "2026-11-15"), ("tomorrow", "2026-11-01"), ("in two weeks", "2026-11-14"),
    ("no date here", None),
])
def test_parse_deadline(phrase, expected):
    assert parse_deadline(phrase, date(2026, 10, 31)) == expected


def _ingest(name: str, d: date) -> dict:
    return service.ingest(name, d, (SAMPLES / f"{name}.txt").read_text(), [])


def _approve_all(meeting: dict) -> None:
    for it in meeting["items"]:
        service.approve(it["id"], {})


def test_extracts_actions_owners_deadlines():
    m = _ingest("01_sprint_planning", date(2026, 10, 24))
    actions = {(i["owner"], i["deadline"]) for i in m["items"] if i["kind"] == "action"}
    assert ("Arjun", "2026-10-28") in actions and ("Meera", "2026-10-30") in actions
    decisions = {(i["subject"], i["value"]) for i in m["items"] if i["kind"] == "decision"}
    assert ("launch date", "November 14") in decisions and ("database", "Postgres") in decisions


def test_conflict_detected_across_meetings():
    _approve_all(_ingest("01_sprint_planning", date(2026, 10, 24)))
    m2 = _ingest("02_launch_sync", date(2026, 10, 31))
    flagged = {i["subject"]: i["conflict_reason"] for i in m2["items"] if i["conflict_with"]}
    assert set(flagged) == {"launch date", "database"}
    assert "November 14" in flagged["launch date"] and "November 28" in flagged["launch date"]


def test_no_conflict_same_value():
    _approve_all(_ingest("01_sprint_planning", date(2026, 10, 24)))
    m = service.ingest("recap", date(2026, 10, 25), "Priya: We decided the launch date is Nov 14.", [])
    assert all(i["conflict_with"] is None for i in m["items"])


def test_pending_decisions_are_not_memory():
    _ingest("01_sprint_planning", date(2026, 10, 24))  # never approved
    m2 = _ingest("02_launch_sync", date(2026, 10, 31))
    assert all(i["conflict_with"] is None for i in m2["items"])


def test_supersede_on_approval():
    _approve_all(_ingest("01_sprint_planning", date(2026, 10, 24)))
    m2 = _ingest("02_launch_sync", date(2026, 10, 31))
    clash = next(i for i in m2["items"] if i["conflict_with"])
    service.approve(clash["id"], {})
    assert db.one("SELECT status FROM items WHERE id=?", (clash["conflict_with"],))["status"] == "superseded"


def test_nothing_posted_without_approval(monkeypatch):
    calls = []
    monkeypatch.setattr("app.tracker.create_issue", lambda *a, **k: calls.append(a) or "https://github.com/x/y/issues/1")
    m = _ingest("01_sprint_planning", date(2026, 10, 24))
    first, second = m["items"][0], m["items"][1]
    service.approve(first["id"], {})
    results = service.post([first["id"], second["id"]])
    assert len(calls) == 1
    assert results[0]["url"] and "not approved" in results[1]["error"]


def test_concurrent_post_creates_one_issue(monkeypatch):
    import threading
    import time

    calls = []

    def slow_create(*a, **k):
        calls.append(a)
        time.sleep(0.2)  # GitHub round-trip: a second click lands while the first is in flight
        return f"https://github.com/x/y/issues/{len(calls)}"

    monkeypatch.setattr("app.tracker.create_issue", slow_create)
    item = _ingest("01_sprint_planning", date(2026, 10, 24))["items"][0]
    service.approve(item["id"], {})
    threads = [threading.Thread(target=service.post, args=([item["id"]],)) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(calls) == 1


def test_reminders_due_window():
    m = _ingest("01_sprint_planning", date(2026, 10, 24))
    _approve_all(m)
    out = service.run_reminders(datetime(2026, 10, 27, 9), window_hours=48)
    assert {r["deadline"] for r in out} == {"2026-10-28"}
    assert len(service.run_reminders(datetime(2026, 10, 27, 9), window_hours=48)) == 1  # idempotent


def test_digest_groups_by_owner():
    _approve_all(_ingest("01_sprint_planning", date(2026, 10, 24)))
    people = {p["person"]: p for p in service.digest(date(2026, 10, 26))}
    assert [i["deadline"] for i in people["Meera"]["due_this_week"]] == ["2026-10-30"]
    assert len(people["Arjun"]["due_this_week"]) == 1


def test_filler_between_verb_and_task():
    m = service.ingest("q", date(2026, 10, 31), "Priya: Um, Arjun will, uh, write the FAQ by Friday, no wait, Thursday.", [])
    assert [(i["owner"], i["deadline"]) for i in m["items"]] == [("Arjun", "2026-11-05")]


def test_due_soon_reminder_escalates_to_overdue_and_can_be_redelivered():
    _approve_all(_ingest("01_sprint_planning", date(2026, 10, 24)))
    [soon] = service.run_reminders(datetime(2026, 10, 27, 9), window_hours=48)
    assert soon["stage"] == "due_soon"
    db.execute("UPDATE reminders SET posted_url='https://github.com/x/y/issues/1#c1' WHERE id=?", (soon["id"],))
    later = {r["item_id"]: r for r in service.run_reminders(datetime(2026, 10, 29, 9), window_hours=0)}
    assert later[soon["item_id"]]["stage"] == "overdue"
    assert later[soon["item_id"]]["posted_url"] is None  # escalation is a new delivery
    assert later[soon["item_id"]]["message"].startswith("⚠️ Overdue")


def test_auto_delivery_comments_with_owner_mention(monkeypatch):
    monkeypatch.setenv("OWNER_GITHUB", "Arjun=arjun-gh")
    sent = []
    monkeypatch.setattr("app.tracker.comment", lambda url, body: sent.append(body) or url + "#c1")
    m = _ingest("01_sprint_planning", date(2026, 10, 24))
    _approve_all(m)
    arjun = next(i for i in m["items"] if i["owner"] == "Arjun")
    db.execute("UPDATE items SET status='posted', tracker_url='https://github.com/x/y/issues/9' WHERE id=?", (arjun["id"],))
    out = service.run_reminders(datetime(2026, 10, 27, 9), window_hours=48, deliver=True)
    assert sent and sent[0].startswith("@arjun-gh ⏰ Due soon")
    assert out[0]["posted_url"].endswith("#c1")


def test_issue_create_timeout_recovers_existing_issue(monkeypatch):
    import httpx
    from app import tracker

    found = iter([None, "https://github.com/x/y/issues/7"])  # not there before the POST, there after it timed out
    monkeypatch.setattr(tracker, "find_issue", lambda marker: next(found))
    monkeypatch.setattr(tracker, "_token", lambda: "t")
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: (_ for _ in ()).throw(httpx.ReadTimeout("slow")))
    assert tracker.create_issue("t", "b", ["action-graph"], marker="m1") == "https://github.com/x/y/issues/7"
