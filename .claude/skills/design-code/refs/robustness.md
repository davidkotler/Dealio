# Robustness Design Reference

> Design systems that withstand failure, reject invalid input, and maintain integrity under stress.

---

## Core Principle

**Robust systems assume everything can fail and design accordingly.** They validate aggressively at boundaries, fail fast with clear signals, and never silently corrupt state.

---

## Must / Never

### MUST

| Requirement | Rationale |
|-------------|-----------|
| Validate all inputs at system boundaries | Invalid data detected early cannot corrupt downstream state |
| Define explicit error types for each failure mode | Callers can handle specific failures appropriately |
| Set timeouts on all blocking operations | Prevent indefinite hangs from cascading |
| Return `Result` types for expected failures | Make failure handling explicit in the type system |
| Preserve error context through call chains | Root cause is discoverable without guesswork |
| Design mutations to be idempotent | Safe retries after partial failures |
| Implement circuit breakers for external calls | Prevent cascade failures from propagating |
| Bound all collections and queues | Prevent memory exhaustion under load |

### NEVER

| Prohibition | Consequence |
|-------------|-------------|
| Silently swallow exceptions | Hidden failures corrupt state invisibly |
| Return `None`/`null` for errors | Caller cannot distinguish "not found" from "failed" |
| Trust input from external sources | Injection attacks, crashes, data corruption |
| Retry indefinitely without backoff | Amplify failures, exhaust resources |
| Use catch-all handlers without re-raising | Mask programmer errors, hide bugs |
| Assume operations succeed | One unhandled failure path crashes the system |
| Mix validation with business logic | Validation gaps appear as code evolves |
| Ignore partial failure scenarios | Data inconsistency across boundaries |

---

## When / Then

### Input Handling

**WHEN** receiving data from external sources (API, file, message queue)  
**THEN** validate schema, types, and business constraints immediately:

```python
# ✅ Boundary validation
class CreateOrderRequest(BaseModel):
    customer_id: CustomerId
    items: list[OrderItem] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def validate_items(cls, v: list[OrderItem]) -> list[OrderItem]:
        if sum(item.quantity for item in v) > 1000:
            raise ValueError("Order exceeds maximum quantity")
        return v

@router.post("/orders")
async def create_order(request: CreateOrderRequest) -> Order:
    # Request is guaranteed valid here
    return await order_service.create(request)
```

```python
# ❌ Validation mixed with logic
@router.post("/orders")
async def create_order(data: dict) -> Order:
    if "items" not in data:
        raise HTTPException(400, "Missing items")  # Scattered validation
    # More validation buried in service layer...
```

---

### Error Representation

**WHEN** an operation has expected failure modes  
**THEN** model failures explicitly with union types or Result:

```python
# ✅ Explicit failure modes
from typing import Union
from dataclasses import dataclass

@dataclass(frozen=True)
class InsufficientFunds:
    available: Money
    required: Money

@dataclass(frozen=True)
class AccountLocked:
    reason: str
    locked_until: datetime | None

@dataclass(frozen=True)
class PaymentSuccess:
    transaction_id: str
    amount: Money

PaymentResult = Union[PaymentSuccess, InsufficientFunds, AccountLocked]

async def process_payment(amount: Money) -> PaymentResult:
    # Caller must handle all cases
    ...
```

```python
# ❌ Exceptions for control flow
async def process_payment(amount: Money) -> str:
    # Caller might forget to catch these
    raise InsufficientFundsError(...)  # Exception for expected case
```

---

### External Dependencies

**WHEN** calling external services or databases  
**THEN** apply timeout + retry + circuit breaker:

```python
# ✅ Defensive external calls
from tenacity import retry, stop_after_attempt, wait_exponential
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
async def fetch_inventory(sku: str) -> InventoryStatus:
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{INVENTORY_URL}/items/{sku}")
        response.raise_for_status()
        return InventoryStatus.model_validate(response.json())
```

```python
# ❌ Naked external call
async def fetch_inventory(sku: str) -> InventoryStatus:
    async with httpx.AsyncClient() as client:  # No timeout
        response = await client.get(f"{INVENTORY_URL}/items/{sku}")
        return InventoryStatus.model_validate(response.json())  # No retry
```

---

### Error Propagation

