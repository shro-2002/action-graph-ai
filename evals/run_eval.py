"""Score extraction against labeled messy-speech cases.

    python -m evals.run_eval            # deterministic extractor
    python -m evals.run_eval --llm      # Claude extractor (needs ANTHROPIC_API_KEY)
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

from app.extract import extract
from app.main import load_env

CASES = Path(__file__).with_name("cases.json")


def key(item: dict) -> tuple:
    if item["kind"] == "action":
        return ("action", (item.get("owner") or "").lower(), item.get("deadline"))
    return ("decision", (item.get("subject") or "").lower(), (item.get("value") or "").lower())


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
        hit = got & want
        tp, fp, fn = tp + len(hit), fp + len(got - want), fn + len(want - got)
        mark = "PASS" if got == want else "MISS"
        print(f"{mark}  {case['name']}" + ("" if got == want else f"\n      got  {sorted(got - want)}\n      want {sorted(want - got)}"))
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    summary = {"extractor": extractor, "precision": round(precision, 3), "recall": round(recall, 3), "tp": tp, "fp": fp, "fn": fn}
    print(json.dumps(summary))
    Path(__file__).with_name(f"results_{'llm' if '--llm' in sys.argv else 'rules'}.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
