"""Centralized clock for deterministic evaluation dates."""
import os
from datetime import date


def today() -> date:
    """Return today's date, or EVAL_AS_OF_DATE if set for reproducibility."""
    eval_date = os.environ.get("EVAL_AS_OF_DATE")
    if eval_date:
        try:
            return date.fromisoformat(eval_date)
        except ValueError:
            pass  # Fall through to real date
    return date.today()