**WHEN** catching and re-raising exceptions  
**THEN** chain the original cause:

```python
# ✅ Preserved context
class OrderProcessingError(Exception):
    def __init__(self, order_id: str, message: str):
        self.order_id = order_id
        super().__init__(f"Order {order_id}: {message}")

async def process_order(order_id: str) -> Order:
    try:
        return await _do_process(order_id)
    except PaymentGatewayError as e:
        raise OrderProcessingError(order_id, "Payment failed") from e
    except InventoryError as e:
        raise OrderProcessingError(order_id, "Inventory unavailable") from e
```

```python
# ❌ Lost context
async def process_order(order_id: str) -> Order:
    try:
        return await _do_process(order_id)
    except Exception:
        raise Exception("Processing failed")  # Original cause lost
```

---

### Idempotency

**WHEN** designing operations that may be retried  
**THEN** use idempotency keys and check-before-write:

```python
# ✅ Idempotent operation
async def process_payment(
    payment_id: PaymentId,
    idempotency_key: str,
    amount: Money,
) -> PaymentResult:
    # Check if already processed
    existing = await payment_repo.get_by_idempotency_key(idempotency_key)
    if existing:
        return existing.result

    # Process and record atomically
    async with transaction():
        result = await gateway.charge(amount)
        await payment_repo.save(Payment(
            id=payment_id,
            idempotency_key=idempotency_key,
            result=result,
        ))
    return result
```

```python
# ❌ Non-idempotent
async def process_payment(amount: Money) -> PaymentResult:
    return await gateway.charge(amount)  # Retry = double charge
```

---

### Graceful Degradation

**WHEN** a non-critical dependency fails  
**THEN** return degraded response rather than error:

```python
# ✅ Graceful degradation
async def get_product_page(product_id: str) -> ProductPage:
    product = await product_repo.get(product_id)  # Critical - fail if unavailable

    # Non-critical enrichments
    recommendations = await safe_fetch(
        recommendation_service.get(product_id),
        default=[],
        log_message="Recommendations unavailable",
    )
    reviews = await safe_fetch(
        review_service.get(product_id),
        default=[],
        log_message="Reviews unavailable",
    )

    return ProductPage(
        product=product,
        recommendations=recommendations,
        reviews=reviews,
        degraded=not recommendations or not reviews,
    )

async def safe_fetch[T](
    coro: Awaitable[T],
    default: T,
    log_message: str,
) -> T:
    try:
        return await asyncio.wait_for(coro, timeout=2.0)
    except Exception as e:
        logger.warning(log_message, error=str(e))
        return default
```

---

### Resource Bounds

**WHEN** accepting collections or streams  
**THEN** enforce explicit limits:

```python
# ✅ Bounded input
class BatchRequest(BaseModel):
    items: list[Item] = Field(max_length=100)

async def process_batch(request: BatchRequest) -> BatchResult:
    # Guaranteed max 100 items
    ...

# ✅ Bounded queue
from asyncio import Queue

work_queue: Queue[Task] = Queue(maxsize=1000)

async def enqueue(task: Task) -> bool:
    try:
        work_queue.put_nowait(task)
        return True
    except asyncio.QueueFull:
        logger.warning("Queue full, rejecting task", task_id=task.id)
        return False
```

```python
# ❌ Unbounded
class BatchRequest(BaseModel):
    items: list[Item]  # Could be millions

work_queue: Queue[Task] = Queue()  # Unbounded growth
```

---

## Patterns

### Pattern: Fail-Fast Validation Layer

Centralize all validation at system entry points:

```
┌─────────────────────────────────────────┐
│           BOUNDARY LAYER                │
│  ┌─────────────────────────────────┐    │
│  │     Schema Validation           │    │  ← Pydantic models
│  ├─────────────────────────────────┤    │
│  │     Business Rule Validation    │    │  ← Domain validators
│  ├─────────────────────────────────┤    │
│  │     Authorization Check         │    │  ← Permission guards
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
                    │
                    ▼ (only valid requests pass)
┌─────────────────────────────────────────┐
│           DOMAIN LAYER                  │
│     (can assume inputs are valid)       │
└─────────────────────────────────────────┘
```

### Pattern: Bulkhead Isolation

