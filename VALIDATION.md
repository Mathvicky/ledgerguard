# Validation — 15 October 2026

Executed locally on Windows / Python 3.13.15 / Node 24:

- Python suite: 12 tests passed. Covers planted discrepancies, a clean control, currency separation, duplicate-cluster cardinality, money/CSV validation, durable job completion, note/transition rules, audit history, worker retries/dead-letter state, crashed-worker recovery and concurrent claims.
- JavaScript suite: 6 tests, including full Python/JS parity for the synthetic scenario.
- Browser: local API mode loaded 12 records, completed a background job and displayed five cases. An investigation update persisted the note and open -> investigating audit event through the API.
- Engine-only benchmark: 3,000 clean records (1,000 supplier buckets), five runs: 85.743, 103.025, 92.288, 119.411, 84.423 ms; zero findings. Run `python scripts/benchmark.py` to reproduce. Not an HTTP load test, worst-case matching test or capacity guarantee.
- Docker build and Terraform provider validation not run locally; included CI jobs perform them. No AWS resources provisioned.

Limits: failure injection is exercised in unit tests, not a host-kill chaos test. No claim of measured production SLOs, restore RTO or shared-user security.
