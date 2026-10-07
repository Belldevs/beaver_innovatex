"""Beaver KPI engine (fintech). Replaces the old insurance-only version.
All numbers are computed here with pandas, never by the LLM."""
import re
from dataclasses import dataclass, field
from typing import Callable, Optional
import pandas as pd
import datastore

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ───────────────────────── periods ─────────────────────────
def normalize_period(spec: str, a: dict, notes: list) -> list:
    """Turns loose period text into canonical specs: 'ALL', '2025', '2025-Q1', '2025-H2', '2025-03'."""
    s = str(spec).strip().upper().replace("_", "-").replace(" ", "-")
    lfy, ly = a["latest_full_year"], a["latest_year"]
    if s in ("ALL", "ALL-TIME", "OVERALL", "ANY"):
        return ["ALL"]
    if s in ("LAST-YEAR", "PREVIOUS-YEAR"):
        return [str(lfy)]
    if s in ("THIS-YEAR", "CURRENT-YEAR"):
        return [str(ly)]
    if s in ("LAST-2-YEARS", "LAST-TWO-YEARS", "PAST-2-YEARS", "PAST-TWO-YEARS"):
        return [str(lfy - 1), str(lfy)]
    if re.fullmatch(r"\d{4}", s):
        return [s]
    m = re.fullmatch(r"(\d{4})-?([QH])([1-4])", s) or None
    if m:
        return [f"{m.group(1)}-{m.group(2)}{m.group(3)}"]
    m = re.fullmatch(r"([QH])([1-4])-?(\d{4})", s)
    if m:
        return [f"{m.group(3)}-{m.group(1)}{m.group(2)}"]
    m = re.fullmatch(r"([QH])([1-4])", s)
    if m:
        notes.append(f"No year given for {m.group(1)}{m.group(2)}, so I used {lfy} (the latest full year in the data).")
        return [f"{lfy}-{m.group(1)}{m.group(2)}"]
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", s)
    if m and 1 <= int(m.group(2)) <= 12:
        return [f"{m.group(1)}-{int(m.group(2)):02d}"]
    raise ValueError(f"Unrecognised period: {spec}")


def resolve_period(spec: str) -> dict:
    if spec == "ALL":
        return {"spec": "ALL", "label": "All time", "start": None, "end": None}
    if re.fullmatch(r"\d{4}", spec):
        y = int(spec)
        return {"spec": spec, "label": spec, "start": pd.Timestamp(y, 1, 1), "end": pd.Timestamp(y + 1, 1, 1)}
    m = re.fullmatch(r"(\d{4})-Q([1-4])", spec)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        s = pd.Timestamp(y, 3 * (q - 1) + 1, 1)
        return {"spec": spec, "label": f"{y} Q{q}", "start": s, "end": s + pd.DateOffset(months=3)}
    m = re.fullmatch(r"(\d{4})-H([12])", spec)
    if m:
        y, h = int(m.group(1)), int(m.group(2))
        s = pd.Timestamp(y, 6 * (h - 1) + 1, 1)
        return {"spec": spec, "label": f"{y} H{h}", "start": s, "end": s + pd.DateOffset(months=6)}
    m = re.fullmatch(r"(\d{4})-(\d{2})", spec)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        s = pd.Timestamp(y, mo, 1)
        return {"spec": spec, "label": f"{MONTHS[mo - 1]} {y}", "start": s, "end": s + pd.DateOffset(months=1)}
    raise ValueError(f"Unrecognised period: {spec}")


