"""Score extraction against labeled messy-speech cases.

    python -m evals.run_eval            # deterministic extractor
    python -m evals.run_eval --llm      # Claude extractor (needs ANTHROPIC_API_KEY)
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

from app.conflicts import SIMILARITY_THRESHOLD, _normalise_value, similarity
from app.extract import extract
from app.main import load_env

CASES = Path(__file__).with_name("cases.json")


def key(item: dict) -> tuple:
    if item["kind"] == "action":
        return ("action", (item.get("owner") or "").lower(), item.get("deadline"))
    return ("decision", (item.get("subject") or "").lower(), (item.get("value") or "").lower())


def same(got: tuple, want: tuple, base: date) -> bool:
    """Actions match exactly; decisions match the way the conflict engine compares them."""
    if got[0] != want[0]:
        return False
    if got[0] == "action":
        return got == want
    subject_ok = similarity([got[1]], [want[1]])[0, 0].item() >= SIMILARITY_THRESHOLD
    return subject_ok and _normalise_value(got[2], base) == _normalise_value(want[2], base)


def match(got: set, want: set, base: date) -> tuple[set, set, set]:
    hit, unmatched_got = set(), set(got)
    for w in want:
        g = next((g for g in unmatched_got if same(g, w, base)), None)
        if g:
            hit.add(w)
            unmatched_got.discard(g)
    return hit, unmatched_got, want - hit


def main() -> None:
    load_env()
    if "--llm" not in sys.argv:
        os.environ.pop("ANTHROPIC_API_KEY", None)
    tp = fp = fn = 0
    extractor = "?"
    for case in json.loads(CASES.read_text()):
        result = extract(case["transcript"], date.fromisoformat(case["date"]), [], [])
        extractor = result.extractor
        got = {key(vars(i)) for i in result.items}
        want = {key(i) for i in case["expected"]}
        hit, extra, missed = match(got, want, date.fromisoformat(case["date"]))
        tp, fp, fn = tp + len(hit), fp + len(extra), fn + len(missed)
        ok = not extra and not missed
        print(f"{'PASS' if ok else 'MISS'}  {case['name']}" + ("" if ok else f"\n      extra  {sorted(extra)}\n      missed {sorted(missed)}"))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    summary = {"extractor": extractor, "precision": round(precision, 3), "recall": round(recall, 3), "tp": tp, "fp": fp, "fn": fn}
    print(json.dumps(summary))
    Path(__file__).with_name(f"results_{'llm' if '--llm' in sys.argv else 'rules'}.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
