#!/usr/bin/env python3
"""
Fault-injection check for the 503 retry improvement.

The real run_eval.py can't show the improvement unless the model service
happens to be overloaded during the run. This forces it: the model client fails
the first attempt of every call with a 503, then answers normally. It runs the
real suggest_outfit tool (real model, real prompt) five times with the old
generate.py (git HEAD) and five times with the current one.

    python fault_test.py
"""

import importlib.util
import subprocess
import sys
import types

import config
import tools
from utils.data_loader import get_example_wardrobe, load_listings

config.CACHE_ENABLED = False
ITEM = load_listings()[0]
WARDROBE = get_example_wardrobe()
TRIES = 5


def load_old_generate():
    """generate.py as it was at the last commit, before the retry change."""
    source = subprocess.run(
        ["git", "show", "HEAD:generate.py"], capture_output=True, text=True,
        encoding="utf-8", check=True,
    ).stdout
    module = types.ModuleType("generate_old")
    module.__file__ = "generate_old.py"
    exec(compile(source, "generate_old.py", "exec"), module.__dict__)
    return module


def inject_503_on_first_attempt(module):
    """Wrap the client so each generate() call's first attempt raises a 503."""
    real_get_client = module._get_client
    state = {"fail_next": True}

    class Models:
        def __init__(self, models):
            self._models = models

        def generate_content(self, **kwargs):
            if state["fail_next"]:
                state["fail_next"] = False
                raise Exception(
                    "503 UNAVAILABLE. {'error': {'code': 503, 'message': "
                    "'This model is currently experiencing high demand.', "
                    "'status': 'UNAVAILABLE'}}"
                )
            return self._models.generate_content(**kwargs)

    class Client:
        def __init__(self, client):
            self.models = Models(client.models)

    module._get_client = lambda: Client(real_get_client())
    return state


def run(label, generate_module):
    tools.generate = generate_module.generate
    state = inject_503_on_first_attempt(generate_module)
    ok = 0
    for i in range(1, TRIES + 1):
        state["fail_next"] = True
        try:
            text = tools.suggest_outfit(ITEM, WARDROBE)
            passed = bool(text and text.strip())
            result = "PASS" if passed else "FAIL (empty)"
        except Exception as exc:  # noqa: BLE001
            passed = False
            result = f"FAIL ({type(exc).__name__})"
        ok += passed
        print(f"  {label} try {i}: {result}", flush=True)
    return ok


if __name__ == "__main__":
    import generate

    print("First attempt of every model call fails with a 503.\n")
    old = run("old generate.py", load_old_generate())
    new = run("new generate.py", generate)
    print(f"\nold generate.py: {old}/{TRIES} suggest_outfit calls succeeded")
    print(f"new generate.py: {new}/{TRIES} suggest_outfit calls succeeded")
