# Capstone run log - before

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Reproducible run, 3 fresh clones | 3 of 3 trials | PASS | PASS | PASS | MET |
| 2. Run logging, 8 trials (2 per outcome) | 8 of 8 | PASS 8/8 | PASS 8/8 | PASS 8/8 | MET |
| 3. Model-call tracing, 5 runs, 10 lines | all checks | PASS | PASS | PASS | MET |
| 4. Performance: mean <=8 s, <=1000 tokens | both limits | FAIL 12.06s/730tok | FAIL 9.88s/732tok | FAIL 9.04s/724tok | MISSED |
| 5. Failure evidence, 5 rejected-key runs | 5 of 5 | PASS 5/5 | PASS 5/5 | PASS 5/5 | MET |

- criterion 4 run 1 problems: ['mean latency 12.06s > 8']
- criterion 4 run 2 problems: ['mean latency 9.88s > 8']
- criterion 4 run 3 problems: ['mean latency 9.04s > 8']

## Criterion 1 - real output (run 1)

```
test.py tail:
------------------------------------------------------------
10 passed, 0 failed, 0 to look at, 0 skipped

You're set. See you in class.

sample query, fit card line:
Fit card: Scored this literal dream Y2K butterfly baby tee on Depop for $18 and I’m obsessed. Giving major early 2000s mall rat energy, especially styled with baggy denim and a zip-up or tucked into k
```

## Criterion 2 - real output (run 1)

```
crash trial, the line appended to logs/runs.jsonl:
{"timestamp": "2026-11-18T01:37:09.066+00:00", "run_id": "c925aa80f455", "input": null, "parsed": {}, "outcome": "crash", "error": "TypeError: expected string or bytes-like object, got 'NoneType'", "output": {"selected_item_id": null, "results_found": 0, "fit_card": null}, "duration_s": 0.001, "stage_s": {}, "model_calls": 0, "model_retries": 0, "prompt_tokens": 0, "output_tokens": 0, "cache_hits": 0}
```

## Criterion 3 - real output (run 1)

```
lines per run_id: {"1dabde62351c": 2, "03079d490147": 2, "06fff4f61a92": 2, "6d615fcd5199": 2, "176ec51a2110": 2}
total model-call lines: 10; orphans: 0
first two lines:
{"timestamp": "2026-11-18T01:39:06.545+00:00", "run_id": "1dabde62351c", "model": "gemini-3.5-flash-lite", "outcome": "ok", "error": null, "duration_s": 3.955, "attempts": 1, "cache_hit": false, "prompt_tokens": 341, "output_tokens": 139}
{"timestamp": "2026-11-18T01:39:11.517+00:00", "run_id": "1dabde62351c", "model": "gemini-3.5-flash-lite", "outcome": "ok", "error": null, "duration_s": 3.204, "attempts": 1, "cache_hit": false, "prompt_tokens": 234, "output_tokens": 72}
```

## Criterion 4 - real output (run 1)

```
measure.py summary:

10 successful runs measured, 0 failed run(s) replaced (warm-up excluded)
model       : gemini-3.5-flash-lite
seconds/run : mean 12.06  median 9.40  max 21.23
prompt tok  : mean 552 per run
output tok  : mean 178 per run
total tok   : mean 730 per run
model calls : mean 2.0 per run, 0 retries in total
```

## Criterion 5 - real output (run 1)

```
user-facing message:
I found 'Y2K Baby Tee — Butterfly Print' ($18) but couldn't reach the model that writes the outfit and caption. Your API key was rejected. Check GEMINI_API_KEY in your .env file, then run the same query again.
  (detail: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.)

1 model calls this session

model_calls.jsonl line:
{"timestamp": "2026-11-18T01:49:14.808+00:00", "run_id": "3d30878c20db", "model": "gemini-3.5-flash-lite", "outcome": "error", "error": "ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.", "duration_s": 2.182, "attempts": 1, "cache_hit": false, "prompt_tokens": 0, "output_tokens": 0}
```
