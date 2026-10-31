"""Extract decisions and action items: Claude tool-use first, deterministic rules as fallback."""
import logging
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import date

from app.cleanup import Utterance, parse_speakers
from app.dates import parse_deadline

log = logging.getLogger(__name__)

NOT_NAMES = set(
    "We I It The This That Let Lets So And But Also Okay Ok Yes No Then Now Next Everyone Someone Team "
    "Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July "
    "August September October November December Action Decision Please Can Could Who What Speaker".split()
)
DECISION_CUE = re.compile(
    r"\b(we(?:'ve| have)? decided|decided|decision is|let's go with|we'll go with|we're going with|going with|"
    r"agreed|final call|we will use|we'll use|we're moving|we are moving|moving the|push(?:ing)? the|"
    r"is final|we're dropping|we are dropping|we will not|we won't|scrap(?:ping)? the|switch(?:ing)? to)\b",
    re.I,
)
SELF_ACTION = re.compile(r"^(?:(?:so|okay|ok|and|yeah)[,]?\s+)*(?:i'll|i will|i can|i'm going to|i am going to|let me),?\s+(.+)", re.I)
NAMED_ACTION = re.compile(r"\b([A-Z][a-z]+)(?:,)?\s+(?:will|is going to|to|can you|could you|please|owns|takes|should),?\s+(.+)")
TRAILING_ASK = re.compile(r"^(?:[Cc]an|[Cc]ould|[Ww]ould) you\s+(.+?),?\s+([A-Z][a-z]+)\??$")
CATEGORIES = {
    "database": "postgres postgresql mysql mongodb mongo sqlite dynamodb firestore supabase".split(),
    "frontend framework": "react vue svelte angular nextjs next.js".split(),
    "cloud provider": "aws gcp azure vercel netlify render".split(),
    "pricing": "freemium subscription usage-based".split(),
}
DECISION_PATTERNS = [
    re.compile(r"(?:move|moving|push|pushing|shift|shifting|delay|delaying)\s+(?:the\s+|our\s+)?(?P<subj>[\w -]+?)\s+to\s+(?P<val>[^,.]+)", re.I),
    re.compile(r"(?:go(?:ing)? with|use|using|switch(?:ing)? to|pick|chose|choose)\s+(?P<val>[\w.-]+(?: (?!for\b|as\b)[\w.-]+)?)(?:\s+(?:for|as)\s+(?:the\s+|our\s+)?(?P<subj>[\w -]+))?", re.I),
    re.compile(r"(?:the\s+|our\s+)?(?P<subj>[\w -]+?)\s+(?:is|will be|is now|stays|remains|moves to|goes to)\s+(?:on\s+|at\s+)?(?P<val>[^,.]+)", re.I),
]
CUE_PREFIX = re.compile(r"^(?:so|okay|ok|alright|and|final call|decision is)?[,:]?\s*(?:we(?:'ve| have)? (?:decided|agreed)|decided|agreed)?\s*(?:that|to|on)?\s*", re.I)


@dataclass
class Item:
    kind: str
    text: str
    owner: str | None = None
    deadline: str | None = None
    subject: str | None = None
    value: str | None = None
    speaker: str | None = None
    source_quote: str | None = None
    confidence: float = 0.6


@dataclass
class Extraction:
    utterances: list[Utterance]
    items: list[Item]
    extractor: str
    notes: list[str] = field(default_factory=list)


def _category(value: str) -> str | None:
    low = value.lower()
    return next((cat for cat, words in CATEGORIES.items() if any(w in low.split() for w in words)), None)


def decision_slot(text: str) -> tuple[str, str | None]:
    """Best-effort (subject, value) for a decision sentence."""
    body = CUE_PREFIX.sub("", text.strip().rstrip(".")).strip()
    for pattern in DECISION_PATTERNS:
        if m := pattern.search(body):
            val = m.group("val").strip()
            subj = (m.groupdict().get("subj") or _category(val) or "").strip()
            subj = re.sub(r"^(?:the|our)\s+", "", subj, flags=re.I)
            if subj and subj.lower() not in {"we", "it", "that", "this"}:
                return subj.lower(), val
    return body.lower(), None


LEAD_WORDS = re.compile(r"^(?:(?:so|also|and|okay|ok|sure|alright|then)\b[,]?\s*)+", re.I)


def tidy(text: str) -> str:
    text = LEAD_WORDS.sub("", text.strip()).strip(" ,")
    return text[:1].upper() + text[1:]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _action_from(sentence: str, speaker: str) -> tuple[str, str] | None:
    if m := SELF_ACTION.match(sentence):
        return speaker, m.group(1)
    if m := TRAILING_ASK.match(sentence):
        return m.group(2), m.group(1)
    if (m := NAMED_ACTION.search(sentence)) and m.group(1) not in NOT_NAMES:
        return m.group(1), m.group(2)
    return None


def rule_extract(utterances: list[Utterance], meeting_date: date) -> list[Item]:
    items: list[Item] = []
    for u in utterances:
        for s in _sentences(u.text):
            if DECISION_CUE.search(s):
                subject, value = decision_slot(s)
                if value is None and len(s.split()) < 5:
                    continue  # "Agreed." carries no decision of its own
                items.append(Item("decision", tidy(s), subject=subject, value=value, speaker=u.speaker, source_quote=s))
            elif found := _action_from(s, u.speaker):
                owner, task = found
                task = tidy(task.rstrip(".?! "))
                items.append(Item("action", task, owner=owner,
                                  deadline=parse_deadline(s, meeting_date), speaker=u.speaker, source_quote=s))
    return items