def subperiods(spec: str, granularity: Optional[str], a: dict) -> list:
    p = resolve_period(spec)
    start = p["start"] or a["earliest_date"].normalize().replace(day=1)
    end = p["end"] or (a["latest_date"].normalize() + pd.Timedelta(days=1))
    if granularity not in ("month", "quarter", "year"):
        granularity = ("quarter" if re.fullmatch(r"\d{4}", spec) else
                       "year" if spec == "ALL" and (end - start).days > 366 else "month")
    out, cur = [], start
    if granularity == "quarter":
        cur = pd.Timestamp(cur.year, 3 * ((cur.month - 1) // 3) + 1, 1)
    elif granularity == "year":
        cur = pd.Timestamp(cur.year, 1, 1)
    while cur < end:
        if granularity == "year":
            out.append(str(cur.year)); cur += pd.DateOffset(years=1)
        elif granularity == "quarter":
            out.append(f"{cur.year}-Q{(cur.month - 1) // 3 + 1}"); cur += pd.DateOffset(months=3)
        else:
            out.append(f"{cur.year}-{cur.month:02d}"); cur += pd.DateOffset(months=1)
    return out


def _slice(df, date_col, spec):
    p = resolve_period(spec)
    if p["start"] is None:
        return df
    return df[(df[date_col] >= p["start"]) & (df[date_col] < p["end"])]


# ───────────────────────── metrics ─────────────────────────
def _num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if x != x else x


def _ratio(n, d):
    return _num(n / d) if d else None


@dataclass
class Metric:
    id: str
    label: str
    unit: str            # currency | percent | count | score | list
    table: str
    columns: list
    fn: Callable
    desc: str
    synonyms: list
    example: str
    kind: str = "scalar"  # scalar | list


METRICS = {m.id: m for m in [
    Metric("net_profit", "Net profit", "currency", "pnl",
           ["fee_revenue", "interest_income", "operating_expense", "loan_loss_provision"],
           lambda d: _num((d.fee_revenue + d.interest_income - d.operating_expense - d.loan_loss_provision).sum()),
           "fee revenue + interest income - operating expense - loan-loss provision",
           ["net profit", "profit", "earnings", "bottom line"],
           "What was our net profit in Q1 vs Q2?"),
    Metric("total_revenue", "Total revenue", "currency", "pnl", ["fee_revenue", "interest_income"],
           lambda d: _num((d.fee_revenue + d.interest_income).sum()),
           "fee revenue + interest income", ["total revenue", "revenue", "income"],
           "Show revenue by quarter for 2025."),
    Metric("total_expenses", "Total expenses", "currency", "pnl", ["operating_expense", "loan_loss_provision"],
           lambda d: _num((d.operating_expense + d.loan_loss_provision).sum()),
           "operating expense + loan-loss provision", ["total expenses", "expenses", "operating costs", "costs", "opex"],
           "How did expenses change from 2024 to 2025?"),
    Metric("profit_margin", "Profit margin", "percent", "pnl",
           ["fee_revenue", "interest_income", "operating_expense", "loan_loss_provision"],
           lambda d: _ratio((d.fee_revenue + d.interest_income - d.operating_expense - d.loan_loss_provision).sum(),
                            (d.fee_revenue + d.interest_income).sum()),
           "net profit / total revenue", ["profit margin", "net margin", "margin"],
           "What is the profit margin for each quarter of 2025?"),
    Metric("transaction_volume", "Transaction volume", "currency", "transactions", ["amount", "status"],
           lambda d: _num(d.loc[d.status == "success", "amount"].sum()),
           "sum of successful transaction amounts", ["transaction volume", "payment volume", "volume", "tpv", "processed"],
           "Compare transaction volume across the last two years."),
    Metric("transaction_count", "Transactions", "count", "transactions", ["txn_id"],
           lambda d: _num(len(d)), "number of transactions",
           ["number of transactions", "transaction count", "how many transactions", "transactions"],
           "How many transactions did we process in 2025?"),
    Metric("avg_transaction_value", "Average transaction value", "currency", "transactions", ["amount", "status"],
           lambda d: _num(d.loc[d.status == "success", "amount"].mean()),
           "mean successful transaction amount",
           ["average transaction", "avg transaction", "ticket size", "average ticket", "transaction value"],
           "What is the average transaction value by channel?"),
    Metric("failed_txn_rate", "Failed transaction rate", "percent", "transactions", ["status"],
           lambda d: _num((d.status == "failed").mean()) if len(d) else None,
           "share of transactions that failed",
           ["failed transaction", "failure rate", "decline rate", "failed payments"],
           "What is the failed transaction rate by country?"),
    Metric("fraud_rate", "Fraud rate", "percent", "transactions", ["is_fraud"],
           lambda d: _num(d.is_fraud.mean()) if len(d) else None,
           "share of transactions flagged as fraud", ["fraud rate", "fraud", "fraudulent"],
           "How did the fraud rate change between 2024 and 2025?"),
    Metric("loans_disbursed", "Loans disbursed", "currency", "loans", ["principal"],
           lambda d: _num(d.principal.sum()), "total principal of loans issued",
           ["loans disbursed", "disbursed", "disbursement", "total lending", "loan book"],
           "How much did we disburse each quarter of 2025?"),
    Metric("loan_count", "Loans issued", "count", "loans", ["loan_id"],
           lambda d: _num(len(d)), "number of loans issued",
           ["number of loans", "loan count", "loans issued", "how many loans"],
           "How many loans were issued in 2025?"),
    Metric("avg_loan_size", "Average loan size", "currency", "loans", ["principal"],
           lambda d: _num(d.principal.mean()), "mean loan principal",
           ["average loan", "avg loan", "loan size"], "What is the average loan size per year?"),
    Metric("loan_repayment_rate", "Loan repayment rate", "percent", "loans", ["amount_repaid", "amount_due"],
           lambda d: _ratio(d.amount_repaid.sum(), d.amount_due.sum()),
           "amount repaid / amount due, for loans issued in the period",
           ["repayment rate", "loan repayment", "repayment", "repaid"],
           "Generate a chart of the loan repayment rate comparing the last two years."),
    Metric("default_rate", "Default rate", "percent", "loans", ["status"],
           lambda d: _num((d.status == "default").mean()) if len(d) else None,
           "share of loans in default", ["default rate", "defaults", "loan default", "defaulted"],
           "What is the loan default rate for 2025?"),
    Metric("avg_credit_score", "Average credit score", "score", "loans", ["credit_score"],
           lambda d: _num(d.credit_score.mean()), "mean borrower credit score",
           ["credit score", "average score"], "What is the average credit score of borrowers by year?"),
    Metric("customer_contacts", "Customer contacts", "list", "loans", ["customer_name", "email"],
           lambda d: d[["customer_name", "email"]].drop_duplicates("email").head(10),
           "customer names and emails (first 10)",
           ["customer contacts", "contact details", "customer emails", "customer list", "customer names", "email addresses"],
           "Show me some customer contact details.", kind="list"),
]}


def match_metric(text: str) -> Optional[str]:
    """Longest-synonym match, used by the offline rule-based planner."""
    t = text.lower()
    best, best_len = None, 0
    for m in METRICS.values():
        for s in m.synonyms:
            if s in t and len(s) > best_len:
                best, best_len = m.id, len(s)
    return best


def required_columns(metric_id: str, group_by: Optional[str] = None, periods: Optional[list] = None) -> set:
    """Every (table, column) the answer will touch. The date column only counts if a period filter is applied."""
    m = METRICS[metric_id]
    meta = datastore.schema()[m.table]
    need = {(m.table, c) for c in m.columns}
    if m.kind != "list" or (periods and periods != ["ALL"]):
        need.add((m.table, meta["date_column"]))
    if group_by:
        need.add((m.table, group_by))
    return need


# ───────────────────────── calculation ─────────────────────────
def _changes(rows, unit):
    out = []
    for prev, cur in zip(rows, rows[1:]):
        a, b = prev["value"], cur["value"]
        if a is None or b is None:
            out.append({"from": prev["label"], "to": cur["label"], "abs": None, "pct": None, "pp": None})
            continue
        out.append({"from": prev["label"], "to": cur["label"], "abs": b - a,
                    "pct": ((b - a) / abs(a) * 100) if a else None,
                    "pp": (b - a) * 100 if unit == "percent" else None})
    return out


def run(metric_id: str, operation: str, periods: list, granularity: Optional[str], group_by: Optional[str]) -> dict:
    m = METRICS[metric_id]
    a = datastore.anchor()
    df = datastore.table(m.table)
    date_col = datastore.schema()[m.table]["date_column"]
    res = {"metric": m.id, "label": m.label, "unit": m.unit, "operation": operation, "rows": [], "changes": []}

    if m.kind == "list":
        sl = _slice(df, date_col, periods[0]) if periods else df
        res["table"] = m.fn(sl)
        res["operation"] = "list"
        return res

    if operation == "breakdown" and group_by:
        sl = _slice(df, date_col, periods[0] if periods else "ALL")
        rows = [{"label": str(k), "value": m.fn(g)} for k, g in sl.groupby(group_by)]
        rows.sort(key=lambda r: (r["value"] is None, -(r["value"] or 0)))
        res["rows"], res["period_label"], res["group_by"] = rows[:12], resolve_period(periods[0] if periods else "ALL")["label"], group_by
        return res

    if operation == "trend":
        specs = subperiods(periods[0] if periods else "ALL", granularity, a)
    else:  # value / compare
        specs = periods or ["ALL"]
    for s in specs:
        p = resolve_period(s)
        res["rows"].append({"label": p["label"], "value": m.fn(_slice(df, date_col, s))})
    res["changes"] = _changes(res["rows"], m.unit)
    if len(res["rows"]) > 2:
        res["overall"] = _changes([res["rows"][0], res["rows"][-1]], m.unit)[0]
    return res
