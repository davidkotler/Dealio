# Non-Functional Requirements Checklist

> Systematic checklist of quality attribute categories with elicitation prompts.

Walk through each category during requirements discovery. Not every category applies to every feature—skip those that genuinely don't apply, but explicitly state why.

---

## How to Use This Checklist

For each category:







1. Ask the elicitation questions
2. If relevant, capture a measurable target
3. Document the validation approach (how you'll verify the target is met)
4. Note trade-offs with other quality attributes




---





## Runtime Attributes









### Performance






**Elicitation prompts:**





- What latency is acceptable for user-facing operations? (p50, p95, p99)
- What throughput must the system sustain? (requests/sec, messages/sec)


- Are there batch processing windows with time constraints?




- What are the largest payloads or datasets this feature handles?



**Target format:** "p95 latency < 200ms for [operation] under [load]"







### Scalability


**Elicitation prompts:**








- How many concurrent users/requests are expected at launch? In 12 months?
- What data growth rate is expected? (GB/month, records/day)
- Are there seasonal or event-driven traffic spikes?



- Must the system scale horizontally without code changes?










**Target format:** "Handle [N] concurrent [units] with linear horizontal scaling"

### Availability



**Elicitation prompts:**











- What uptime target is required? (99.9%, 99.95%, 99.99%)
- What's the maximum acceptable downtime per month?
- Which components are critical vs. degradable?
- What's the tolerable recovery time after failure? (RTO)



- What's the tolerable data loss window? (RPO)








**Target format:** "[N] nines availability measured over [period]"







---



## Evolution Attributes






### Modifiability







**Elicitation prompts:**








- What parts of this feature are likely to change within 6 months?
- Are business rules expected to evolve frequently?

- Must the system support feature flags or gradual rollout?







**Target format:** "Changes to [component] deployable in < [time] without affecting [other component]"






### Extensibility







**Elicitation prompts:**







- Will third parties need to extend this system? (plugins, webhooks, APIs)
- What integration patterns must be supported?
- Are there anticipated variants of this feature for different user segments?



---









## Security Attributes



### Authentication & Authorization






**Elicitation prompts:**





- Who can access this feature? What roles exist?

- What authentication mechanism is used? (OAuth2, API keys, SSO)
- What authorization model applies? (RBAC, ABAC, resource-level)
- Are there multi-tenancy isolation requirements?



### Data Sensitivity





**Elicitation prompts:**



- Does this feature handle PII, financial data, or health records?


- What data classification applies? (public, internal, confidential, restricted)
- Are there encryption-at-rest or encryption-in-transit requirements?
- What data retention and deletion policies apply?








### Compliance


**Elicitation prompts:**

- Which regulations apply? (GDPR, HIPAA, SOC2, PCI-DSS)
- Are there audit trail requirements?
- Is data residency constrained to specific regions?

- Are there penetration testing or security review gates?





**Target format:** "Compliant with [regulation] by [date], validated by [method]"


---





## Operational Attributes

### Observability





**Elicitation prompts:**


- What SLIs should be measured for this feature?

- What SLOs will be committed to?
- What alerting thresholds trigger incident response?
- Is distributed tracing required across service boundaries?
- What dashboards are needed for operational visibility?

**Target format:** "SLI: [metric]. SLO: [target] over [window]. Alert at [threshold]."



### Deployability



**Elicitation prompts:**

- Can this be deployed independently of other services?
- Is zero-downtime deployment required?


- What rollback strategy is needed?


- Are canary or blue-green deployments expected?

### Testability


**Elicitation prompts:**


- What test coverage level is required?
- Are there specific testing requirements? (contract tests, load tests, chaos tests)

- Must the feature be testable in isolation from external dependencies?


---

## Reliability Attributes

### Fault Tolerance

**Elicitation prompts:**

- What happens when an upstream dependency fails?

- Should the feature degrade gracefully or fail fast?

- Are there retry, circuit breaker, or fallback requirements?
- What failure modes are acceptable vs. unacceptable?

### Data Integrity


**Elicitation prompts:**


- What consistency model is required? (strong, eventual, causal)
- Are there idempotency requirements for operations?
- Must operations be atomic across multiple systems?
- Is an audit trail required for data mutations?



**Target format:** "All [operation type] operations are idempotent. [Entity] mutations recorded in audit log."

### Disaster Recovery

**Elicitation prompts:**

- What's the recovery time objective (RTO)?
- What's the recovery point objective (RPO)?
- Is multi-region failover required?
- What backup frequency and retention is needed?

---

## Business Attributes

### Cost

**Elicitation prompts:**

- What infrastructure budget is allocated?
- Are there per-transaction cost constraints?
- What's the cost ceiling for third-party services?

### Time-to-Market

**Elicitation prompts:**

- What is the hard deadline?
- Can the feature be delivered incrementally? What's the MVP?
- Are there external commitments tied to this timeline?

### Accessibility

**Elicitation prompts:**

- What WCAG conformance level is required? (A, AA, AAA)
- Are there specific assistive technology requirements?
- Is this feature subject to accessibility regulations?

---

## Quick Capture Template

For each applicable NFR, capture:

```markdown
### NFR-[N]: [Category] — [Short Title]
- **Target:** [specific, measurable value]
- **Rationale:** [why this matters to users or the business]
- **Validation:** [how to test or measure]
- **Trade-offs:** [what other attributes this may impact]
- **Priority:** Must Have | Should Have | Nice to Have
```
