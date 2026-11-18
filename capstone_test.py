#!/usr/bin/env python3
"""
Capstone test: the five criteria in criteria.md ("Capstone criteria"), three
trials each, changing nothing between trials.

    python capstone_test.py before            all five criteria
    python capstone_test.py after 2 3 5       only criteria 2, 3 and 5
    python capstone_test.py before 1          clean-checkout trials only

Writes results/capstone_<label>.json (every check, every trial) and
results/capstone_<label>.md (the run log table and real output samples).

Every trial that touches a model runs with the cache off. Trials that need a
separate process (clean clone, rejected key, crash) run as real subprocesses,
because a rejected key set in-process would be ignored by an already-built
client.
"""

import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).parent
RUNS = ROOT / "logs" / "runs.jsonl"
CALLS = ROOT / "logs" / "model_calls.jsonl"
PY = sys.executable
TRIALS = 3
MATCH_Q = "vintage graphic tee under $30"
IMPOSSIBLE_Q = "designer ballgown size XXS under $5"

SAMPLES: dict[int, str] = {}   # criterion -> real output from one trial


def lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def new_records(path: Path, before: int) -> tuple[list[dict], list[str]]:
    raw = lines(path)[before:]
    out = []
    for line in raw:
        try:
            out.append(json.loads(line))
        except ValueError:
            out.append({"_invalid": line})
    return out, raw


def cli(query: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "AI201_CACHE": "0", "PYTHONIOENCODING": "utf-8", **(env_extra or {})}
    return subprocess.run([PY, "app.py", "ask", query], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=300)


# ── criterion 1: reproducible run ────────────────────────────────────────────

