# A three-minute recruiter walkthrough

1. Open the public demo and click Load synthetic example, then Run reconciliation.
2. Explain the clean Cedar Studio control record and five planted discrepancies. Do not call their sum recoverable savings.
3. Open Possible duplicate: reference NS-1001 versus NS-100I, equal amount, same normalized supplier, one-day gap. Explain false positives and why human review is required.
4. Add a synthetic investigation note, move open -> investigating, then record the outcome and resolve. Show the audit history. Explain that browser audit data is editable and that production needs authenticated roles and external immutable storage.
5. Open Overpayment: two payments total GBP 1,000 against an GBP 800 invoice. This finding is grounded in payment records, unlike a possible duplicate invoice.
6. In the repository, show queue tests for retry exhaustion, crash recovery and concurrent claims. Explain the 120-second lease and attempt fencing; the public browser demo does not run this queue.
7. Discuss the AWS design as an extension: ECS, RDS, S3 and SQS. Only the isolated SQS/DLQ Terraform module is implemented; no cloud deployment is claimed.

Suggested CV wording after you have run and understood the project:

"Built a synthetic AP reconciliation prototype with Python, transactional case auditing, durable job retries and an interactive public demo; tested duplicate matching, currency isolation and worker recovery."

Avoid claiming real customer savings, production scale, employer affiliation or infrastructure you have not deployed.
