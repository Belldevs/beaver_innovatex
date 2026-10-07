# Beaver

Chat with your fintech data. Role-based, tag-driven access, calculations done in code, language understood by a local LLM (Ollama), so it works offline.

## Run it
1. **Ollama (once):** install from ollama.com, then `ollama pull llama3.1:8b` and keep `ollama serve` running.
   Without Ollama, Beaver falls back to a built-in rule parser (status pill in the top bar shows which is active).
   Use another model with `BEAVER_MODEL=qwen2.5:7b` (env var).
2. **Backend:** `cd analytics`, activate your venv, `uvicorn main:app --port 5000`
   (needs: fastapi uvicorn pandas numpy requests python-multipart).
   Sample data is in `analytics/data/`; regenerate with `python generate_sample_data.py`.
3. **Frontend:** `cd frontend`, `npm install`, `npm run dev`, open http://localhost:5173

## How access works
- `analytics/data/schema_tags.json`: every column has tags (e.g. `pii`, `risk`, `financials`).
- `analytics/roles.json`: each role lists the tags it may read (`*` = everything = admin) and users hold roles.
- A question becomes a plan (metric, periods, grouping). The plan's columns are checked against the active role's tags **before** any data is touched. Denied questions explain which tag blocked them.
- Every question and its allow/deny result is appended to `analytics/audit.log`.

## Try it
Alex Morgan (admin): "generate a datagram of the loan repayment rate comparing the last two years"
Alex Morgan (admin): "net profit in the first quarter vs the second quarter"
Switch to Jordan Lee (finance): "fraud rate in 2025" is denied (tag `risk`).
Casey Kim (support): "show me customer emails" works; "net profit" is denied.

## Using your own data
Drop your CSVs in `analytics/data/`, edit `schema_tags.json` (tables, date column, tags), and edit the metric
definitions in `analytics/kpi_engine.py` to match your column names.
