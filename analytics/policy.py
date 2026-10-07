"""Role-based access driven by TAGS on dataset columns (see data/schema_tags.json).
A column is readable by a role only if the role is allowed every tag on that column ('*' = everything)."""
import json
from pathlib import Path
import datastore

ROLES_FILE = Path(__file__).parent / "roles.json"


def load() -> dict:
    return json.loads(ROLES_FILE.read_text(encoding="utf-8"))


def save(data: dict):
    ROLES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_user(user_id: str):
    return next((u for u in load()["users"] if u["id"] == user_id), None)


def role_tags(role: str):
    r = load()["roles"].get(role)
    return None if r is None else set(r["allowed_tags"])


def column_tags(table: str, column: str) -> list:
    return datastore.schema()[table]["columns"][column]


def check(role: str, needed: set):
    """needed = {(table, column), ...}. Returns (allowed, denied_details)."""
    allowed_tags = role_tags(role)
    if allowed_tags is None:
        return False, [{"table": t, "column": c, "tags": column_tags(t, c), "missing": column_tags(t, c)} for t, c in sorted(needed)]
    if "*" in allowed_tags:
        return True, []
    denied = []
    for t, c in sorted(needed):
        tags = column_tags(t, c)
        missing = [x for x in tags if x not in allowed_tags]
        if missing:
            denied.append({"table": t, "column": c, "tags": tags, "missing": missing})
    return not denied, denied


def roles_with_access(needed: set, among=None) -> list:
    names = among if among is not None else list(load()["roles"])
    return [r for r in names if check(r, needed)[0]]
