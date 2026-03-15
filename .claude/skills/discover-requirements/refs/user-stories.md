# User Stories Reference

> Patterns for well-formed user stories, acceptance criteria, and story splitting.

---

## User Story Format

```
As a [role], I want [capability], so that [benefit].
```

Every story must include all three parts. The "so that" clause reveals intent and enables trade-off decisions.

**Role** must be a specific actor, not "user." Use: customer, admin, API consumer, billing manager, guest visitor.

---

## INVEST Criteria

Validate every story against:

| Criterion | Question | Fix If Violated |
|-----------|----------|-----------------|
| **Independent** | Can this be built without other stories? | Remove coupling or split |
| **Negotiable** | Is there room to discuss implementation? | Remove solution prescriptions |
| **Valuable** | Does this deliver user/business value? | Reframe or merge into parent |
| **Estimable** | Can the team size this? | Spike or split to reduce unknowns |
| **Small** | Fits in one iteration? | Split using techniques below |
| **Testable** | Can acceptance be verified? | Add concrete acceptance criteria |

---

## Acceptance Criteria Format

Use Given/When/Then (Gherkin) for precision:

```
Given [precondition or initial state]
When [action or trigger]
Then [expected outcome or observable result]
```

### Rules for Good Acceptance Criteria

1. **One behavior per criterion** — split compound outcomes into separate criteria
2. **Observable outcomes only** — assert what the user sees, not internal state
3. **Include boundary cases** — empty input, maximum values, unauthorized access
4. **Specify error behavior** — what happens when things go wrong

### Example: Complete Story with Criteria

```
As a customer, I want to receive an email when my order ships,
so that I can track my package.

Acceptance Criteria:
- Given an order with status "processing," when the warehouse marks it
  "shipped," then the customer receives an email within 5 minutes
- Given a customer with no email on file, when the order ships,
  then the system logs a warning and skips email delivery
- Given an order already marked "shipped," when the status is set to
  "shipped" again, then no duplicate email is sent
- Given the email service is unavailable, when the order ships,
  then the notification is queued for retry with exponential backoff
```

---

## Story Splitting Techniques

When a story is too large, split along these dimensions:

### 1. Workflow Steps







Split a multi-step process into individual steps.
```
Before: "As a user, I want to complete checkout"
After:
  - "As a user, I want to add items to cart"

  - "As a user, I want to enter shipping address"

  - "As a user, I want to submit payment"

  - "As a user, I want to receive order confirmation"

```




### 2. Business Rule Variations


Separate complex rules into individual stories.
```

Before: "As an admin, I want to apply discounts"
After:

  - "...apply percentage discounts to individual items"

  - "...apply fixed-amount discounts to orders"

  - "...apply buy-one-get-one promotions"


```





### 3. Data Variations


Split by input type or data source.


```
Before: "As a user, I want to import contacts"

After:


  - "...import contacts from CSV"
  - "...import contacts from Google"

  - "...import contacts manually"


```


### 4. Operations (CRUD)


Split by create, read, update, delete.


### 5. Happy Path vs. Edge Cases

Build the happy path first, then add error handling and edge cases as separate stories.

### 6. Performance Tiers

Split by performance level.
```
Before: "As a user, I want fast search results"
After:
  - "...search returns results within 2 seconds (basic index)"
  - "...search returns results within 200ms (with caching layer)"
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| **Epic disguised as story** | Too large to estimate or deliver in one iteration | Split using techniques above |
| **Technical story** | "As a developer, I want to refactor the database" — no user value | Reframe as user-facing outcome or classify as technical task |
| **Solution-prescriptive** | "As a user, I want a Redis cache" — dictates implementation | Rewrite as need: "I want fast search results" |
| **Compound story** | Multiple behaviors in one story | Split into atomic behaviors |
| **Missing "so that"** | No stated benefit — can't prioritize or negotiate | Add the benefit clause |
| **Vague criteria** | "System works correctly" — untestable | Rewrite with specific observable outcomes |
