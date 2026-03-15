# Testability Design Reference

> Design code that is easy to test in isolation, fast to verify, and resilient to refactoring.

---

## Quick Navigation

| Section | Purpose |
|---------|---------|
| [Must / Never](#must--never) | Non-negotiable rules |
| [When / Then](#when--then) | Situational decisions |
| [Patterns](#patterns) | Proven testable designs |
| [Anti-Patterns](#anti-patterns) | Designs that resist testing |
| [Examples](#examples) | Concrete implementations |

---

## Must / Never

### MUST

| Rule | Rationale |
|------|-----------|
| **Inject all dependencies via constructor** | Enables test doubles; makes dependencies explicit |
| **Separate pure logic from I/O** | Pure functions test without mocks or fixtures |
| **Design units with single responsibility** | Fewer code paths = fewer test cases needed |
| **Use protocols/ABCs for collaborators** | Allows substitution with fakes/stubs/mocks |
| **Make side effects explicit and boundary-pushed** | Isolates effectful code; core logic stays pure |
| **Keep constructors trivial (assignment only)** | Complex setup belongs in factories, not constructors |
| **Design for determinism** | Same input → same output; no hidden state |
| **Provide explicit seams for test doubles** | Every external dependency has an injection point |
| **Return values over mutating state** | Assertions on returns are simpler than state inspection |
| **Expose observable behavior, not internals** | Tests survive refactoring when they test contracts |

### NEVER

| Rule | Consequence |
|------|-------------|
| **Use global or module-level mutable state** | Tests pollute each other; order-dependent failures |
| **Instantiate collaborators inside methods** | No seam for injection; forced to use real implementations |
| **Mix queries (return data) with commands (change state)** | Can't verify state change without side effects |
| **Create "god classes" spanning multiple concerns** | Combinatorial explosion of test scenarios |
| **Use singletons for dependencies** | Hidden coupling; shared state across tests |
| **Call `datetime.now()` or `random()` directly** | Non-deterministic; tests become flaky |
| **Perform I/O in constructors** | Object creation becomes slow and unpredictable |
| **Hide dependencies in method bodies** | Invisible coupling; impossible to substitute |
| **Create deep inheritance hierarchies (>2 levels)** | Tests must understand entire hierarchy |
| **Use static methods with side effects** | Cannot substitute; global state mutation |

---

## When / Then

### Dependency Management

**WHEN** a class needs a collaborator  
**THEN** inject it via constructor parameter typed to an abstraction

```python
# ✅ Testable
class OrderService:
    def __init__(self, repo: OrderRepository, notifier: Notifier):
        self._repo = repo
        self._notifier = notifier
```

---

**WHEN** a method needs external data  
**THEN** accept it as a parameter; don't fetch internally

```python
# ✅ Testable - data passed in
def calculate_discount(order: Order, customer_tier: CustomerTier) -> Money: ...

# ❌ Untestable - fetches internally
def calculate_discount(order_id: str) -> Money:
    order = db.get(order_id)  # Hidden dependency
```

---

**WHEN** logic depends on current time  
**THEN** inject a clock abstraction

```python
# ✅ Testable
class AuctionService:
    def __init__(self, clock: Clock):
        self._clock = clock

    def is_expired(self, auction: Auction) -> bool:
        return self._clock.now() > auction.end_time
```

---

**WHEN** a test requires mocking more than 2-3 collaborators  
**THEN** the unit has too many responsibilities—decompose it

```python
# ❌ Design smell - too many dependencies
class OrderProcessor:
    def __init__(self, repo, payment, inventory, shipping, notifications, analytics): ...

# ✅ Decompose into focused units
class OrderProcessor:
    def __init__(self, order_workflow: OrderWorkflow):
        self._workflow = order_workflow  # Facade over sub-components
```

---

**WHEN** an operation has side effects  
**THEN** separate the decision (pure) from the action (effectful)

```python
# ✅ Testable - decision is pure
def should_send_reminder(user: User, last_activity: datetime) -> bool:
    return (datetime.now() - last_activity).days > 7

# Effect pushed to boundary
async def maybe_send_reminder(user: User) -> None:
    if should_send_reminder(user, user.last_activity):
        await notifier.send(user.id, REMINDER_TEMPLATE)
```

---

**WHEN** testing requires complex object setup  
**THEN** create test factories or builders

```python
# ✅ Test factory pattern
class OrderFactory:
    @staticmethod
    def build(
        customer_id: str = "cust-123",
        items: list[LineItem] | None = None,
        status: OrderStatus = OrderStatus.PENDING,
    ) -> Order:
        return Order(
            id=OrderId(f"order-{uuid4().hex[:8]}"),
            customer_id=CustomerId(customer_id),
            items=items or [LineItemFactory.build()],
            status=status,
        )
```

---

**WHEN** external systems are involved (DB, HTTP, filesystem)  
**THEN** define a port (interface) and implement adapters

```python
# ✅ Port (interface)
class OrderRepository(Protocol):
    async def get(self, order_id: OrderId) -> Order | None: ...
    async def save(self, order: Order) -> None: ...

# Production adapter
class PostgresOrderRepository(OrderRepository): ...

# Test adapter
class InMemoryOrderRepository(OrderRepository):
    def __init__(self):
        self._orders: dict[OrderId, Order] = {}
```

---

**WHEN** a function transforms data  
**THEN** make it pure—no side effects, deterministic output

```python
# ✅ Pure function - trivially testable
def apply_discount(price: Money, discount_pct: Decimal) -> Money:
    return Money(price * (1 - discount_pct))

# Test
def test_apply_discount():
    assert apply_discount(Money(100), Decimal("0.1")) == Money(90)
```

---

**WHEN** behavior varies based on type/strategy  
**THEN** use composition with injected strategies

```python
# ✅ Strategy injection - each strategy testable in isolation
class PricingService:
    def __init__(self, discount_strategy: DiscountStrategy):
        self._discount = discount_strategy

    def calculate(self, order: Order) -> Money:
        return self._discount.apply(order.subtotal)
```

---

**WHEN** a class orchestrates multiple steps  
**THEN** extract each step as an injectable collaborator

```python
# ✅ Each step is independently testable
class CheckoutUseCase:
    def __init__(
        self,
        validator: OrderValidator,
        pricer: OrderPricer,
        payment: PaymentGateway,
        repo: OrderRepository,
    ):
        self._validator = validator
        self._pricer = pricer
        self._payment = payment
        self._repo = repo

    async def execute(self, request: CheckoutRequest) -> Order:
        order = Order.from_request(request)
        self._validator.validate(order).raise_if_invalid()
        order.total = self._pricer.calculate(order)
        await self._payment.charge(order.total, request.payment_token)
        await self._repo.save(order)
        return order
```

---

## Patterns

### Pattern 1: Humble Object

Separate testable logic from hard-to-test infrastructure.

```python
# ✅ Humble Object Pattern
# Infrastructure (hard to test, kept minimal)
class OrderController:
    def __init__(self, use_case: CreateOrderUseCase):
        self._use_case = use_case

    async def post(self, request: Request) -> Response:
        dto = CreateOrderDTO.model_validate(await request.json())
        result = await self._use_case.execute(dto)  # Delegates immediately
        return Response(status=201, body=result.model_dump())

# Logic (easy to test, contains all business rules)
class CreateOrderUseCase:
    async def execute(self, dto: CreateOrderDTO) -> OrderResponse: ...
```

---

### Pattern 2: Functional Core, Imperative Shell

Pure business logic wrapped by an imperative shell that handles I/O.

```python
# ✅ Functional Core (pure, testable)
def calculate_order_total(
    items: list[LineItem],
    discounts: list[Discount],
    tax_rate: Decimal,
) -> OrderTotal:
    subtotal = sum(item.price * item.quantity for item in items)
    discount_amount = sum(d.apply(subtotal) for d in discounts)
    taxable = subtotal - discount_amount
    tax = taxable * tax_rate
    return OrderTotal(subtotal=subtotal, discount=discount_amount, tax=tax, total=taxable + tax)

# Imperative Shell (handles I/O, thin)
async def process_order(order_id: OrderId) -> None:
    order = await repo.get(order_id)
    discounts = await discount_service.get_applicable(order)
    tax_rate = await tax_service.get_rate(order.shipping_address)

    total = calculate_order_total(order.items, discounts, tax_rate)  # Pure call

    await repo.update(order_id, total=total)
```

---

## Anti-Patterns

### Anti-Pattern 1: Service Locator

Hidden dependencies fetched from a global registry.

```python
# ❌ Service Locator - hidden dependencies
class OrderService:
    def create_order(self, request: CreateOrderRequest) -> Order:
        repo = ServiceLocator.get(OrderRepository)  # Where does this come from?
        notifier = ServiceLocator.get(Notifier)  # Hidden coupling
        ...

# ✅ Explicit injection
class OrderService:
    def __init__(self, repo: OrderRepository, notifier: Notifier):
        self._repo = repo
        self._notifier = notifier
```

---

### Anti-Pattern 2: Static Cling

Static methods with side effects that can't be substituted.

```python
# ❌ Static method - cannot substitute in tests
class AuditLogger:
    @staticmethod
    def log(event: AuditEvent) -> None:
        requests.post(AUDIT_SERVICE_URL, json=event.dict())  # HTTP in static!

class OrderService:
    def complete(self, order: Order) -> None:
        AuditLogger.log(AuditEvent(action="order_completed"))  # Cannot mock

# ✅ Instance method with injection
class OrderService:
    def __init__(self, audit: AuditLogger):
        self._audit = audit

    def complete(self, order: Order) -> None:
        self._audit.log(AuditEvent(action="order_completed"))
```

---

### Anti-Pattern 3: Train Wreck (Law of Demeter Violation)

Reaching through objects to access nested dependencies.

```python
# ❌ Train wreck - tight coupling to structure
def get_shipping_cost(order: Order) -> Money:
    return order.customer.address.region.shipping_zone.base_rate

# ✅ Tell, don't ask
def get_shipping_cost(order: Order, shipping_calculator: ShippingCalculator) -> Money:
    return shipping_calculator.calculate(order.shipping_address)
```

---

### Anti-Pattern 4: Constructor Over-Injection

Too many constructor parameters signals too many responsibilities.

```python
# ❌ Constructor over-injection (>5 params = smell)
class OrderProcessor:
    def __init__(
        self,
        order_repo: OrderRepository,
        customer_repo: CustomerRepository,
        product_repo: ProductRepository,
        payment_gateway: PaymentGateway,
        shipping_service: ShippingService,
        notification_service: NotificationService,
        analytics_service: AnalyticsService,
        audit_logger: AuditLogger,
    ): ...

# ✅ Decompose or use facade
class OrderProcessor:
    def __init__(self, workflow: OrderWorkflow):
        self._workflow = workflow  # Aggregates sub-concerns
```

---

### Anti-Pattern 5: Test-Specific Production Code

Adding code to production solely for testing purposes.

```python
# ❌ Test hook in production code
class PaymentService:
    _test_mode: bool = False  # Pollutes production

    def charge(self, amount: Money) -> PaymentResult:
        if self._test_mode:
            return PaymentResult(success=True)  # Bypass in tests
        return self._gateway.charge(amount)

# ✅ Inject the dependency instead
class PaymentService:
    def __init__(self, gateway: PaymentGateway):
        self._gateway = gateway  # Inject fake gateway in tests
```

---

### Anti-Pattern 6: Time Bombs

Direct use of system time creates non-deterministic tests.

```python
# ❌ Time bomb - flaky around midnight, DST, etc.
def is_expired(subscription: Subscription) -> bool:
    return datetime.now() > subscription.end_date

# ✅ Inject clock
def is_expired(subscription: Subscription, now: datetime) -> bool:
    return now > subscription.end_date

# Or use clock abstraction
class SubscriptionService:
    def __init__(self, clock: Clock):
        self._clock = clock

    def is_expired(self, subscription: Subscription) -> bool:
        return self._clock.now() > subscription.end_date
```

---

## Examples

### Example 1: Testable Domain Service

```python
from abc import ABC, abstractmethod
from decimal import Decimal
from pydantic import BaseModel

# Abstractions (ports)
class OrderRepository(ABC):
    @abstractmethod
    async def get(self, order_id: str) -> "Order | None": ...
    @abstractmethod
    async def save(self, order: "Order") -> None: ...

class DiscountCalculator(ABC):
    @abstractmethod
    def calculate(self, order: "Order") -> Decimal: ...

# Domain model
class Order(BaseModel):
    id: str
    items: list["LineItem"]
    subtotal: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    total: Decimal = Decimal("0")

# Testable service
class OrderPricingService:
    def __init__(self, repo: OrderRepository, discount_calc: DiscountCalculator):
        self._repo = repo
        self._discount_calc = discount_calc

    async def price_order(self, order_id: str) -> Order:
        order = await self._repo.get(order_id)
        if not order:
            raise OrderNotFoundError(order_id)

        order.subtotal = sum(item.total for item in order.items)
        order.discount = self._discount_calc.calculate(order)
        order.total = order.subtotal - order.discount

        await self._repo.save(order)
        return order

# Test with fakes
class InMemoryOrderRepository(OrderRepository):
    def __init__(self, orders: dict[str, Order] | None = None):
        self._orders = orders or {}

    async def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    async def save(self, order: Order) -> None:
        self._orders[order.id] = order

class FixedDiscountCalculator(DiscountCalculator):
    def __init__(self, discount: Decimal):
        self._discount = discount

    def calculate(self, order: Order) -> Decimal:
        return self._discount

# Test
async def test_price_order_applies_discount():
    order = Order(id="123", items=[LineItem(sku="A", quantity=2, unit_price=Decimal("50"))])
    repo = InMemoryOrderRepository({"123": order})
    discount_calc = FixedDiscountCalculator(Decimal("10"))
    service = OrderPricingService(repo, discount_calc)

    result = await service.price_order("123")

    assert result.subtotal == Decimal("100")
    assert result.discount == Decimal("10")
    assert result.total == Decimal("90")
```

---

### Example 2: Testing Async Event Handler

```python
from collections.abc import Callable, Awaitable

# Port for event publishing
class EventPublisher(ABC):
    @abstractmethod
    async def publish(self, event: "DomainEvent") -> None: ...

# Testable handler
class OrderCompletedHandler:
    def __init__(self, repo: OrderRepository, publisher: EventPublisher):
        self._repo = repo
        self._publisher = publisher

    async def handle(self, event: "OrderCompletedEvent") -> None:
        order = await self._repo.get(event.order_id)
        if order and order.total > Decimal("1000"):
            await self._publisher.publish(
                HighValueOrderEvent(order_id=order.id, total=order.total)
            )

# Test fake that captures events
class CapturingEventPublisher(EventPublisher):
    def __init__(self):
        self.events: list[DomainEvent] = []

    async def publish(self, event: DomainEvent) -> None:
        self.events.append(event)

# Test
async def test_publishes_high_value_event_for_large_orders():
    order = Order(id="123", total=Decimal("1500"))
    repo = InMemoryOrderRepository({"123": order})
    publisher = CapturingEventPublisher()
    handler = OrderCompletedHandler(repo, publisher)

    await handler.handle(OrderCompletedEvent(order_id="123"))

    assert len(publisher.events) == 1
    assert isinstance(publisher.events[0], HighValueOrderEvent)
    assert publisher.events[0].total == Decimal("1500")
```

---

## Testability Checklist

Before finalizing any design, verify:

- [ ] All dependencies are injected via constructor
- [ ] Each class has ≤5 constructor parameters
- [ ] No `datetime.now()`, `random()`, or `uuid4()` called directly
- [ ] I/O operations are behind abstractions (protocols/ABCs)
- [ ] Pure functions are separated from effectful operations
- [ ] No global mutable state
- [ ] No static methods with side effects
- [ ] Constructors perform only assignment (no logic/I/O)
- [ ] Test doubles can be created without complex setup
- [ ] Behavior is observable through return values or explicit outputs

---

## Related References

- **[modularity.md](modularity.md)**: Loose coupling enables testability
- **[coherence.md](coherence.md)**: High cohesion reduces test complexity
- **[ddd.md](ddd.md)**: Bounded contexts isolate test scope
- **[observability.md](observability.md)**: Observable code is testable code
