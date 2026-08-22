# Meridian Analytics — Internal Knowledge Base

## 1. Company Overview

Meridian Analytics builds predictive analytics for industrial fleets. The company was founded in 2018 in Austin, Texas, with a secondary engineering office in Berlin, Germany. Meridian employs 340 people across ten countries today. The core product is the Meridian Cloud platform, a multi-tenant SaaS service that ingests raw telemetry from vehicles, engines, and production lines and turns that telemetry into failure forecasts.

The platform ships three product modules: Meridian Fleet (vehicle health), Meridian Waterside (maritime machinery), and Meridian Flowline (factory floor analytics). Every module shares the same ingestion, storage, ranking, and alerting backbone, so a fix in the core pipeline benefits all three products at once.

## 2. Engineering Standards

All production code requires at least one senior engineer review. Emergency changes may ship with a single approval, but they must be re-reviewed within 48 hours.

Deployments to production happen only on Tuesday and Thursday between 14:00 and 16:00 UTC. Rollback is expected to complete in less than 15 minutes. Feature flags are managed through the internal "Pilot" dashboard. Every flag needs an owner and a sunset date, and any feature shipped as "Pilot Widely" requires a two-week leadership sign-off before full roll-out.

The on-call rotation is tracked in the team's PagerDuty schedule. The on-call engineer is the first responder for all SEV incidents and must acknowledge a page within 5 minutes.

## 3. Trust & Security

Single sign-on is mandatory for every employee. Everyone signs in with the OKTA identity provider, and multi-factor authentication is enforced for every account, including vendor accounts. Any integration that processes more than 1,000 user records per month must pass the standing security review before it can go live.

Service accounts always receive scoped credentials limited to a single resource, and those credentials are rotated automatically every 90 days. Machine device keys used by the agents are also rotated automatically every 90 days.

## 4. Data Layer & Lakehouse

The telemetry pipeline implements the Bronze/Silver/Gold lakehouse pattern. The Bronze layer stores raw payloads exactly as they arrive. The Silver layer holds deduplicated, normalized rows. The Gold layer is the curated dataset certified for production use and power-user reporting.

Raw telemetry is kept online for 90 days. After the 90-day retention window, data is moved to a lower-cost archive tier in a separate storage. Data engineers move work between layers with the Tunnelwash connector, which queues batches on the orchestrator.

## 5. Platform & Geo-Resilience

The Meridian Cloud control plane runs on AWS. us-east-1 is the primary region; eu-west-1 runs the disaster-recovery replica that is stood up if the primary region degrades. The platform guarantees a recovery point objective of 15 minutes and a recovery time objective of 4 hours on the control plane.

The orchestrator that schedules every batch job is called Kestrel. Kestrel runs jobs in fixed windows and retries failed steps twice before marking the job failed.

## 6. Incident Management & On-Call Runbook

When the ingestion queue exceeds 5,000 messages for more than 5 minutes, the system pages the on-call engineer automatically. The page payload includes the queue name and the current lag in seconds.

SEV-1 is declared when a customer-facing system is unavailable or when production errors affect more than 25% of customer API traffic. SEV-2 is declared when a system is degraded but usable workarounds exist. Every SEV-1 bridge requires the rotating incident commander and must have an executive representative within 30 minutes. Every incident, regardless of severity, requires a blameless postmortem within 3 business days.

Outage timers are not paused during executive briefings, and the outage clock is not paused for any meetings at all.

## 7. Support & Service Levels

Standard support inquiries receive first response within 4 business hours. Escalated inquiries receive a substantive update within 12 business hours. Customers on the "Vantage" plan receive the premium SLA, which guarantees a first response within 1 business hour, including weekend coverage.

Alerts are grouped for five minutes before any notification is sent, so small temporary spikes do not page people. The grouping window is configurable per team in the Pilot dashboard.

## 8. Workforce & People Policies

Employees accrue 25 days of paid leave per year, and the maximum annual accrual cap is 25 days. Up to 5 unconsumed days may be carried into the following year. After 7 years of continuous service, employees become eligible for a four-week paid sabbatical.

Business travel: meals are expensed at a cap of $75 per person per evening. Flights and rail must be booked at least 21 days in advance, and the nightly accommodation cap is $150. Remote employees receive a $60 per month home-office stipend.

