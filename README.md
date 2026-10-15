# LedgerGuard — AP Reconciliation & Recovery

An independent financial-controls portfolio project inspired by Accounts Payable operations. Not affiliated with Xelix. Synthetic data only.

## Live recruiter demo

[Open LedgerGuard](https://mathvicky.github.io/ledgerguard/) — click **Load synthetic example**, then **Run reconciliation**, then **Investigate** on a finding. This hosted version uses browser-local processing and storage.

## Start locally

Python 3.13, no pip packages required:

```powershell
python -m ledgerguard.server
```

Open http://localhost:8091/ and click **Load synthetic example**, then **Run reconciliation**. The local API queues a durable job, processes it in a background worker, and stores cases and investigation notes in SQLite. Use **Investigate** to move a case from open to investigating, then resolved or dismissed. A note is required for every change. Resolved means manually closed, not money recovered.

Docker alternative: `docker compose up --build` (persistent named volume).

## Demonstration scenario

Twelve records contain five planted findings:

| Finding | Evidence | Value to review |
|---|---|---:|
| Near-duplicate reference | INV-1 / INV-2 | GBP 1,200.00 |
| Unmatched payment | PAY-3 | GBP 950.00 |
| Missing invoice | ST-2 | GBP 425.00 |
| Overpayment | INV-3 / PAY-1 / PAY-2 | GBP 200.00 |
| Statement difference | INV-4 / ST-1 | GBP 50.00 |

The Cedar Studio control record reconciles cleanly. Case values may overlap; they are not a savings total.

## What makes this an engineering project

- CSV schema, amount, date, identifier and record-limit validation.
- Currency-isolated matching, bounded reference similarity and integer monetary arithmetic.
- Durable queued/running/complete/dead job states, three-attempt backoff, lease recovery and stale-worker fencing.
- Transactional case transitions with investigation notes and audit history.
- Python backend and standalone JS browser demo, with separate automated suites.
- Non-root Docker packaging, CI and a Terraform SQS/DLQ module for the proposed AWS extension.

## Browser demo

Serve `web/` with `python -m http.server 8092 --directory web`. The page falls back to a browser-only engine if `/health` is unavailable. Browser data is stored on the current device, not in the Python database. The public demo uses this mode. Download sample CSVs, upload/edit datasets, filter cases and export JSON findings. Running a new analysis creates a fresh case set.

CSV headers must be exactly `id,vendor,reference,amount,currency,date`. All fields are required. Currency is three uppercase letters and assumes two decimal places; dates use YYYY-MM-DD. Amounts must be positive, <= one billion and at most two decimal places. Maximum 2,000 rows per dataset and 2 MB request payload. No real invoices or payment actions.

## Checks

```powershell
python -m unittest discover -s tests -v
node --test tests/engine.test.cjs
```

See [VALIDATION.md](VALIDATION.md) for executed checks and measured performance. [Architecture](docs/ARCHITECTURE.md) separates implemented behavior from the proposed AWS production design. [Runbook](docs/RUNBOOK.md) covers job failures and database recovery.

This is not a production financial system: no authentication, tenant separation, immutable audit, trained ML model or production cloud deployment. The standard-library HTTP server is for local use. EKS and production PostgreSQL are not implemented.
