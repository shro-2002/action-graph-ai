"""Resolve spoken deadlines ("by Friday", "next Tuesday", "Nov 15") to ISO dates."""
import re
from datetime import date, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = {
    m: i + 1
    for i, names in enumerate(
        [("jan", "january"), ("feb", "february"), ("mar", "march"), ("apr", "april"),
         ("may",), ("jun", "june"), ("jul", "july"), ("aug", "august"),
         ("sep", "sept", "september"), ("oct", "october"), ("nov", "november"), ("dec", "december")]
    )
    for m in names
}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "a": 1, "an": 1}
MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))


def _next_weekday(base: date, weekday: int, skip_week: bool) -> date:
    days = (weekday - base.weekday()) % 7 or 7
    return base + timedelta(days=days + (7 if skip_week else 0))


def _month_day(base: date, month: int, day: int) -> date | None:
    try:
        candidate = date(base.year, month, day)
    except ValueError:
        return None
    # A date far in the past most likely means next year ("Jan 5" said in December).
    if (base - candidate).days > 60:
        candidate = date(base.year + 1, month, day)
    return candidate


def parse_deadline(text: str, base: date) -> str | None:
    """Return the first deadline mentioned in text as YYYY-MM-DD, or None."""
    t = text.lower()
    if m := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", t):
        return m.group(0)
    if m := re.search(rf"\b({MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", t):
        d = _month_day(base, MONTHS[m.group(1)], int(m.group(2)))
        return d.isoformat() if d else None
    if m := re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({MONTH_RE})\b", t):
        d = _month_day(base, MONTHS[m.group(2)], int(m.group(1)))
        return d.isoformat() if d else None
    if re.search(r"\b(today|eod|end of day|tonight)\b", t):
        return base.isoformat()
    if re.search(r"\btomorrow\b", t):
        return (base + timedelta(days=1)).isoformat()
    if re.search(r"\bend of (the )?week\b|\beow\b", t):
        return (base + timedelta(days=(4 - base.weekday()) % 7)).isoformat()
    if re.search(r"\bend of (the )?month\b", t):
        nxt = date(base.year + base.month // 12, base.month % 12 + 1, 1)
        return (nxt - timedelta(days=1)).isoformat()
    if m := re.search(r"\b(next|this|by|on|until|before)?\s*(" + "|".join(WEEKDAYS) + r")\b", t):
        return _next_weekday(base, WEEKDAYS.index(m.group(2)), m.group(1) == "next").isoformat()
    if m := re.search(r"\bin\s+(\d+|one|two|three|four|five|a|an)\s+(day|week)s?\b", t):
        n = int(m.group(1)) if m.group(1).isdigit() else NUMBER_WORDS[m.group(1)]
        return (base + timedelta(days=n * (7 if m.group(2) == "week" else 1))).isoformat()
    if re.search(r"\bnext week\b", t):
        return _next_weekday(base, 0, False).isoformat()
    return None
