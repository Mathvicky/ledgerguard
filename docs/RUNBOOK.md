# Operational runbook

## Worker backlog

Inspect job state and attempt count through GET /api/jobs/JOB_ID. A queued job may be waiting for exponential backoff. The embedded worker checks every 0.5 seconds. Check service logs and filesystem capacity before restarting. Running jobs with expired leases return to the queue; attempt three moves to dead. Do not manually replay non-idempotent financial actions: this project only computes cases and never initiates payments.

## Failed jobs

The demo masks exception details from API clients. Reproduce with the same synthetic CSV in a test environment and inspect worker behavior. A dead job is retained for investigation. There is no replay endpoint; resubmit a corrected dataset as a new job and retain the failed job ID in the investigation record. A replay can create new cases; there is no global upload deduplication.

## Database recovery

For a consistent local backup use Python sqlite3.Connection.backup while the service runs, or stop it cleanly before copying the database and WAL files. Restore into a separate directory and verify job counts, case states, notes and a synthetic reconciliation before switching files. Define and test RPO/RTO before relying on any backup. No restore-time SLA is claimed.

## Delivery and cost

CI runs Python/Node tests and a Docker build. Test a release locally with the synthetic example, including a retry failure and a case transition. Terraform is a small isolated future queue module, not an automatic deploy pipeline. Validate and review a cost-bearing plan before applying; configure secure remote state and provider lockfiles for team use.

Suggested future telemetry: request latency/errors, queue depth/age, worker attempts and dead count, processing latency, database lock waits and disk headroom. These metrics and on-call paging are design recommendations, not implemented dashboards.
