"""Run-mode flags, per the team convention.

KB infrastructure/email-testing.md.

TEST_EMAIL and DRY_RUN default to True so a bare run can never email the real
list; the workflow sets them explicitly. Copied from ds-aa-som-floods.
"""

import os


def env_flag(name, default):
    val = os.getenv(name)
    if val is None or not val.strip():
        return default
    v = val.strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    raise ValueError(f"{name}={val!r} is not a boolean")


def mode():
    m = {
        "TEST_EMAIL": env_flag("TEST_EMAIL", True),
        "DRY_RUN": env_flag("DRY_RUN", True),
    }
    print("mode: " + " ".join(f"{k}={v}" for k, v in m.items()))
    return m
