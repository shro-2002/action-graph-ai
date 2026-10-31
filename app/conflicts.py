"""Deterministic conflict detection against cross-meeting decision memory.

PyTorch finds candidate decisions about the same subject (cosine similarity of
hashed bag-of-words vectors); fixed rules then decide whether the values clash.
"""
import hashlib
import re
from dataclasses import dataclass
from datetime import date

import torch

from app.dates import parse_deadline

DIM = 1024
SIMILARITY_THRESHOLD = 0.5
STOPWORDS = set(
    "a an the of to for on in and or is are be will we our this that it with by as at from "
    "going go use using decided decide decision lets let us final".split()
)
NEGATION_RE = re.compile(r"\b(not|no longer|won't|will not|don't|drop|dropped|cancel|cancelled|scrap|kill|pause|postpone)\b", re.I)


@dataclass(frozen=True)
class Memory:
    id: int
    subject: str
    value: str | None
    text: str
    meeting_title: str
    meeting_date: str
    speaker: str | None


@dataclass(frozen=True)
class Conflict:
    memory_id: int
    similarity: float
    reason: str


def _tokens(text: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def embed(texts: list[str]) -> torch.Tensor:
    """Feature-hashed bag of unigrams+bigrams, L2-normalised. Deterministic across runs."""
    matrix = torch.zeros(len(texts), DIM)
    for row, text in enumerate(texts):
        for tok in _tokens(text):
            idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % DIM
            matrix[row, idx] += 1.0
    return torch.nn.functional.normalize(matrix, dim=1)


def similarity(a: list[str], b: list[str]) -> torch.Tensor:
    if not a or not b:
        return torch.zeros(len(a), len(b))
    return embed(a) @ embed(b).T


def _normalise_value(value: str | None, base: date) -> str | None:
    if not value:
        return None
    if iso := parse_deadline(value, base):
        return iso
    return " ".join(_tokens(value)) or value.strip().lower()


def find_conflict(subject: str, value: str | None, text: str, meeting_date: date, memory: list[Memory]) -> Conflict | None:
    """Return the strongest clash between a new decision and remembered decisions."""
    if not memory:
        return None
    scores = similarity([subject], [m.subject for m in memory])[0]
    new_value = _normalise_value(value, meeting_date)
    best: Conflict | None = None
    for m, score in zip(memory, scores.tolist()):
        if score < SIMILARITY_THRESHOLD:
            continue
        old_value = _normalise_value(m.value, date.fromisoformat(m.meeting_date))
        where = f"'{m.meeting_title}' ({m.meeting_date}{', ' + m.speaker if m.speaker else ''})"
        if new_value and old_value and new_value != old_value:
            reason = f"Contradicts {where}: {m.subject} was “{m.value}”, now “{value}”."
        elif bool(NEGATION_RE.search(text)) != bool(NEGATION_RE.search(m.text)):
            reason = f"Reverses {where}: earlier “{m.text}”."
        else:
            continue
        if best is None or score > best.similarity:
            best = Conflict(m.id, round(score, 3), reason)
    return best