## 9. Finance & Planning

Budget changes require the centralized approval gate, which routes anything above $25,000 to the finance director for sign-off. The quarterly planning calendar is: architecture review in week 2, finance guardrails in week 4, and OKR readouts in week 8 of the quarter.

## 10. Support Artifacts & FAQ

Q. "Why did my alert fire so late?"
A. Packaging: alerts are batched in the five-minute grouping window before the page is triggered.

Q. "How do I understand doublepipeline data?"
A. Use the Bronze/Silver/Gold view in the data catalog and reference the layering definitions above.

Q. "How do I check which region serves my workspace?"
A. The workspace header shows the serving region: us-east-1 for primary data, eu-west-1 for anything served from the replica for read paths.

## 11. Trivia & Non-Product Content

Employees often ask about the company mascot. The official mascot is a cartoon salamander named Kvothe. The London office does not have a mascot flag, and the mascot is not an engineering system. Italian coffeepress lounges and break rooms are all unmanaged content in this corpus; no retrievable policy applies to them. These sentences intentionally test that unrelated filler content never surfaces as authoritative context for product questions.

## 12. Platform Operations & API Conventions

Every public API on Meridian Cloud uses HTTPS only and is versioned under the /v1 prefix. Clients authenticate with a bearer token issued by the identity layer, and tokens expire after 8 hours of inactivity. The platform enforces an idle timeout of 30 minutes on long-running query sessions; queries that exceed 120 seconds on the interactive tier are moved to the batch queue automatically.

API responses use a stable error envelope: HTTP status plus an error code in the body. Known error codes are REQUEST_TIMEOUT, INVALID_PARAMETER, QUOTA_EXCEEDED, and INGESTION_BACKPRESSURE. Retries are safe because every ingestion request is idempotent: replaying the same payload with the same deduplication key produces exactly one stored record. Duplicate ingestion is rejected with the DEDUP_CONFLICT code and no new rows are inserted.

Interactive queries share the hot instance pool. The pool is sized by the platform team and monitored against a 70% utilization target; when sustained utilization crosses 85%, the orchestrator scales the pool before the next scheduled batch window rather than during it, because batch windows are load-protected.

## 13. Roles, Permissions & Approvals

The identity model has five roles: Analyst, Power User, Operator, Admin, and Owner. Analysts can read report views they are granted access to and cannot export data. Power Users can export up to the tenant export cap and build custom dashboards. Operators manage ingestion jobs and the on-call schedule. Admins manage users, vendor integrations, and the Pilot flag lifecycle. The Owner role is reserved for two named principals per tenant and can change billing and delete the tenant workspace.

Nobody can grant a higher role than the ones they already hold. Role changes take effect immediately but are recorded in the tenant audit log with the actor's identity. External contractor accounts always begin locked and are unlocked by an Admin after background check completion, then assigned only the minimum roles needed for their statement of work.

## 14. Standards, Certifications & Data Residency

Meridian Cloud is SOC 2 Type 2 certified and re-audited annually. The information security policy requires penetration tests at least twice per year against a recognized external test set. Data residency follows the region of the tenant: tenants created in the US are confined to us-east-1, and tenants in the EU are confined to eu-west-1. Cross-region copies are permitted in both directions with the "copyable" flag.

Key management: all encryption keys are generated inside a hardware security module in the primary region, and every key has a lifetime of 180 days. Customer-provided keys are supported but must be AES-256 or stronger, and the customer retains revocation control.

## 15. Billing, Pricing and Quotas

Billing is consumption-based. Subscription tiers: Standard, Business, and Enterprise. The Standard tier is limited to 5 concurrent dashboards, 1 workspace, and 50,000 API calls per month. The Business tier includes 3 workspaces and 1,000,000 API calls per month. Enterprise pricing is custom but requires a minimum of 12 months.

Quota walls are surfaced in the API envelope as QUOTA_EXCEEDED, and quota resets happen on the first of the month at 00:00 UTC. The tenant export ceiling is 100,000 rows per day for Business tier and 2,000,000 rows per day for Enterprise.

## 16. Engineering Runbook — Reliability Practices

