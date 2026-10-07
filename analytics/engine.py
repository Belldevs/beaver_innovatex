"""Beaver chat engine: question -> plan -> TAG ACCESS CHECK -> calculation -> answer."""
import json
import os
from datetime import datetime
from pathlib import Path
import datastore
import kpi_engine as kpi
import planner
import policy

CURRENCY = os.getenv("BEAVER_CURRENCY", "$")
AUDIT_FILE = Path(__file__).parent / "audit.log"


# ───────────── formatting ─────────────
def fmt(v, unit):
    if v is None:
        return "n/a"
    if unit == "currency":
        a = abs(v)
        s = (f"{a / 1e9:.2f}B" if a >= 1e9 else f"{a / 1e6:.2f}M" if a >= 1e6 else f"{a / 1e3:.1f}K" if a >= 1e4 else f"{a:,.0f}")
        return f"{'-' if v < 0 else ''}{CURRENCY}{s}"
    if unit == "percent":
        return f"{v * 100:.1f}%"
    if unit == "score":
        return f"{v:.0f}"
    return f"{v:,.0f}"


def _chg(c, unit):
    if c["abs"] is None:
        return "n/a"
    direction = "up" if c["abs"] > 0 else "down" if c["abs"] < 0 else "flat"
    if direction == "flat":
        return "no change"
    pct = f"{abs(c['pct']):.1f}%" if c["pct"] is not None else "n/a"
    if unit == "percent":
        return f"{direction} {abs(c['pp']):.1f} pts ({'+' if c['abs'] > 0 else '-'}{pct} relative)"
    return f"{direction} {pct} ({'+' if c['abs'] > 0 else '-'}{fmt(abs(c['abs']), unit)})"


def _audit(entry: dict):
    try:
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"), **entry}) + "\n")
    except OSError:
        pass


# ───────────── responses ─────────────
def allowed_metrics(role: str) -> list:
    return [m for m in kpi.METRICS.values() if policy.check(role, kpi.required_columns(m.id))[0]]


def suggestions(role: str, n=4) -> list:
    return _spread([m.example for m in allowed_metrics(role)], n)


def _spread(items, n):
    if len(items) <= n:
        return items
    step = len(items) / n
    return [items[int(i * step)] for i in range(n)]


def _help(role):
    ms = allowed_metrics(role)
    names = ", ".join(m.label.lower() for m in ms)
    return {"kind": "help", "answer": f"With the {role} role you can ask about: {names}.\n\n"
            "You can ask for a single figure, compare periods (Q1 vs Q2, 2024 vs 2025) to get the increase or decrease, "
            "see a trend by month, quarter or year, or break a figure down by channel, category, country or loan status. "
            "Add 'chart' to any question to get a visual.", "suggestions": [m.example for m in ms][:4]}


def _denied(role, user, plan, denied, needed):
    metric = kpi.METRICS[plan["metric"]]
    tags = sorted({t for d in denied for t in d["missing"]})
    others = [r for r in policy.roles_with_access(needed, among=user["roles"]) if r != role]
    msg = (f"I can't answer that as {role}. {metric.label} draws on {' and '.join(tags)} data, "
           f"and the {role} role isn't cleared for it.")
    if others:
        msg += f" Your {' / '.join(others)} role can; switch roles to ask it."
    else:
        holders = policy.roles_with_access(needed)
        msg += f" Roles with access: {', '.join(holders) if holders else 'none'}."
    return {"kind": "denied", "answer": msg, "denied": [{"column": d["column"], "tags": d["tags"], "missing": d["missing"]} for d in denied]}