Isolate failure domains to prevent cascade:

```python
# Separate thread pools for different dependency types
db_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="db")
api_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="api")
file_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="file")

# Failure in API calls won't exhaust DB connection capacity
```

### Pattern: Dead Letter Queue

Capture failed operations for later analysis/retry:

```python
async def process_event(event: Event) -> None:
    try:
        await handle(event)
    except RetryableError:
        await retry_queue.put(event)
    except NonRetryableError as e:
        await dead_letter_queue.put(DeadLetter(
            event=event,
            error=str(e),
            failed_at=utc_now(),
        ))
        logger.error("Event sent to DLQ", event_id=event.id, error=str(e))
```

---

## Anti-Patterns

### Anti-Pattern: Defensive Copying Everywhere

```python
# ❌ Paranoid copying wastes resources
def process(data: list[Item]) -> Result:
    safe_data = copy.deepcopy(data)  # Unnecessary if using immutable types
    ...
```

**Fix:** Use immutable data structures (frozen dataclasses, Pydantic with `frozen=True`).

### Anti-Pattern: Empty Catch Blocks

```python
# ❌ Silent failure
try:
    send_notification(user_id)
except Exception:
    pass  # Notifications silently broken
```

**Fix:** Log, count, or propagate—never ignore.

### Anti-Pattern: Stringly-Typed Errors

```python
# ❌ Error checking via string matching
result = process()
if "error" in result.lower():
    handle_error()
```

**Fix:** Use typed error classes or Result types.

### Anti-Pattern: Optimistic Serialization

```python
# ❌ Assumes valid JSON structure
data = json.loads(response.text)
user_id = data["user"]["id"]  # KeyError if structure changes
```

**Fix:** Validate with Pydantic before accessing.

```python
# ❌ Defaults hide bugs
value = data.get("key", "default")  # Missing data goes unnoticed
name = getattr(obj, "name", None)   # Typos and missing attrs masked
```

**Fix:** Use direct access for required data—let `KeyError`/`AttributeError` surface problems immediately.

```python
# ✅ Fail fast
value = data["key"]
name = obj.name
```

---

### Anti-Pattern: Exception Swallowing

```python
# ❌ Silent failure
try:
    risky_operation()
except Exception:
    pass  # Bug hidden forever
```

**Fix:** Catch specific exceptions with logging, or let unexpected errors propagate.

```python
# ✅ Specific handling
try:
    risky_operation()
except ValidationError as e:
    logger.error("Validation failed", error=str(e))
    raise
```

---

### Anti-Pattern: Optional Return for Required Data

```python
# ❌ Caller burden
def get_user(id: str) -> User | None:  # None checks spread everywhere
```

**Fix:** Raise when absence is exceptional; use `Result` types when absence is expected.

```python
# ✅ Clear contract
def get_user(id: str) -> User:
    """Raises UserNotFoundError if user doesn't exist."""
```

---

### Anti-Pattern: Duck Typing Without Contracts

```python
# ❌ Runtime guessing
if hasattr(obj, "process"):
    obj.process()  # Interface violations hidden
```

**Fix:** Define protocols explicitly; let missing methods fail at call site.

```python
# ✅ Protocol contract
def handle(processor: Processor) -> None:
    processor.process()  # Type checker enforces interface
```

---

## Decision Matrix

| Scenario | Robustness Strategy |
|----------|---------------------|
| External API call | Timeout + retry + circuit breaker |
| User input | Pydantic validation at boundary |
| Database write | Idempotency key + transaction |
| Async task | Dead letter queue for failures |
| Optional feature | Graceful degradation with logging |
| Collection input | Explicit size bounds |
| Error propagation | Chain original cause |
| Resource cleanup | Context managers / `try`-`finally` |

---

## Quality Gates

Before completing a robustness review:

- [ ] All external inputs validated at boundaries
- [ ] All expected failure modes have explicit types
- [ ] All external calls have timeouts configured
- [ ] All retryable operations are idempotent
- [ ] All collections have explicit bounds
- [ ] No silent exception swallowing
- [ ] No silent defaults for missed data
- [ ] No Duck Typing Without Contracts
- [ ] No optional return for required data
- [ ] Error context preserved through chains
- [ ] Non-critical failures degrade gracefully
