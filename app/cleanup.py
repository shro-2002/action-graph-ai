"""Turn raw dictated speech into clean, speaker-attributed utterances."""
import re
from dataclasses import dataclass

FILLER_RE = re.compile(
    r"(?:(?<=^)|(?<=[\s,.;]))(?:um+|uh+|uhm+|er+|ah+|hmm+|you know|sort of|kind of|basically|literally|like,)(?=[\s,.;!?]|$)[,]?",
    re.IGNORECASE,
)
CORRECTION_RE = re.compile(
    r",\s*(?:no wait|no no|actually no|actually|scratch that|sorry,? i mean|i mean|correction|make that|or rather)\b[,:]?\s*"
    r"|\s+(?:no wait|scratch that|sorry,? i mean|or rather)\b[,:]?\s*",
    re.IGNORECASE,
)
SPEAKER_RE = re.compile(r"^\s*(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?\s*)?([A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+)?)\s*[:\-–]\s+(.+)$")
SLOT_PATTERNS = [
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?\b",
    r"\b\d+(?:\.\d+)?%?\b",
    r"\b[A-Z][a-zA-Z]+\b",
]


@dataclass(frozen=True)
class Utterance:
    speaker: str
    text: str


def remove_fillers(text: str) -> str:
    text = FILLER_RE.sub("", text)
    text = re.sub(r"\b([\w']+),?(\s+\1\b)+,?", r"\1", text, flags=re.IGNORECASE)  # "the the"
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r",([.!?])", r"\1", text)
    return re.sub(r"\s{2,}", " ", text).strip(" ,")


def _slot_kind(fragment: str) -> str | None:
    for pattern in SLOT_PATTERNS:
        if re.match(pattern + r"$", fragment.strip(" ,."), re.IGNORECASE if pattern != SLOT_PATTERNS[-1] else 0):
            return pattern
    return None


def resolve_self_corrections(sentence: str) -> str:
    """'Launch on Friday, no wait, Monday' -> 'Launch on Monday'."""
    while (m := CORRECTION_RE.search(sentence)) and m.start() > 0:
        left, right = sentence[: m.start()], sentence[m.end():]
        replacement = re.split(r"[,.;]| and | but ", right, maxsplit=1)[0].strip()
        rest = right[len(replacement):] if right.startswith(replacement) else right
        kind = _slot_kind(replacement)
        if kind:
            hits = list(re.finditer(kind, left, 0 if kind == SLOT_PATTERNS[-1] else re.IGNORECASE))
            if hits:
                h = hits[-1]
                sentence = left[: h.start()] + replacement + left[h.end():] + rest
                continue
        # Unknown slot: a restatement replaces the clause; a short fix replaces as many trailing words.
        n = len(replacement.split())
        if n >= 3 or n == 0:
            sentence = right
        else:
            sentence = " ".join(left.split()[:-n] + [replacement]) + rest
    return sentence.strip()


LEADING_CORRECTION = re.compile(r"^(?:no wait|no no|actually no|actually|scratch that|sorry|i mean|correction)\b", re.I)


def clean_text(text: str) -> str:
    sentences: list[str] = []
    for s in re.split(r"(?<=[.!?])\s+", remove_fillers(text)):
        if sentences and LEADING_CORRECTION.match(s):
            sentences[-1] = sentences[-1].rstrip(".!?") + ", " + s  # correction spoken as its own sentence
        elif s.strip():
            sentences.append(s)
    fixed = [resolve_self_corrections(s) for s in sentences]
    return " ".join(s[:1].upper() + s[1:] for s in fixed if s)


def split_inline_labels(transcript: str, names: list[str]) -> str:
    """Dictation arrives as one paragraph: 'Priya: ... Arjun: ...'. Break before each known speaker label."""
    labelled = {m.group(1) for m in map(SPEAKER_RE.match, transcript.splitlines()) if m}
    names = sorted({n.strip() for n in names if n.strip()} | labelled, key=len, reverse=True)  # longest first
    if not names:
        return transcript
    label = r"(?<=[.!?,])\s+(?=(?:" + "|".join(map(re.escape, names)) + r")\s*:\s)"
    return re.sub(label, "\n", transcript)


def parse_speakers(transcript: str, default_speaker: str = "Speaker", speakers: list[str] = ()) -> list[Utterance]:
    """Split a transcript into utterances. Unlabeled lines continue the previous speaker."""
    utterances: list[Utterance] = []
    speaker = default_speaker
    for line in split_inline_labels(transcript, list(speakers)).splitlines():
        if not line.strip():
            continue
        if m := SPEAKER_RE.match(line):
            speaker, body = m.group(1), m.group(2)
        else:
            body = line
        text = clean_text(body)
        if not text:
            continue
        if utterances and utterances[-1].speaker == speaker and not m:
            utterances[-1] = Utterance(speaker, f"{utterances[-1].text} {text}")
        else:
            utterances.append(Utterance(speaker, text))
    return utterances
