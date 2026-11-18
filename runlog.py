"""
Structured run log for FitFindr (capstone, Shape A).

Two append-only JSONL files in logs/, one JSON object per line, named fields:

  logs/runs.jsonl         one record per run_agent() call, written even when
                          the run fails
  logs/model_calls.jsonl  one record per generate() call, tagged with the
                          run_id of the run that caused it

model_calls.jsonl is a separate file because create_fit_card runs inside the
MCP server, a different process. The run id travels there in the environment
variable AI201_RUN_ID, and the file is how the two processes report to one
place. run_agent() reads it back to put token totals on the run record.

Logging must never break a run, so every write swallows its own errors.
"""

import json
import os
from datetime import datetime, timezone

import config

LOG_DIR = config.ROOT / "logs"
RUNS = LOG_DIR / "runs.jsonl"
MODEL_CALLS = LOG_DIR / "model_calls.jsonl"
RUN_ID_ENV = "AI201_RUN_ID"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _append(path, record: dict) -> None:
    try:
        LOG_DIR.mkdir(exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — a log failure must not kill a run
        pass


def log_run(record: dict) -> None:
    _append(RUNS, record)


def log_model_call(record: dict) -> None:
    record = {"timestamp": now_iso(), "run_id": os.environ.get(RUN_ID_ENV), **record}
    _append(MODEL_CALLS, record)


def model_calls_for(run_id: str) -> list[dict]:
    """Every model-call record written for one run, from any process."""
    calls = []
    try:
        with open(MODEL_CALLS, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("run_id") == run_id:
                    calls.append(rec)
    except OSError:
        pass
    return calls