def c1_trial(i: int) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="fitfindr_clone_"))
    dest = tmp / "fresh"
    steps = []
    try:
        def run(cmd, **kw):
            return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                                  timeout=600, **kw)
        r = run(["git", "clone", "-q", str(ROOT), str(dest)])
        steps.append(("clone", r.returncode))
        r = run([PY, "-m", "venv", ".venv"], cwd=dest)
        steps.append(("venv", r.returncode))
        vpy = dest / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        r = run([str(vpy), "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=dest)
        steps.append(("pip install", r.returncode))
        shutil.copy(ROOT / ".env", dest / ".env")   # the only file touched
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "AI201_CACHE": "0"}
        t = run([str(vpy), "test.py"], cwd=dest, env=env)
        passed = "10 passed" in t.stdout
        q = run([str(vpy), "app.py", "ask", MATCH_Q], cwd=dest, env=env)
        m = re.search(r"Fit card:\s*(\S.*)", q.stdout)
        ok = passed and m is not None
        if i == 0:
            SAMPLES[1] = ("test.py tail:\n" + "\n".join(t.stdout.strip().splitlines()[-4:])
                          + "\n\nsample query, fit card line:\n"
                          + (m.group(0)[:200] if m else "(none)"))
        return {"pass": ok, "test_py_10_passed": passed, "fit_card": bool(m),
                "steps": steps}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── criterion 2: run logging ─────────────────────────────────────────────────

CRASH_SNIPPET = (
    "import os; os.environ['AI201_CACHE']='0'\n"
    "from agent import run_agent\n"
    "from utils.data_loader import get_example_wardrobe\n"
    "run_agent(None, get_example_wardrobe())\n"
)


def c2_trial(i: int) -> dict:
    plan = [("ok", MATCH_Q, {}), ("ok", "denim jacket under $50", {}),
            ("no_results", IMPOSSIBLE_Q, {}), ("no_results", "designer ballgown size XXS under $5", {}),
            ("error", MATCH_Q, {"GEMINI_API_KEY": "bad"}),
            ("error", "90s track jacket in size M", {"GEMINI_API_KEY": "bad"}),
            ("crash", None, {}), ("crash", None, {})]
    ids, results, sample = set(), [], None
    for expected, query, env_extra in plan:
        before = len(lines(RUNS))
        if expected == "crash":
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            subprocess.run([PY, "-c", CRASH_SNIPPET], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=120)
        else:
            cli(query, env_extra)
        recs, raw = new_records(RUNS, before)
        problems = []
        if len(recs) != 1:
            problems.append(f"{len(recs)} lines appended, expected 1")
        else:
            r = recs[0]
            if "_invalid" in r:
                problems.append("line is not valid JSON")
            else:
                for k in ("run_id", "input", "outcome", "duration_s"):
                    if k not in r:
                        problems.append(f"missing {k}")
                if r.get("run_id") in ids:
                    problems.append("run_id not unique")
                ids.add(r.get("run_id"))
                if not isinstance(r.get("duration_s"), (int, float)):
                    problems.append("duration_s not a number")
                if r.get("outcome") != expected:
                    problems.append(f"outcome {r.get('outcome')!r}, observed {expected!r}")
                if expected == "ok":
                    if r.get("error") is not None or not (r.get("output") or {}).get("selected_item_id"):
                        problems.append("ok record: error not null or no selected_item_id")
                elif not (isinstance(r.get("error"), str) and r["error"].strip()):
                    problems.append("non-ok record has empty error")
        results.append({"expected": expected, "ok": not problems, "problems": problems})
        if i == 0 and expected in ("no_results", "crash") and sample is None and expected == "crash":
            sample = raw[0][:700] if raw else "(no line)"
    if i == 0:
        SAMPLES[2] = "crash trial, the line appended to logs/runs.jsonl:\n" + (sample or "")
    n_ok = sum(r["ok"] for r in results)
    return {"pass": n_ok == 8, "score": f"{n_ok}/8", "trials": results}


# ── criterion 3: model-call tracing ──────────────────────────────────────────

def c3_trial(i: int) -> dict:
    os.environ["AI201_CACHE"] = "0"
    sys.path.insert(0, str(ROOT))
    import importlib
    import config
    config.CACHE_ENABLED = False
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe
    queries = ["vintage graphic tee under $30", "90s track jacket in size M",
               "silk slip dress in midi length under $40", "platform sneakers size 8",
               "denim jacket under $50"]
    b_runs, b_calls = len(lines(RUNS)), len(lines(CALLS))
    for q in queries:
        run_agent(q, get_example_wardrobe())
    runs, _ = new_records(RUNS, b_runs)
    calls, raw = new_records(CALLS, b_calls)
    problems = []
    if len(calls) != 10:
        problems.append(f"{len(calls)} model-call lines, expected 10")
    for r in runs:
        mine = [c for c in calls if c.get("run_id") == r["run_id"]]
        if len(mine) != 2:
            problems.append(f"run {r['run_id']}: {len(mine)} lines, expected 2")
        if any(c.get("outcome") != "ok" for c in mine):
            problems.append(f"run {r['run_id']}: a call was not ok")
        if r.get("model_calls") != 2:
            problems.append(f"run {r['run_id']}: model_calls field is {r.get('model_calls')}")
    known = {r["run_id"] for r in runs}
    orphans = [c for c in calls if c.get("run_id") not in known]
    if orphans:
        problems.append(f"{len(orphans)} line(s) with null or unknown run_id")
    if i == 0:
        SAMPLES[3] = ("lines per run_id: "
                      + json.dumps({r['run_id']: sum(c.get('run_id') == r['run_id'] for c in calls)
                                    for r in runs})
                      + f"\ntotal model-call lines: {len(calls)}; orphans: {len(orphans)}"
                      + "\nfirst two lines:\n" + "\n".join(raw[:2]))
    return {"pass": not problems, "problems": problems, "lines": len(calls),
            "orphans": len(orphans)}


# ── criterion 4: performance and cost ────────────────────────────────────────

def c4_trial(i: int) -> dict:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    p = subprocess.run([PY, "measure.py"], cwd=ROOT, env=env, capture_output=True,
                       text=True, encoding="utf-8", timeout=900)
    out = p.stdout
    m_s = re.search(r"seconds/run : mean ([\d.]+)", out)
    m_t = re.search(r"total tok\s+: mean ([\d.]+)", out)
    m_n = re.search(r"(\d+) successful runs measured, (\d+) failed", out)
    if not (m_s and m_t and m_n):
        return {"pass": False, "problems": ["could not parse measure.py output"], "output": out[-800:]}
    secs, toks, n, failed = float(m_s[1]), float(m_t[1]), int(m_n[1]), int(m_n[2])
    problems = []
    if n != 10:
        problems.append(f"only {n} successful runs")
    if secs > 8:
        problems.append(f"mean latency {secs}s > 8")
    if toks > 1000:
        problems.append(f"mean tokens {toks} > 1000")
    if i == 0:
        SAMPLES[4] = "measure.py summary:\n" + "\n".join(out.strip().splitlines()[-8:])
    return {"pass": not problems, "problems": problems, "mean_s": secs,
            "mean_tokens": toks, "replaced": failed}


# ── criterion 5: failure evidence ────────────────────────────────────────────

def c5_trial(i: int) -> dict:
    good, details, sample = 0, [], None
    for k in range(5):
        before_r, before_c = len(lines(RUNS)), len(lines(CALLS))
        p = cli(MATCH_Q, {"GEMINI_API_KEY": "bad"})
        text = p.stdout
        runs, _ = new_records(RUNS, before_r)
        calls, craw = new_records(CALLS, before_c)
        problems = []
        low = text.lower()
        if not ("api key" in low and "rejected" in low):
            problems.append("message does not say the key was rejected")
        if "GEMINI_API_KEY" not in text:
            problems.append("message does not name GEMINI_API_KEY")
        if len(runs) != 1 or runs[0].get("outcome") != "error":
            problems.append("no single run record with outcome error")
        else:
            rid = runs[0]["run_id"]
            match = [c for c in calls if c.get("run_id") == rid and c.get("outcome") == "error"]
            if not match:
                problems.append("no error model-call record with the same run_id")
        details.append(problems)
        good += not problems
        if i == 0 and k == 0:
            sample = ("user-facing message:\n" + text.strip()[:500]
                      + "\n\nmodel_calls.jsonl line:\n" + (craw[0][:400] if craw else "(none)"))
    if i == 0:
        SAMPLES[5] = sample or ""
    return {"pass": good == 5, "score": f"{good}/5", "problems": [p for p in details if p]}


CRITERIA = {
    1: ("Reproducible run, 3 fresh clones", "3 of 3 trials", c1_trial),
    2: ("Run logging, 8 trials (2 per outcome)", "8 of 8", c2_trial),
    3: ("Model-call tracing, 5 runs, 10 lines", "all checks", c3_trial),
    4: ("Performance: mean <=8 s, <=1000 tokens", "both limits", c4_trial),
    5: ("Failure evidence, 5 rejected-key runs", "5 of 5", c5_trial),
}


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "before"
    wanted = [int(a) for a in sys.argv[2:]] or list(CRITERIA)
    results: dict[int, list[dict]] = {}
    for c in wanted:
        name, target, fn = CRITERIA[c]
        results[c] = []
        for i in range(TRIALS):
            t0 = time.time()
            print(f"criterion {c} ({name}) run {i + 1}/{TRIALS} ...", flush=True)
            try:
                res = fn(i)
            except Exception as exc:  # noqa: BLE001 — a harness error is a result
                res = {"pass": False, "problems": [f"harness error: {type(exc).__name__}: {exc}"]}
            res["seconds"] = round(time.time() - t0, 1)
            results[c].append(res)
            print(f"    -> {'PASS' if res['pass'] else 'FAIL'}  "
                  f"{res.get('score') or res.get('problems') or ''}", flush=True)

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / f"capstone_{label}.json").write_text(
        json.dumps({"label": label, "results": results}, indent=2), encoding="utf-8")

    md = [f"# Capstone run log - {label}", "",
          "| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |", "|---|---|---|---|---|---|"]
    for c in wanted:
        name, target, _ = CRITERIA[c]
        cells = []
        for r in results[c]:
            tag = "PASS" if r["pass"] else "FAIL"
            extra = r.get("score") or (f"{r['mean_s']}s/{r['mean_tokens']:.0f}tok" if "mean_s" in r else "")
            cells.append(f"{tag} {extra}".strip())
        verdict = "MET" if all(r["pass"] for r in results[c]) else "MISSED"
        md.append(f"| {c}. {name} | {target} | " + " | ".join(cells) + f" | {verdict} |")
    md.append("")
    for c in wanted:
        for i, r in enumerate(results[c]):
            if r.get("problems"):
                md.append(f"- criterion {c} run {i + 1} problems: {r['problems']}")
    md.append("")
    for c, text in sorted(SAMPLES.items()):
        md += [f"## Criterion {c} - real output (run 1)", "", "```", text, "```", ""]
    (out / f"capstone_{label}.md").write_text("\n".join(md), encoding="utf-8")
    print("\n" + "\n".join(md[:12]))


if __name__ == "__main__":
    main()
