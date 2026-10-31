"""Compare LLM providers on the same frozen scoring as run_eval, plus speaker, contradiction, latency and cost.

    LLM_PROVIDER=anthropic python -m evals.compare_providers
    LLM_PROVIDER=meta      python -m evals.compare_providers

A case where the provider failed (rules fallback ran) scores as zero items and counts as a schema failure.
Writes evals/compare_<provider>.json.
"""
import json
import re
import os
import time
from datetime import date
from pathlib import Path

from app import db, extract as ex, service
from app.main import load_env
from evals.run_eval import key, match

HERE = Path(__file__).parent
# USD per 1M tokens (input, output), list prices as of 31 Oct 2026.
# Meta: dev.meta.ai/docs/pricing-rate-limits (muse-spark-1.3, standard). Claude: claude-sonnet-5-5 list price.
PRICES = {"meta": (1.25, 4.25), "anthropic": (float(os.getenv("CLAUDE_PRICE_IN", "2")), float(os.getenv("CLAUDE_PRICE_OUT", "10")))}
PAIR = [  # the demo scenario: speakers and contradictions
    ("Pricing review", date(2026, 10, 24), ["Nisha", "Dev", "Karan", "Nisha"],
     "Nisha: Okay so um, for the paid tier we're going with seat-based pricing, nine dollars per seat. Dev: I'll, uh, update the pricing "
     "page copy by Thursday. Karan: And the free trial stays at fourteen days. Nisha: Karan, can you set up the Stripe test products by November second?"),
    ("Pricing follow-up", date(2026, 10, 31), ["Nisha", "Karan", "Karan", "Dev"],
     "Nisha: Finance came back, we're changing the paid tier to twelve dollars per seat. Karan: And the trial, we're cutting it to seven days, "
     "no sorry, ten days. Karan: I'll announce the new price on LinkedIn by Friday. Dev: I might look into a churn dashboard at some point."),
]


LEFTOVER = re.compile(r"\b(?:um+|uh+|you know|no sorry|no wait|scratch that|i mean)\b", re.I)


def timed(fn, *args):
    start = time.perf_counter()
    out = fn(*args)
    return out, time.perf_counter() - start


def score_set(name: str, provider: str) -> dict:
    tp = fp = fn = schema_ok = date_hit = date_total = 0
    latencies, tokens_in, tokens_out, failures = [], 0, 0, []
    for case in json.loads((HERE / name).read_text()):
        base = date.fromisoformat(case["date"])
        result, secs = timed(ex.extract, case["transcript"], base, [], [])
        latencies.append(secs)
        native = not result.extractor.startswith("rules")
        schema_ok += native
        tokens_in += result.usage.get("input_tokens") or 0
        tokens_out += result.usage.get("output_tokens") or 0
        got = {key(vars(i)) for i in result.items} if native else set()
        want = {key(i) for i in case["expected"]}
        hit, extra, missed = match(got, want, base)
        tp, fp, fn = tp + len(hit), fp + len(extra), fn + len(missed)
        wanted_dates = {i["deadline"] for i in case["expected"] if i["kind"] == "action" and i.get("deadline")}
        date_total += len(wanted_dates)
        date_hit += len(wanted_dates & {g[2] for g in got if g[0] == "action"})
        if not native or extra or missed:
            failures.append({"case": case["name"], "fallback": not native, "notes": result.notes,
                             "extra": sorted(map(list, extra)), "missed": sorted(map(list, missed))})
    n = len(latencies)
    return {"cases": n, "precision": round(tp / (tp + fp), 3) if tp + fp else 1.0, "recall": round(tp / (tp + fn), 3) if tp + fn else 1.0,
            "tp": tp, "fp": fp, "fn": fn, "schema_valid": f"{schema_ok}/{n}", "deadline_accuracy": f"{date_hit}/{date_total}",
            "latency_s": {"mean": round(sum(latencies) / n, 2), "max": round(max(latencies), 2)},
            "tokens": {"input": tokens_in, "output": tokens_out}, "failures": failures}


def score_pair(provider: str) -> dict:
    db.connect(":memory:")
    speakers_ok = speakers_total = leftovers = 0
    meetings = []
    for title, when, want_speakers, transcript in PAIR:
        m = service.ingest(title, when, transcript, ["Nisha", "Dev", "Karan"])
        got = [u["speaker"] for u in m["utterances"]]
        leftovers += sum(len(LEFTOVER.findall(u["text"])) for u in m["utterances"])
        speakers_total += len(want_speakers)
        speakers_ok += sum(g == w for g, w in zip(got, want_speakers))
        meetings.append(m)
        for it in m["items"]:
            service.approve(it["id"], {})  # meeting 1 becomes memory for meeting 2
    first, second = meetings
    memory_subjects = {i["subject"] for i in first["items"] if i["kind"] == "decision"}
    flagged = [i for i in second["items"] if i["conflict_with"]]
    return {"extractors": [m["extractor"] for m in meetings], "speaker_accuracy": f"{speakers_ok}/{speakers_total}",
            "contradictions_flagged": f"{len(flagged)}/2",
            "fillers_or_corrections_left_in_clean_transcript": leftovers,
            "clean_transcript": [[u["speaker"], u["text"]] for m in meetings for u in m["utterances"]], "conflict_reasons": [i["conflict_reason"] for i in flagged],
            "reused_memory_subject": sorted(i["subject"] for i in second["items"] if i["kind"] == "decision" and i["subject"] in memory_subjects),
            "meeting2_items": [(i["kind"], i["owner"], i["deadline"], i["subject"], i["value"]) for i in second["items"]]}


def main() -> None:
    load_env()
    provider = ex.provider_name()
    report = {"provider": provider, "dev": score_set("cases.json", provider), "holdout": score_set("holdout_cases.json", provider),
              "pair": score_pair(provider)}
    price_in, price_out = PRICES[provider]
    tokens = [report[s]["tokens"] for s in ("dev", "holdout")]
    total_in, total_out = sum(t["input"] for t in tokens), sum(t["output"] for t in tokens)
    report["cost_usd_dev_plus_holdout"] = round(total_in / 1e6 * price_in + total_out / 1e6 * price_out, 4)
    (HERE / f"compare_{provider}{os.getenv('COMPARE_TAG', '')}.json").write_text(json.dumps(report, indent=2, default=str))
    print(json.dumps(report, indent=1, default=str)[:6000])


if __name__ == "__main__":
    main()
