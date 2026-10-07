"""Turns a question into a structured plan: {intent, metric, operation, periods, granularity, group_by, chart}.
1) Ollama (local LLM, works offline) tries first.  2) A rule-based planner is the fallback.
The plan is only a REQUEST: access control and all maths happen afterwards in code."""
import json
import os
import re
import requests
import datastore
import kpi_engine as kpi

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = os.getenv("BEAVER_MODEL", "llama3.1:8b")
OPERATIONS = {"value", "compare", "trend", "breakdown"}
CHART_WORDS = ("chart", "graph", "datagram", "diagram", "plot", "visual", "bar")


def ollama_status() -> dict:
    try:
        tags = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2).json()
        names = [m["name"] for m in tags.get("models", [])]
        has = any(n == MODEL or n.split(":")[0] == MODEL.split(":")[0] for n in names)
        return {"online": True, "model": MODEL, "model_ready": has, "available": names}
    except Exception:
        return {"online": False, "model": MODEL, "model_ready": False, "available": []}


# ───────────── Ollama planner ─────────────
def _system_prompt(a: dict) -> str:
    catalog = "\n".join(f"- {m.id}: {m.desc} (table {m.table})" for m in kpi.METRICS.values())
    dims = "\n".join(f"- {t}: {', '.join(m['dimensions']) or 'none'}" for t, m in datastore.schema().items())
    return f"""You convert a user's question about a fintech dataset into ONE JSON object. Output JSON only.

Metrics:
{catalog}

Group-by columns per table:
{dims}

JSON schema:
{{"intent": "query" | "help" | "unknown",
  "metric": <metric id or null>,
  "operation": "value" | "compare" | "trend" | "breakdown",
  "periods": [<period strings>],
  "granularity": "month" | "quarter" | "year" | null,
  "group_by": <column or null>,
  "chart": true | false}}

Period strings: "2025", "2025-Q1", "2025-H2", "2025-03", "Q1" (year unknown), "last_year", "last_2_years", "all".
- "compare": 2+ periods, used for increase/decrease/percentage change/vs/comparing.
- "trend": ONE period plus a granularity (e.g. each quarter of 2025 -> periods ["2025"], granularity "quarter").
- "breakdown": ONE period plus group_by.
- "value": a single number for one period (use ["all"] when no period is mentioned).
- chart is true when the user asks for a chart, graph, diagram, datagram or plot.
- intent "help" if they ask what they can ask; "unknown" if unrelated to the metrics.
Latest full year in the data is {a['latest_full_year']}.

Examples:
Q: net profit in the first quarter vs the second quarter -> {{"intent":"query","metric":"net_profit","operation":"compare","periods":["Q1","Q2"],"granularity":null,"group_by":null,"chart":false}}
Q: generate a datagram of loan repayment rate for the last two years -> {{"intent":"query","metric":"loan_repayment_rate","operation":"compare","periods":["last_2_years"],"granularity":null,"group_by":null,"chart":true}}
Q: transaction volume by channel in 2025 -> {{"intent":"query","metric":"transaction_volume","operation":"breakdown","periods":["2025"],"granularity":null,"group_by":"channel","chart":false}}"""


def plan_with_ollama(question: str, a: dict):
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", timeout=60, json={
            "model": MODEL, "stream": False, "format": "json", "options": {"temperature": 0},
            "messages": [{"role": "system", "content": _system_prompt(a)}, {"role": "user", "content": question}]})
        r.raise_for_status()
        return json.loads(r.json()["message"]["content"])
    except Exception:
        return None


# ───────────── rule-based fallback ─────────────
_WORD_Q = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4}
_MONTHS = {m.lower(): i + 1 for i, m in enumerate(kpi.MONTHS)}
_MONTHS.update({"june": 6, "july": 7, "sept": 9, "september": 9, "march": 3, "april": 4,
                "january": 1, "february": 2, "august": 8, "october": 10, "november": 11, "december": 12})


