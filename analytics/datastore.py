"""Loads the fintech tables and the tag schema that is anchored to them."""
import json
from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
_cache = {}


def schema() -> dict:
    return json.loads((DATA_DIR / "schema_tags.json").read_text(encoding="utf-8"))["tables"]


def table(name: str) -> pd.DataFrame:
    if name not in _cache:
        meta = schema()[name]
        df = pd.read_csv(DATA_DIR / meta["file"])
        df[meta["date_column"]] = pd.to_datetime(df[meta["date_column"]])
        _cache[name] = df
    return _cache[name]


def reload():
    _cache.clear()


def anchor() -> dict:
    """Dates are anchored to the data (not the clock): 'last year' = latest FULL year in the data."""
    latest = max(table(t)[m["date_column"]].max() for t, m in schema().items())
    earliest = min(table(t)[m["date_column"]].min() for t, m in schema().items())
    full_year = latest.year if latest.month == 12 else latest.year - 1
    return {"latest_date": latest, "earliest_date": earliest,
            "latest_year": int(latest.year), "latest_full_year": int(full_year)}
