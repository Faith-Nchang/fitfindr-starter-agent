# Capstone run log - after

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Reproducible run, 3 fresh clones | 3 of 3 trials | PASS | PASS | PASS | MET |
| 2. Run logging, 8 trials (2 per outcome) | 8 of 8 | PASS 8/8 | PASS 8/8 | PASS 8/8 | MET |
| 3. Model-call tracing, 5 runs, 10 lines | all checks | PASS | PASS | PASS | MET |
| 4. Performance: mean <=8 s, <=1000 tokens | both limits | PASS 6.71s/741tok | FAIL 10.2s/738tok | PASS 7.69s/732tok | MISSED |
| 5. Failure evidence, 5 rejected-key runs | 5 of 5 | PASS 5/5 | PASS 5/5 | PASS 5/5 | MET |

- criterion 4 run 2 problems: ['mean latency 10.2s > 8']

## Criterion 1 - real output (run 1)

```
test.py tail:
------------------------------------------------------------
10 passed, 0 failed, 0 to look at, 0 skipped

You're set. See you in class.

sample query, fit card line:
Fit card: scored this absolute steal of a Y2K butterfly baby tee on Depop for just $18 and I’m obsessed. giving major 2000s pop princess energy whether I'm styling it with baggy denim or leaning into 
```

## Criterion 2 - real output (run 1)

```
crash trial, the line appended to logs/runs.jsonl:
{"timestamp": "2026-11-18T02:01:04.385+00:00", "run_id": "e6ea8825f3a5", "input": null, "parsed": {}, "outcome": "crash", "error": "TypeError: expected string or bytes-like object, got 'NoneType'", "output": {"selected_item_id": null, "results_found": 0, "fit_card": null}, "duration_s": 3.395, "stage_s": {"mcp_start": 3.225}, "model_calls": 0, "model_retries": 0, "prompt_tokens": 0, "output_tokens": 0, "cache_hits": 0}
```

## Criterion 3 - real output (run 1)

```
lines per run_id: {"ae72cf808705": 2, "52336a838ca3": 2, "3a2ca8d9ed03": 2, "39f6eae7dc95": 2, "461b0c452b93": 2}
total model-call lines: 10; orphans: 0
first two lines:
{"timestamp": "2026-11-18T02:03:08.332+00:00", "run_id": "ae72cf808705", "model": "gemini-3.5-flash-lite", "outcome": "ok", "error": null, "duration_s": 4.805, "attempts": 1, "cache_hit": false, "prompt_tokens": 341, "output_tokens": 102}
{"timestamp": "2026-11-18T02:03:10.247+00:00", "run_id": "ae72cf808705", "model": "gemini-3.5-flash-lite", "outcome": "ok", "error": null, "duration_s": 1.911, "attempts": 1, "cache_hit": false, "prompt_tokens": 197, "output_tokens": 66}
```

## Criterion 4 - real output (run 1)

```
measure.py summary:

10 successful runs measured, 2 failed run(s) replaced (warm-up excluded)
model       : gemini-3.5-flash-lite
seconds/run : mean 6.71  median 6.98  max 8.11
prompt tok  : mean 556 per run
output tok  : mean 185 per run
total tok   : mean 741 per run
model calls : mean 2.0 per run, 0 retries in total
```

## Criterion 5 - real output (run 1)

```
user-facing message:
I found 'Y2K Baby Tee — Butterfly Print' ($18) but couldn't reach the model that writes the outfit and caption. Your API key was rejected. Check GEMINI_API_KEY in your .env file, then run the same query again.
  (detail: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.)

1 model calls this session

model_calls.jsonl line:
{"timestamp": "2026-11-18T02:16:39.904+00:00", "run_id": "aba9d9798b36", "model": "gemini-3.5-flash-lite", "outcome": "error", "error": "ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.", "duration_s": 2.554, "attempts": 1, "cache_hit": false, "prompt_tokens": 0, "output_tokens": 0}
```