def _narrate(res, plan, unit):
    label, op = res["label"], res["operation"]
    rows = res["rows"]
    if op == "list":
        return f"Here are {len(res['table'])} customer contact records."
    if op == "value":
        r = rows[0]
        return f"{label} ({r['label']}): {fmt(r['value'], unit)}."
    if op == "compare":
        parts = " → ".join(f"{r['label']} {fmt(r['value'], unit)}" for r in rows)
        lines = [f"{label}: {parts}."]
        for c in res["changes"]:
            lines.append(f"{c['from']} to {c['to']}: {_chg(c, unit)}.")
        if "overall" in res:
            lines.append(f"Overall, {res['overall']['from']} to {res['overall']['to']}: {_chg(res['overall'], unit)}.")
        return "\n".join(lines)
    if op == "trend":
        valid = [r for r in rows if r["value"] is not None]
        lines = [f"{label} by period, {rows[0]['label']} to {rows[-1]['label']}."]
        if valid:
            hi, lo = max(valid, key=lambda r: r["value"]), min(valid, key=lambda r: r["value"])
            lines.append(f"Highest: {hi['label']} ({fmt(hi['value'], unit)}). Lowest: {lo['label']} ({fmt(lo['value'], unit)}).")
        ov = res.get("overall") or (res["changes"][0] if res["changes"] else None)
        if ov:
            lines.append(f"First to last period: {_chg(ov, unit)}.")
        return "\n".join(lines)
    if op == "breakdown":
        top = rows[0] if rows else None
        s = f"{label} by {res['group_by'].replace('_', ' ')} ({res['period_label']})."
        return s + (f" Highest: {top['label']} at {fmt(top['value'], unit)}." if top else "")
    return label


def _table(res, unit):
    if res["operation"] == "list":
        df = res["table"]
        return {"columns": list(df.columns), "rows": df.astype(str).values.tolist()}
    rows, ch = res["rows"], res["changes"]
    if res["operation"] == "breakdown":
        return {"columns": [res["group_by"].replace("_", " ").title(), res["label"]],
                "rows": [[r["label"], fmt(r["value"], unit)] for r in rows]}
    out = []
    for i, r in enumerate(rows):
        out.append([r["label"], fmt(r["value"], unit), "" if i == 0 else (_chg(ch[i - 1], unit) if i - 1 < len(ch) else "")])
    return {"columns": ["Period", res["label"], "Change vs previous"], "rows": out}


def _chart(res, unit, plan):
    rows = [r for r in res["rows"] if r["value"] is not None]
    if res["operation"] in ("list", "value") or len(rows) < 2:
        return None
    scale = 100 if unit == "percent" else 1
    sub = f" by {res['group_by'].replace('_', ' ')}" if res["operation"] == "breakdown" else ""
    return {"type": "bar", "title": res["label"] + sub, "unit": unit,
            "labels": [r["label"] for r in rows], "values": [r["value"] * scale for r in rows],
            "valueLabels": [fmt(r["value"], unit) for r in rows]}


def ask(question: str, user: dict, role: str) -> dict:
    plan, engine = planner.make_plan(question)
    base = {"role": role, "planner": engine, "plan": plan}
    if plan.get("intent") == "help":
        return {**base, **_help(role)}
    if plan.get("intent") != "query":
        return {**base, "kind": "unknown", "suggestions": suggestions(role),
                "answer": "I can answer questions about your fintech data: figures, period comparisons with percentage change, trends and breakdowns. "
                          "Try one of the examples below."}
    needed = kpi.required_columns(plan["metric"], plan.get("group_by"), plan.get("periods"))
    ok, denied = policy.check(role, needed)
    _audit({"user": user["id"], "role": role, "question": question, "metric": plan["metric"], "allowed": ok,
            "denied_columns": [d["column"] for d in denied], "planner": engine})
    if not ok:
        return {**base, **_denied(role, user, plan, denied, needed)}
    res = kpi.run(plan["metric"], plan["operation"], plan["periods"], plan.get("granularity"), plan.get("group_by"))
    unit = res["unit"]
    text = _narrate(res, plan, unit)
    if plan.get("notes"):
        text += "\n\n" + " ".join(plan["notes"])
    return {**base, "kind": "answer", "answer": text, "table": _table(res, unit),
            "chart": _chart(res, unit, plan)}