def plan_with_rules(question: str, a: dict) -> dict:
    q = question.lower()
    lfy = a["latest_full_year"]
    plan = {"intent": "query", "metric": kpi.match_metric(q), "operation": "value", "periods": [],
            "granularity": None, "group_by": None, "chart": any(w in q for w in CHART_WORDS)}
    if re.search(r"\b(what can i|what can you|help|what do you do|capabilit)", q) and not plan["metric"]:
        return {**plan, "intent": "help"}
    if not plan["metric"]:
        return {**plan, "intent": "unknown"}

    years = [y for y in re.findall(r"\b(20\d{2})\b", q)]
    quarters = [int(x) for x in re.findall(r"\bq([1-4])\b", q)]
    quarters += [n for w, n in _WORD_Q.items() if re.search(rf"\b{w}\s+quarter\b", q)]
    quarters = list(dict.fromkeys(quarters))
    halves = [int(x) for x in re.findall(r"\bh([12])\b", q)]
    months = [n for w, n in _MONTHS.items() if re.search(rf"\b{w}\b", q)]
    months = list(dict.fromkeys(months))

    if re.search(r"last (two|2) years|past (two|2) years", q):
        years = [str(lfy - 1), str(lfy)]
    elif "last year" in q and not years:
        years = [str(lfy)]
    elif "this year" in q and not years:
        years = [str(a["latest_year"])]
    ys = years or [str(lfy)]
    if not years and (quarters or halves or months):
        plan["assumed_year"] = lfy

    specs = []
    if quarters:
        specs = [f"{y}-Q{n}" for y in ys for n in quarters]
    elif halves:
        specs = [f"{y}-H{n}" for y in ys for n in halves]
    elif months:
        specs = [f"{y}-{n:02d}" for y in ys for n in months]
    elif years:
        specs = list(dict.fromkeys(years))
    plan["periods"] = specs or ["all"]

    compare_cue = re.search(r"\b(compare|comparing|comparison|versus|vs\.?|change|changed|increase|decrease|growth|grew|"
                            r"drop|dropped|fell|rose|rise|difference|percentage)\b", q)
    trend_cue = re.search(r"\b(trend|over time|monthly|quarterly|yearly|each (month|quarter|year)|per (month|quarter|year)|by (month|quarter|year))\b", q)
    dim = next((d for t in datastore.schema().values() for d in t["dimensions"]
                if re.search(rf"\bby {d.replace('_', ' ')}\b|\bper {d.replace('_', ' ')}\b|\bby {d}\b", q)), None)

    if dim:
        plan.update(operation="breakdown", group_by=dim)
        plan["periods"] = plan["periods"][:1]
    elif trend_cue and len(plan["periods"]) <= 1:
        gran = "month" if re.search(r"month", q) else "year" if re.search(r"year", q) and not years else "quarter"
        plan.update(operation="trend", granularity=gran)
    elif len(plan["periods"]) >= 2 or (compare_cue and plan["periods"] != ["all"]):
        plan["operation"] = "compare"
        if len(plan["periods"]) == 1:  # "how did X change in 2025" -> compare with the previous period
            plan["periods"] = ["__previous__", plan["periods"][0]]
    return plan


# ───────────── validation ─────────────
def _previous(spec: str) -> str:
    import re as _re
    if _re.fullmatch(r"\d{4}", spec):
        return str(int(spec) - 1)
    m = _re.fullmatch(r"(\d{4})-([QH]\d)", spec)
    if m:
        return f"{int(m.group(1)) - 1}-{m.group(2)}"
    m = _re.fullmatch(r"(\d{4})-(\d{2})", spec)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return f"{y - 1}-12" if mo == 1 else f"{y}-{mo - 1:02d}"
    return spec


def validate(plan, a: dict):
    """Returns a clean plan or None if the LLM output is unusable."""
    if not isinstance(plan, dict):
        return None
    intent = plan.get("intent", "query")
    if intent in ("help", "unknown"):
        return {"intent": intent}
    mid = plan.get("metric")
    if mid not in kpi.METRICS:
        return None
    op = plan.get("operation", "value")
    if op not in OPERATIONS:
        op = "value"
    notes, periods = [], []
    if plan.get("assumed_year"):
        notes.append(f"No year given, so I used {plan['assumed_year']} (the latest full year in the data).")
    try:
        for p in (plan.get("periods") or ["all"]):
            if p == "__previous__":
                periods.append(p)
            else:
                periods.extend(kpi.normalize_period(p, a, notes))
    except ValueError:
        return None
    periods = [_previous(periods[i + 1]) if p == "__previous__" else p for i, p in enumerate(periods)]
    periods = list(dict.fromkeys(periods)) or ["ALL"]
    m = kpi.METRICS[mid]
    gb = plan.get("group_by")
    if gb not in datastore.schema()[m.table]["dimensions"]:
        gb = None
    if op == "breakdown" and not gb:
        op = "value"
    if op == "compare" and len(periods) < 2:
        periods = [_previous(periods[0]), periods[0]] if periods[0] != "ALL" else periods
        op = "compare" if len(periods) == 2 else "value"
    if op == "value" and len(periods) > 1:
        op = "compare"
    gran = plan.get("granularity") if plan.get("granularity") in ("month", "quarter", "year") else None
    return {"intent": "query", "metric": mid, "operation": op, "periods": periods, "granularity": gran,
            "group_by": gb, "chart": bool(plan.get("chart")), "notes": notes}


def make_plan(question: str):
    a = datastore.anchor()
    raw = plan_with_ollama(question, a)
    plan = validate(raw, a) if raw else None
    if plan:
        return plan, f"ollama:{MODEL}"
    return validate(plan_with_rules(question, a), a) or {"intent": "unknown"}, "rules"
