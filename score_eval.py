#!/usr/bin/env python3
"""
Score a run_eval.py run against the five criteria in criteria.md.

    python score_eval.py results/run_<stamp>_before.json

run_eval.py leaves PASS/FAIL to the person. These are the rules, written down
once so every try is read the same way. They are mechanical readings of the
criteria; each try's real output is still in the .md next to the .json.

  1. PASS if the run finished with no error, an outfit, and a non-empty fit card.
  2. PASS if the run stopped with an error message that tells the user what to
     try, and suggest_outfit and create_fit_card never ran.
  3. PASS if the run finished, session["selected_item"] is the first search
     result, and the trace shows that same title going into suggest_outfit.
  4. PASS if the run finished and the fit card is non-empty and contains a
     content word (4+ letters) from the selected item's title.
  5. PASS if search returned something and every listing is at or under the
     query's max_price. This is scored from search_results alone, so a model
     outage later in the run does not change it.

A FAIL caused by the model being unreachable is marked "(outage)", so it can be
told apart from a FAIL caused by the agent.
"""

import json
import re
import sys

TARGETS = {1: 4, 2: 5, 3: 5, 4: 4, 5: 5}
NAMES = {
    1: "Matching query completes all three tools",
    2: "Impossible query stops before the second tool",
    3: "Selected item is the item passed to suggest_outfit",
    4: "Fit card refers to the selected item",
    5: "Nothing returned is over the max price",
}
GENERIC = {"with", "from", "that", "this", "and", "the"}


def _outage(session):
    err = (session or {}).get("error") or ""
    return "couldn't reach the model" in err.lower()


def _finished(session):
    return bool(
        session
        and not session.get("error")
        and session.get("outfit_suggestion")
        and session.get("fit_card")
    )


def _words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 4} - GENERIC


def score_try(criterion, record):
    """Return (passed, reason)."""
    session = record.get("session")
    if record.get("crashed") or session is None:
        return False, f"crashed: {record.get('crashed')}"
    trace = record.get("trace") or ""

    if criterion == 1:
        if _finished(session):
            return True, ""
        if _outage(session):
            return False, "(outage)"
        return False, f"did not finish: {session.get('error')}"

    if criterion == 2:
        error = session.get("error") or ""
        ran_later = (
            session.get("outfit_suggestion")
            or session.get("fit_card")
            or re.search(r"\]\s+suggest_outfit", trace)
        )
        if not error:
            return False, "no error message"
        if ran_later:
            return False, "a later tool still ran"
        if "try" not in error.lower() and "change" not in error.lower():
            return False, "message doesn't say what to change"
        return True, ""

    if criterion == 3:
        item = session.get("selected_item")
        results = session.get("search_results") or []
        if not item or not results:
            return False, "no item selected"
        if item != results[0]:
            return False, "selected_item is not the first search result"
        passed_in = re.search(r"\]\s+suggest_outfit\s+in:\s+item='(.*?)',", trace)
        if not passed_in:
            return False, "(outage)" if _outage(session) else "suggest_outfit never ran"
        if passed_in.group(1) != item["title"]:
            return False, f"suggest_outfit got '{passed_in.group(1)}'"
        return True, ""

    if criterion == 4:
        if not _finished(session):
            return False, "(outage)" if _outage(session) else "no fit card"
        shared = _words(session["fit_card"]) & _words(session["selected_item"]["title"])
        if not shared:
            return False, "caption shares no word with the item title"
        return True, ""

    if criterion == 5:
        limit = (session.get("parsed") or {}).get("max_price")
        results = session.get("search_results") or []
        if limit is None:
            return False, "query had no max_price"
        if not results:
            return False, "search returned nothing"
        over = [r for r in results if r["price"] > limit]
        if over:
            return False, f"{len(over)} over ${limit:g}: {over[0]['title']} ${over[0]['price']}"
        return True, ""

    return False, "unknown criterion"


def main(path):
    rows = json.load(open(path, encoding="utf-8"))
    print("| Criterion | Target | " + " | ".join(f"Try {i}" for i in range(1, 6))
          + " | Verdict |")
    print("|---|---|" + "---|" * 5 + "---|")
    notes = []
    for row in rows:
        n = row["scenario"].get("criterion")
        if not n:
            continue
        cells, passes = [], 0
        for i, rec in enumerate(row["tries"], 1):
            ok, why = score_try(n, rec)
            passes += ok
            cells.append("PASS" if ok else "FAIL")
            if not ok:
                notes.append(f"  criterion {n}, try {i}: {why}")
        target = TARGETS[n]
        verdict = "MET" if passes >= target else "MISSED"
        print(f"| {n}. {NAMES[n]} | {target} of 5 | " + " | ".join(cells)
              + f" | {verdict} ({passes}/5) |")
    if notes:
        print("\nWhy each FAIL:")
        print("\n".join(notes))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
