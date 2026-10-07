"""Generates a synthetic fintech dataset (transactions, loans, monthly P&L) into ./data.
Run once:  python generate_sample_data.py
Swap in your real tables later: keep the same filenames/columns, or edit data/schema_tags.json."""
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

FIRST = ["Alex", "Jordan", "Sam", "Casey", "Taylor", "Riley", "Morgan", "Jamie", "Avery", "Quinn", "Drew", "Reese"]
LAST = ["Smith", "Chen", "Patel", "Garcia", "Muller", "Novak", "Silva", "Khan", "Ivanov", "Lopez", "Brown", "Tan"]
N_CUST = 400
cust = pd.DataFrame({
    "customer_id": [f"C{1000 + i}" for i in range(N_CUST)],
    "customer_name": [f"{rng.choice(FIRST)} {rng.choice(LAST)}" for _ in range(N_CUST)],
})
cust["email"] = [f"{n.lower().replace(' ', '.')}{i}@example.com" for i, n in enumerate(cust.customer_name)]
cust["national_id"] = [f"ID{rng.integers(10**8, 10**9)}" for _ in range(N_CUST)]

# ---- transactions: 2024-01 .. 2025-12
n_txn = 14000
days = pd.date_range("2024-01-01", "2025-12-31")
w = np.linspace(0.8, 1.35, len(days))  # volume grows over time
txn_dates = rng.choice(days, n_txn, p=w / w.sum())
txn = pd.DataFrame({
    "txn_id": [f"T{100000 + i}" for i in range(n_txn)],
    "txn_date": pd.to_datetime(txn_dates),
    "customer_id": rng.choice(cust.customer_id, n_txn),
    "channel": rng.choice(["card", "bank_transfer", "wallet", "qr"], n_txn, p=[.38, .27, .25, .10]),
    "merchant_category": rng.choice(["retail", "food", "transport", "utilities", "entertainment", "travel"], n_txn),
    "country": rng.choice(["US", "UK", "DE", "SG"], n_txn, p=[.45, .25, .2, .1]),
    "amount": np.round(rng.lognormal(4.2, 0.9, n_txn), 2),
})
txn["status"] = rng.choice(["success", "failed", "pending"], n_txn, p=[.93, .05, .02])
fraud_p = np.where(txn.txn_date.dt.year == 2024, 0.008, 0.005)
txn["is_fraud"] = (rng.random(n_txn) < fraud_p).astype(int)
txn.to_csv(OUT / "transactions.csv", index=False)

# ---- loans: issued across 2024-2025; repayment a little weaker in 2025
n_loan = 1500
issue = pd.to_datetime(rng.choice(days, n_loan))
snapshot = pd.Timestamp("2025-12-31")
months_elapsed = np.clip(np.asarray((snapshot - issue).days) / 30.0, 0, None)
principal = np.round(rng.uniform(500, 20000, n_loan), -1)
rate = np.round(rng.uniform(8, 24, n_loan), 1)
due = principal * (1 + rate / 100) * np.minimum(1, months_elapsed / 12)
base = np.where(np.asarray(issue.year) == 2024, 0.94, 0.89)
ratio = np.clip(rng.beta(base * 18, (1 - base) * 18), 0, 1)
repaid = np.round(due * ratio, 2)
loans = pd.DataFrame({
    "loan_id": [f"L{5000 + i}" for i in range(n_loan)],
    "customer_id": rng.choice(cust.customer_id, n_loan),
    "issue_date": issue,
    "principal": principal,
    "interest_rate": rate,
    "amount_due": np.round(due, 2),
    "amount_repaid": repaid,
    "status": np.where(ratio < 0.55, "default", "active"),
    "credit_score": np.clip(rng.normal(660, 60, n_loan), 450, 850).round(),
})
loans = loans.merge(cust, on="customer_id")[[
    "loan_id", "customer_id", "customer_name", "email", "national_id", "issue_date",
    "principal", "interest_rate", "amount_due", "amount_repaid", "status", "credit_score"]]
loans.to_csv(OUT / "loans.csv", index=False)

# ---- monthly P&L
months = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
t = np.arange(len(months))
fee = 118000 * (1.018 ** t) * rng.normal(1, .03, len(months))
interest = 86000 * (1.022 ** t) * rng.normal(1, .03, len(months))
opex = 150000 * (1.009 ** t) * rng.normal(1, .02, len(months))
prov = interest * rng.uniform(.05, .09, len(months))
pnl = pd.DataFrame({"month": months, "fee_revenue": fee.round(2), "interest_income": interest.round(2),
                    "operating_expense": opex.round(2), "loan_loss_provision": prov.round(2)})
pnl.to_csv(OUT / "pnl.csv", index=False)
print("wrote", [p.name for p in OUT.glob("*.csv")])