TOOL = {
    "name": "record_meeting",
    "description": "Record the cleaned, speaker-attributed meeting and every decision and action item.",
    "input_schema": {
        "type": "object",
        "properties": {
            "utterances": {"type": "array", "items": {"type": "object", "properties": {
                "speaker": {"type": "string"}, "text": {"type": "string"}}, "required": ["speaker", "text"]}},
            "items": {"type": "array", "items": {"type": "object", "properties": {
                "kind": {"type": "string", "enum": ["decision", "action"]},
                "text": {"type": "string", "description": "One crisp sentence, imperative for actions."},
                "owner": {"type": ["string", "null"]},
                "deadline": {"type": ["string", "null"], "description": "YYYY-MM-DD resolved against the meeting date."},
                "subject": {"type": ["string", "null"], "description": "Decisions: short noun phrase of what was decided about, e.g. 'launch date'."},
                "value": {"type": ["string", "null"], "description": "Decisions: the chosen value, e.g. 'Nov 21'."},
                "speaker": {"type": ["string", "null"]},
                "source_quote": {"type": "string"},
                "confidence": {"type": "number"},
            }, "required": ["kind", "text", "source_quote", "confidence"]}},
        },
        "required": ["utterances", "items"],
    },
}
SYSTEM = """You turn messy dictated meeting speech into structured execution data.
The transcript was captured by voice dictation: expect filler words, digressions and self-corrections.
Always keep the FINAL version of a self-corrected statement ("Friday, no wait, Monday" means Monday).
Attribute speakers from labels like "Name:"; for unlabeled text infer from context or use the dictating user.
Extract only real decisions (something the group settled) and action items (someone committed to do something).
Owners must be people named in the meeting. Resolve relative deadlines against the meeting date.
For decisions about something already in MEMORY, reuse that exact subject wording.
Always respond by calling the record_meeting tool exactly once, even if there are no items."""


def llm_extract(transcript: str, meeting_date: date, attendees: list[str], memory_subjects: list[str]) -> Extraction:
    import anthropic

    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        base_url=os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com"),
        timeout=90,
    )
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    prompt = (
        f"Meeting date: {meeting_date.isoformat()} ({meeting_date:%A})\n"
        f"Attendees: {', '.join(attendees) or 'unknown'}\n"
        f"MEMORY subjects: {', '.join(memory_subjects) or 'none'}\n\nTRANSCRIPT:\n{transcript}"
    )
    resp = client.messages.create(
        model=model, max_tokens=4096, system=SYSTEM, tools=[TOOL],
        tool_choice={"type": "auto"},  # forced tool choice is not supported on every model; the system prompt requires the call
        messages=[{"role": "user", "content": prompt}],
    )
    data = next((b.input for b in resp.content if b.type == "tool_use"), None)
    if data is None:
        raise ValueError(f"model did not call {TOOL['name']} (stop_reason={resp.stop_reason})")
    utterances = [Utterance(u["speaker"], u["text"]) for u in data["utterances"]]
    fields = Item.__dataclass_fields__
    items = [Item(**{k: v for k, v in raw.items() if k in fields}) for raw in data["items"]]
    return Extraction(utterances, items, f"llm:{model}")


def _validate(items: list[Item], meeting_date: date, people: set[str]) -> list[Item]:
    """Deterministic guardrails over any extractor's output."""
    clean = []
    for it in items:
        if it.deadline and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", it.deadline):
            it.deadline = parse_deadline(it.deadline, meeting_date)
        if it.kind == "action" and not it.deadline and it.source_quote:
            it.deadline = parse_deadline(it.source_quote, meeting_date)
        if it.owner:
            match = next((p for p in people if p.lower() == it.owner.lower() or p.split()[0].lower() == it.owner.lower()), None)
            it.owner = match or it.owner.strip().title()
        if it.kind == "decision" and not it.subject:
            it.subject, it.value = decision_slot(it.text)
        it.subject = it.subject.lower() if it.subject else None
        clean.append(it)
    return clean


def extract(transcript: str, meeting_date: date, attendees: list[str], memory_subjects: list[str]) -> Extraction:
    notes: list[str] = []
    result: Extraction | None = None
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            result = llm_extract(transcript, meeting_date, attendees, memory_subjects)
        except Exception as exc:  # network, auth, schema: fall back, but say so
            log.warning("LLM extraction failed, using rules: %s", exc)
            notes.append(f"LLM unavailable ({type(exc).__name__}); used deterministic extractor.")
    if result is None:
        utterances = parse_speakers(transcript, attendees[0] if attendees else "Speaker", attendees)
        result = Extraction(utterances, rule_extract(utterances, meeting_date), "rules")
    people = set(attendees) | {u.speaker for u in result.utterances}
    result.items = _validate(result.items, meeting_date, people)
    result.notes = notes + result.notes
    return result


def to_dict(item: Item) -> dict:
    return asdict(item)
