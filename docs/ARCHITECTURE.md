# Architecture and deliberate boundaries

## Implemented

Local HTTP service -> validated CSV job -> SQLite durable queue -> worker -> reconciliation cases -> status changes + append-only application audit history.

Transactions claim one job at a time. A 120-second lease allows recovery after a worker crash; an attempt counter fences stale worker writes. Failed processing retries with exponential delay and stops after three attempts. Invalid CSV is rejected before enqueue. Case status changes and their audit entries commit together. SQLite uses WAL and a 15-second busy timeout. A single local service is the supported deployment, not a multi-node production cluster.

The browser demo reimplements the reconciliation rules for a setup-free public experience. It has no background queue, no shared database and no authenticated audit trail. It saves cases in localStorage on the visitor's device. The Python and JS suites exercise the same planted findings, but this is not a proof of full behavioral equivalence for every CSV dialect or Unicode input.

## Matching and money

Supplier keys ignore punctuation and case; they do not resolve legal entities, aliases or subsidiaries. Reference similarity is at most one insertion/deletion/substitution for references of four or more characters, and only within supplier/currency/amount buckets and a seven-day window. Transpositions are not a special case. Greedy clusters compare against their first record; this is a heuristic, not exhaustive entity resolution.

All calculations use integer minor units with two decimals. The demo assumes currencies with two decimal places, rejects credits/zero values, and does not convert FX. Different currencies never match. A possible duplicate is not an assertion of duplicate payment. Statement inputs represent original invoice values, not remaining balances. Case amounts can overlap; summing them would overstate recoverable value. No recovery total is displayed.

## Production target — not implemented

An AWS architecture could use private ECS API/worker services, RDS PostgreSQL, S3 for encrypted source files, and SQS/DLQ for distributed jobs. Keep upload keys and account identity scoped to a tenant; use an outbox to commit job intent and database updates reliably. Store large payloads in S3 and enqueue pointers, not whole CSVs. Scale workers on queue age and depth with an explicit concurrency limit protecting PostgreSQL connections.

`infra/queues.tf` provisions encrypted SQS queues and a DLQ count alarm only. The local worker does not consume SQS. ECS, RDS, S3, IAM workload policies, SNS paging, remote Terraform state and PostgreSQL adapters remain future work. The alarm has no notification action configured. No AWS resources were deployed. Do not describe this project as AWS production experience.

Production also needs authentication, tenant isolation, reviewer roles, dual approval, immutable external audit storage, encrypted secrets/backups, upload retention controls and a hardened HTTP server. The local API binds loopback; do not expose it publicly. Audit history in SQLite or browser storage is editable by the database/device owner and is not tamper-proof.

Provider reference: https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sqs_queue
