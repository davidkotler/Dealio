# Relationships Reference

> Guidance on modeling entity relationships: cardinality, optionality, foreign keys, and join strategies.

---

## Quick Reference

| Relationship | Implementation | Use When |
|--------------|----------------|----------|
| **1:1 Required** | FK with UNIQUE + NOT NULL on child | Entity split for performance/security |
| **1:1 Optional** | FK with UNIQUE, nullable | Extension data that may not exist |
| **1:N Required** | FK NOT NULL on child | Every child must have parent |
| **1:N Optional** | FK nullable on child | Child can exist independently |
| **M:N** | Bridge table with composite PK | Entities have multiple associations |
| **M:N with attributes** | Bridge table with own columns | Relationship itself carries data |

---

## Relationship Types

### One-to-One (1:1)

One entity instance relates to exactly one instance of another.

```sql
-- Pattern: User ←→ UserProfile (1:1 required)
CREATE TABLE users (
    id VARCHAR(26) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE user_profiles (
    user_id VARCHAR(26) PRIMARY KEY,  -- PK = FK (guarantees 1:1)
    bio TEXT,
    avatar_url VARCHAR(500),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**When to use 1:1:**






- Separate frequently-accessed from rarely-accessed columns
- Isolate sensitive data (PII in separate table)
- Enforce optional extensions (not every user has a profile)

---

### One-to-Many (1:N)

One parent entity relates to multiple child entities.

```sql
-- Pattern: Customer → Orders (1:N)
CREATE TABLE customers (
    id VARCHAR(26) PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE orders (
    id VARCHAR(26) PRIMARY KEY,
    customer_id VARCHAR(26) NOT NULL,  -- NOT NULL = required parent
    total DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);
-- Index on FK for join performance
CREATE INDEX idx_orders_customer ON orders(customer_id);
```

---

### Many-to-Many (M:N)

Multiple entities on both sides relate to each other.

```sql
-- Pattern: Students ↔ Courses (M:N via enrollment)
CREATE TABLE students (
    id VARCHAR(26) PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE courses (
    id VARCHAR(26) PRIMARY KEY,
    title VARCHAR(200) NOT NULL
);

CREATE TABLE enrollments (
    student_id VARCHAR(26) NOT NULL,
    course_id VARCHAR(26) NOT NULL,
    enrolled_at TIMESTAMP NOT NULL DEFAULT NOW(),
    grade CHAR(2),  -- Relationship attribute
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
);
```

---

## Must Rules

### Cardinality

- **MUST** define cardinality explicitly for every relationship (1:1, 1:N, M:N)
- **MUST** define optionality: can child exist without parent? Can relationship be null?
- **MUST** use NOT NULL on FK when parent is required
- **MUST** index all foreign key columns (required for JOIN performance)
- **MUST** define ON DELETE behavior explicitly (CASCADE, SET NULL, RESTRICT)

### Foreign Keys

- **MUST** reference primary keys, not other columns
- **MUST** match FK data type exactly with referenced PK
- **MUST** name FKs consistently: `{referenced_table_singular}_id`
- **MUST** create FK constraint at schema level, not just application

### Bridge Tables

- **MUST** use composite primary key `(entity1_id, entity2_id)` for simple M:N
- **MUST** add surrogate key only when bridge row is referenced elsewhere
- **MUST** include audit columns if relationship has lifecycle significance
- **MUST** index both FK columns individually for bidirectional queries

---

## Never Rules

### Schema Design

- **NEVER** use arrays/JSON to represent M:N (violates 1NF, can't enforce FK)
- **NEVER** embed FK in comma-separated string
- **NEVER** create circular FK dependencies (A→B→C→A)
- **NEVER** reference non-PK columns with FK constraints
- **NEVER** use different data types for FK and referenced PK

### Relationship Modeling

- **NEVER** model 1:N as 1:1 by adding multiple FK columns (customer_1_id, customer_2_id)
- **NEVER** skip the bridge table for M:N to "simplify"
- **NEVER** store parent attributes on child to avoid JOIN
- **NEVER** create bidirectional FKs (A→B AND B→A) for same relationship
- **NEVER** allow orphaned children without explicit business reason

### Performance

- **NEVER** JOIN without index on FK column
- **NEVER** CASCADE DELETE on high-volume relationships without analysis
- **NEVER** lazy-load relationships in loops (N+1 query)

---

## When → Then Decisions

### Cardinality Selection

| When | Then | Example |
|------|------|---------|
| Entity cannot exist without related entity | Required (NOT NULL FK) | Order requires Customer |
| Entity can exist independently | Optional (nullable FK) | Comment can lose its Author |
| Both entities exist independently, related by event | M:N with bridge | User ↔ Role (many users, many roles) |
| One entity extends another | 1:1 with shared PK | User ↔ UserSettings |
| Child has single parent, always | 1:N with NOT NULL FK | OrderItem → Order |

### Foreign Key Location

| When | Then |
|------|------|
| 1:1 relationship | FK on the dependent/optional side |
| 1:N relationship | FK on the "many" side (child) |
| M:N relationship | FKs in bridge table |
| Self-referential | FK and PK on same table |
| Polymorphic | FK + type discriminator column |

### ON DELETE Behavior

| When | Then |
|------|------|
| Child meaningless without parent | CASCADE |
| Child has independent value | RESTRICT or SET NULL |
| Audit/history must be preserved | SET NULL or soft delete |
| Parent deletion is rare/admin-only | RESTRICT (fail loudly) |
| High-volume child table | RESTRICT + batch delete job |

### Index Strategy

| When | Then |
|------|------|
| FK used in JOIN | Index FK column |
| FK used in WHERE clause | Index FK column |
| Bridge table queried from both directions | Index both FK columns individually |
| Composite FK | Index matches query pattern (column order matters) |
| FK rarely queried | Still index (for FK constraint checks on parent delete) |

---

## Patterns

### ✅ Self-Referential Relationship

Entity references itself (hierarchies, graphs).

```sql
-- Pattern: Employee reports to Manager (1:N self-ref)
CREATE TABLE employees (
    id VARCHAR(26) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    manager_id VARCHAR(26),  -- Nullable: CEO has no manager
    FOREIGN KEY (manager_id) REFERENCES employees(id)
);

-- Query: Get employee with manager name
SELECT e.name, m.name AS manager_name
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.id;
```

---

### ✅ Polymorphic Relationship

Child relates to one of multiple parent types.

```sql
-- Pattern: Comments on multiple content types
CREATE TABLE comments (
    id VARCHAR(26) PRIMARY KEY,
    body TEXT NOT NULL,
    -- Polymorphic FK
    commentable_type VARCHAR(50) NOT NULL,  -- 'post', 'video', 'product'
    commentable_id VARCHAR(26) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for polymorphic lookup
CREATE INDEX idx_comments_target ON comments(commentable_type, commentable_id);

-- Query: Get comments for a post
SELECT * FROM comments
WHERE commentable_type = 'post' AND commentable_id = ?;
```

**Trade-off:** No FK constraint enforcement. Consider separate tables if referential integrity is critical.

---

### ✅ Exclusive Arc (XOR Relationship)

Entity relates to exactly one of multiple entities.

```sql
-- Pattern: Payment belongs to either Order OR Subscription (not both)
CREATE TABLE payments (
    id VARCHAR(26) PRIMARY KEY,
    amount DECIMAL(10,2) NOT NULL,
    order_id VARCHAR(26),
    subscription_id VARCHAR(26),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id),
    -- Constraint: exactly one must be set
    CONSTRAINT chk_exclusive_parent CHECK (
        (order_id IS NOT NULL AND subscription_id IS NULL) OR
        (order_id IS NULL AND subscription_id IS NOT NULL)
    )
);
```

---

### ✅ Bridge Table with Attributes

Relationship carries its own data.

```sql
-- Pattern: User ↔ Project with role and timestamps
CREATE TABLE project_members (
    project_id VARCHAR(26) NOT NULL,
    user_id VARCHAR(26) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',  -- Relationship attribute
    joined_at TIMESTAMP NOT NULL DEFAULT NOW(),   -- Relationship attribute
    invited_by VARCHAR(26),                        -- Relationship attribute
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (invited_by) REFERENCES users(id) ON DELETE SET NULL
);
```

---

### ✅ Temporal Relationship (History)

Track relationship changes over time.

```sql
-- Pattern: Employee ↔ Department with history
CREATE TABLE employee_departments (
    id VARCHAR(26) PRIMARY KEY,  -- Surrogate key needed (same pair can repeat)
    employee_id VARCHAR(26) NOT NULL,
    department_id VARCHAR(26) NOT NULL,
    started_at DATE NOT NULL,
    ended_at DATE,  -- NULL = current
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (department_id) REFERENCES departments(id),
    -- Constraint: no overlapping periods
    CONSTRAINT chk_valid_period CHECK (ended_at IS NULL OR ended_at > started_at)
);

-- Query: Current department
SELECT d.* FROM departments d
JOIN employee_departments ed ON d.id = ed.department_id
WHERE ed.employee_id = ? AND ed.ended_at IS NULL;
```

---

### ✅ Ordered Relationship

Maintain sequence within relationship.

```sql
-- Pattern: Playlist → Songs with order
CREATE TABLE playlist_songs (
    playlist_id VARCHAR(26) NOT NULL,
    song_id VARCHAR(26) NOT NULL,
    position INT NOT NULL,  -- Order within playlist
    added_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (playlist_id, song_id),
    UNIQUE (playlist_id, position),  -- No duplicate positions
    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

-- Query: Songs in order
SELECT s.* FROM songs s
JOIN playlist_songs ps ON s.id = ps.song_id
WHERE ps.playlist_id = ?
ORDER BY ps.position;
```

---

## Anti-Patterns

### ❌ Array Instead of Bridge Table

```sql
-- WRONG: M:N via array (can't enforce FK, can't index, can't query efficiently)
CREATE TABLE users (
    id INT PRIMARY KEY,
    role_ids INT[]  -- [1, 2, 3]
);

-- RIGHT: Proper bridge table
CREATE TABLE user_roles (
    user_id INT REFERENCES users(id),
    role_id INT REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
```

---

### ❌ Hardcoded Maximum Columns

```sql
-- WRONG: Fixed number of FK columns
CREATE TABLE orders (
    id INT PRIMARY KEY,
    product_1_id INT,
    product_2_id INT,
    product_3_id INT  -- What about product 4?
);

-- RIGHT: Proper 1:N
CREATE TABLE order_items (
    order_id INT REFERENCES orders(id),
    product_id INT REFERENCES products(id),
    quantity INT NOT NULL,
    PRIMARY KEY (order_id, product_id)
);
```

---

### ❌ Bidirectional FKs

```sql
-- WRONG: Circular reference for same relationship
CREATE TABLE users (
    id INT PRIMARY KEY,
    best_friend_id INT REFERENCES users(id)
);
-- AND
ALTER TABLE users ADD best_friend_of_id INT REFERENCES users(id);
-- Creates ambiguity: which is source of truth?

-- RIGHT: Single direction with query for reverse
CREATE TABLE users (
    id INT PRIMARY KEY,
    best_friend_id INT REFERENCES users(id)
);
-- Query "who has me as best friend":
SELECT * FROM users WHERE best_friend_id = ?;
```

---

### ❌ Missing FK Index

```sql
-- WRONG: FK without index
CREATE TABLE orders (
    id INT PRIMARY KEY,
    customer_id INT REFERENCES customers(id)
    -- No index on customer_id
);
-- JOIN customers → orders scans entire orders table

-- RIGHT: Always index FK
CREATE TABLE orders (
    id INT PRIMARY KEY,
    customer_id INT REFERENCES customers(id)
);
CREATE INDEX idx_orders_customer ON orders(customer_id);
```

---

### ❌ Polymorphic Without Type Check

```sql
-- WRONG: Polymorphic FK without type column
CREATE TABLE comments (
    id INT PRIMARY KEY,
    target_id INT NOT NULL  -- Is this a post? video? product? Unknown.
);

-- RIGHT: Include type discriminator
CREATE TABLE comments (
    id INT PRIMARY KEY,
    target_type VARCHAR(20) NOT NULL,
    target_id INT NOT NULL,
    CONSTRAINT chk_valid_type CHECK (target_type IN ('post', 'video', 'product'))
);
```

---

### ❌ N+1 Query Pattern

```python
# WRONG: N+1 queries
orders = db.query("SELECT * FROM orders WHERE customer_id = ?", customer_id)
for order in orders:
    items = db.query("SELECT * FROM items WHERE order_id = ?", order.id)
    # N additional queries

# RIGHT: Single query with JOIN or batch
orders_with_items = db.query("""
    SELECT o.*, i.product_id, i.quantity
    FROM orders o
    LEFT JOIN order_items i ON o.id = i.order_id
    WHERE o.customer_id = ?
""", customer_id)
```

---

## Decision Matrix

| Scenario | Relationship Type | FK Location | ON DELETE |
|----------|-------------------|-------------|-----------|
| User has one profile | 1:1 | profile.user_id (PK=FK) | CASCADE |
| Order has many items | 1:N required | item.order_id NOT NULL | CASCADE |
| Post may have author | 1:N optional | post.author_id NULL | SET NULL |
| User has many roles | M:N | user_roles bridge | CASCADE |
| Employee → Manager | 1:N self-ref | employee.manager_id | SET NULL |
| Comment on any entity | Polymorphic | comment.{type,id} | Application-level |
| Payment → Order XOR Subscription | Exclusive arc | payment.{order_id,subscription_id} | RESTRICT |
| Tag used by many entities | M:N polymorphic | taggings bridge with type | CASCADE |

---

## Relationship Checklist

Before finalizing any relationship:

- [ ] Cardinality defined (1:1, 1:N, M:N)
- [ ] Optionality defined (required vs optional)
- [ ] FK column data type matches PK exactly
- [ ] FK has index

- [ ] ON DELETE behavior specified
- [ ] Bridge table has composite PK (for M:N)
- [ ] No circular FK dependencies
- [ ] N+1 queries avoided in access patterns
- [ ] Polymorphic relationships have type discriminator
