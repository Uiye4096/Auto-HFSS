"""
_uid.py — shared UID counter for 185g simulation cases.

Reads/writes  <model_dir>/runs/uid_counter.json
Each call to next_uid() returns a zero-padded 3-digit string and
increments the persistent counter.
"""
import json
from pathlib import Path

_COUNTER_PATH = Path(__file__).parent.parent / "runs" / "uid_counter.json"


def _load():
    if _COUNTER_PATH.exists():
        return json.loads(_COUNTER_PATH.read_text(encoding="utf-8"))["next"]
    return 1


def _save(n):
    _COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    _COUNTER_PATH.write_text(json.dumps({"next": n}, indent=2), encoding="utf-8")


def next_uid(count=1):
    """Return the next UID string (or list of strings if count > 1) and persist counter."""
    start = _load()
    end   = start + count
    _save(end)
    ids = [f"{i:03d}" for i in range(start, end)]
    return ids if count > 1 else ids[0]


def peek_next():
    """Return the next UID without incrementing."""
    return f"{_load():03d}"
