#!/usr/bin/env python3
"""
Run FitFindr several times and summarise what the run log recorded.

    python measure.py              1 warm-up run, then 10 successful runs, cache off
    python measure.py -n 20        20 successful runs

Each run goes through agent.run_agent(), so each one writes its own record to
logs/runs.jsonl. This script only adds the summary: it reads those records back
(by run_id) and averages seconds and tokens per run. Cache is forced off, since
a cached answer costs nothing and would hide the real per-run cost.

Queries cycle through the ones in app.py that match a listing, so the average
is not one query repeated.
"""

import argparse
import json
import os
import statistics

os.environ["AI201_CACHE"] = "0"   # before config is imported

import config  # noqa: E402
import runlog  # noqa: E402
from agent import run_agent  # noqa: E402
from app import EXAMPLE_QUERIES  # noqa: E402
from utils.data_loader import get_example_wardrobe  # noqa: E402

QUERIES = EXAMPLE_QUERIES[:-1]   # the last one matches nothing, on purpose


def _records_since(offset: int) -> list[dict]:
    with open(runlog.RUNS, encoding="utf-8") as f:
        lines = f.readlines()[offset:]
    return [json.loads(line) for line in lines]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=10, help="number of successful runs to measure")
    args = ap.parse_args()
    wardrobe = get_example_wardrobe()

    # One unmeasured warm-up run, so process and connection startup on a cold
    # start is not counted. It is still logged, like every run.
    print(f"[warm-up] {QUERIES[0]}", flush=True)
    try:
        run_agent(QUERIES[0], wardrobe)
    except Exception as exc:  # noqa: BLE001 — already in the log
        print(f"    crashed: {exc}")

    try:
        with open(runlog.RUNS, encoding="utf-8") as f:
            offset = len(f.readlines())
    except OSError:
        offset = 0

    # Keep going until n runs succeed. A run that fails is not counted, is
    # replaced by another run, and is reported at the end. Gives up after 2n.
    done = failed = attempts = 0
    while done < args.n and attempts < 2 * args.n:
        query = QUERIES[attempts % len(QUERIES)]
        attempts += 1
        print(f"[{done + 1}/{args.n}] {query}", flush=True)
        try:
            session = run_agent(query, wardrobe)
            if session["error"]:
                failed += 1
            else:
                done += 1
        except Exception as exc:  # noqa: BLE001 — already in the log
            failed += 1
            print(f"    crashed: {exc}")

    recs = _records_since(offset)
    ok = [r for r in recs if r["outcome"] == "ok"]
    print(f"\n{len(ok)} successful runs measured, {failed} failed run(s) replaced "
          f"(warm-up excluded)")
    if not ok:
        return
    secs = [r["duration_s"] for r in ok]
    ptok = [r["prompt_tokens"] for r in ok]
    otok = [r["output_tokens"] for r in ok]
    print(f"model       : {config.MODEL}")
    print(f"seconds/run : mean {statistics.mean(secs):.2f}  "
          f"median {statistics.median(secs):.2f}  max {max(secs):.2f}")
    print(f"prompt tok  : mean {statistics.mean(ptok):.0f} per run")
    print(f"output tok  : mean {statistics.mean(otok):.0f} per run")
    print(f"total tok   : mean {statistics.mean(p + o for p, o in zip(ptok, otok)):.0f} per run")
    print(f"model calls : mean {statistics.mean(r['model_calls'] for r in ok):.1f} per run, "
          f"{sum(r['model_retries'] for r in ok)} retries in total")


if __name__ == "__main__":
    main()