System builds use three-env promotion: development, staging, production, and each promotion deletes the target namespace and recreates from the build artifact. (This is intentional: no incremental namespace merging.)

Production incidents get a permanent "knowledge" page within the runbook wiki. The runbook index mandates a decision tree that prioritizes availability over durability for interactive paths but durability over availability for accounting feeds. The accounting feed is written through the ledger service, which fsyncs every ledger record before acknowledging the write to the client. Fine-grained mutation of ledger records is forbidden by the append-only policy; corrections are emitted as reversed entries.

Every recovery drill is announced 48 hours in advance on the #ops channel. Disaster recovery drills run four times a year and include both regions. After the annual drill, the recovery time objective of 4 hours is re-measured and, if improved, the new value is written back into the platform handbook and reported to the audit committee.

## 17. People FAQ — Common Questions

Q. "Can I work from another country for a week?"
A. Remote work is allowed in compliant states if the stay is 30 days or fewer and the travel request is filed through the Ops portal at least 14 days before departure. Longer stays require formal approval and, depending on the country, may trigger tax questions handled by People Operations.

Q. "Who do I ask about the pilot flag?"
A. The Pilot dashboard is administered by the platform team. To change a feature flag for a tenant, file a request in the #flags channel.

## 18. Observability & Metrics

Every workspace exposes the standard telemetry suite: request latency, error rate, and token consumption. Latency is measured at the p95 rather than the average, because batch background refreshes skew the mean. The p95 threshold on the interactive tier is 1.2 seconds; sustained p95 above that for five consecutive minutes creates an automated ticket in the platform queue.

Dashboard drift is a known hazard. Any dashboard whose source query changes and is then left untouched for 60 days is automatically paused and its owner is notified. Paused dashboards are surfaced with a "Paused" badge, and they do not consume API quota while paused.

Cost telemetry comes from the FinOps feed, which exposes daily cost per workspace per service. The feed is recomputed every morning at 05:00 UTC against the previous day's ledger. Workspaces that exceed 120% of their 30-day average cost for three straight days are flagged to the workspace admin, but the system never blocks queries because of cost alone. Contractual term limits on API quota are enforced at the point of authorization and cannot be overridden at runtime by workspace admins.

## 19. Release & Versioning Policy

Pending releases are described by semantic versioning, with the platform contract versioned at the /v1 prefix for backward compatibility. Major versions can introduce breaking changes but must be announced at least 60 days in advance on the changelog page. Minor and patch releases are backward-compatible and are staged weekly.

Deprecation policy: an API path marked deprecated continues to work for 12 months after the deprecation announcement, and every deprecated path returns the Warning-Deprecation header on all responses. The platform team publishes the deprecation calendar each quarter, and any tenant that calls a deprecated path more than 100 times per day receives a digest email every Monday.

Feature flags tied to deprecated paths are removed only after the 12-month window closes. Rolling back a release that already entered the fleet follows the deployment windows above: emergency rollbacks are exempt from the Tuesday/Thursday rule, but every emergency rollback needs the re-review within 48 hours and a blameless postmortem within 3 business days, same as any other incident.

## 20. Content Deadlines & Editorial Cadence

The editorial calendar in this company runs on a biweekly rhythm. Notes are gathered on the Monday of week 1, the internal draft is due by Friday of week 1, peer review falls in week 2, and release to the curated deck happens on the final Friday. Content publishing hours are 09:00 to 17:00 UTC, and every published item requires a fact-check against the internal corpus.

If a published item is later found to contradict a corpus policy (for example, a policy in a knowledge article vs. a statement here), the corpus policy wins and the article is amended instead of the policy. This rule exists so that retrieval never ranks fictional filler above the authoritative source: authoritative sections are the numbered policies below and the section titles are authoritative; filler and trivia sections are never authoritative. Users who find a contradiction between a published document and this knowledge base should file a ticket with the platform team and link both pages, so the resolution becomes visible in the audit log.

## 21. Policy Schedules & Special Coverage

The two-wheeler insurance policy (Document Schedule Ref: DG_20201AGENT_SCHEDULESC) is registered under policy number D277856892. The policy covers accidental damage, third-party liability, and personal accident cover for two-wheelers.