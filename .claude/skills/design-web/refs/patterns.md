# Component Composition Patterns Reference

> Extended patterns and decision framework for component architecture design.

---

## Pattern Decision Matrix

| Scenario | Pattern | Example |
|----------|---------|---------|
| Related UI with shared implicit state | Compound Components | Tabs, Select, Accordion |
| Flexible content injection | Render Props / Children | DataFetcher, List |
| Component that wraps multiple element types | Polymorphic | Button as link or button |
| Consistent interface, different implementations | Adapter | PaymentForm (Stripe/PayPal) |
| Cross-cutting UI concerns | Provider Pattern | Theme, Auth, Toast |

---

## Compound Components

**Use when:** Parent and children share state implicitly without prop drilling.

**Design checklist:**




- [ ] Context created with descriptive name
- [ ] Hook throws if used outside provider
- [ ] Static sub-components attached to parent
- [ ] Each sub-component has single responsibility

**Interface sketch:**
```typescript
interface TabsContextValue {
  activeTab: string;
  setActiveTab: (value: string) => void;
}

interface TabsProps {
  defaultValue: string;
  children: ReactNode;
}

interface TabProps {
  value: string;
  children: ReactNode;
}

interface TabPanelProps {
  value: string;
  children: ReactNode;
}

// Composition: Tabs.Tab, Tabs.Panel

```



**Anti-patterns:**

- Sub-component works without parent (design bug)

- Missing displayName for DevTools

---


## Polymorphic Components


**Use when:** Same component renders as different HTML elements or other components.


**Design checklist:**

- [ ] Default element type specified
- [ ] Props extend correct element type based on `as`
- [ ] Type inference works for passed component

**Interface sketch:**
```typescript

type PolymorphicRef<C extends ElementType> =
  ComponentPropsWithRef<C>['ref'];


type PolymorphicProps<C extends ElementType, Props = {}> =
  Props & { as?: C } & Omit<ComponentPropsWithoutRef<C>, keyof Props | 'as'>;


interface ButtonOwnProps {
  variant?: 'primary' | 'secondary';
  size?: 'sm' | 'md' | 'lg';

}

// Button<'a'> gets href, Button<'button'> gets onClick

```

**Anti-patterns:**


- `as` prop accepts arbitrary strings
- Props not forwarded to underlying element
- ref forwarding broken


---

## Container/Presenter Split


**Use when:** Data fetching logic should be separate from rendering logic.

**Design checklist:**

- [ ] Container handles: data fetching, error handling, loading states
- [ ] Presenter handles: pure rendering, props-only, no hooks
- [ ] Presenter is testable without mocking data layer


**Interface sketch:**
```typescript
// Presenter - pure, testable
interface UserListViewProps {
  users: User[];
  onSelect: (id: string) => void;
  selectedId: string | null;
}


// Container - orchestrates
interface UserListContainerProps {
  departmentId: string;
}
// Container internally uses useQuery, handles loading/error

// Renders UserListView with resolved data
```


---


## Render Props / Children as Function


**Use when:** Consumer needs control over what renders, but component provides data/logic.

**Design checklist:**


- [ ] Component handles loading/error internally or exposes state

- [ ] Type safety for render prop arguments

**Interface sketch:**
```typescript
interface RenderBag<T> {
  data: T | null;

  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}


interface DataFetcherProps<T> {

  url: string;
  children: (bag: RenderBag<T>) => ReactNode;
}
```



**Modern alternative:** Custom hooks often replace render props, but render props still useful for:

- Cross-framework compatibility
- When hook rules are limiting
- Library APIs



---

## Slot-Based Composition

**Use when:** Parent needs to place children in specific locations.

**Design checklist:**


- [ ] Named slots for each insertion point
- [ ] Default content for optional slots
- [ ] Type safety for slot content

**Interface sketch:**
```typescript
interface CardProps {

  header?: ReactNode;
  children: ReactNode;  // Main content
  footer?: ReactNode;
  actions?: ReactNode;
}

// Usage:
// <Card

//   header={<CardTitle>...</CardTitle>}
//   footer={<CardFooter>...</CardFooter>}
// >
//   Content here
// </Card>
```

**When to use slots vs compound components:**

- **Slots**: Fixed structure, optional sections
- **Compound**: Flexible structure, implicit state sharing

---

## Props Interface Patterns

### Discriminated Unions

```typescript
// Loading state pattern
type AsyncProps<T> =
  | { status: 'loading' }
  | { status: 'error'; error: Error; onRetry: () => void }
  | { status: 'success'; data: T };

// Variant pattern
type AlertProps =
  | { variant: 'info'; dismissible?: boolean }
  | { variant: 'error'; error: Error; onRetry?: () => void }
  | { variant: 'success'; autoHide?: boolean };
```

### Conditional Props

```typescript
// Props that depend on other props
interface InputProps {
  type: 'text' | 'number' | 'email';
}

interface NumberInputProps extends InputProps {
  type: 'number';
  min?: number;
  max?: number;
  step?: number;
}

interface TextInputProps extends InputProps {
  type: 'text' | 'email';
  maxLength?: number;
  pattern?: string;
}

type FullInputProps = NumberInputProps | TextInputProps;
```

### Callback Props

```typescript
// Include relevant context in callbacks
interface ListItemProps {
  item: Item;
  // ❌ onSelect: () => void;          // Caller doesn't know which item
  // ✅ onSelect: (item: Item) => void; // Caller has context
}

// For events, include both event and data
interface RowProps {
  onRowClick: (row: Row, event: React.MouseEvent) => void;
}
```

---

## Common Design Mistakes

### Mistake: Props that require implementation knowledge

```typescript
// ❌ Parent needs to know internal class names
interface ModalProps {
  contentClassName?: string;
  overlayClassName?: string;
  headerClassName?: string;
}

// ✅ Semantic props that map to styles internally
interface ModalProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'fullscreen';
}
```

### Mistake: Boolean props for mutually exclusive states

```typescript
// ❌ Impossible state: isLoading && isSuccess
interface Props {
  isLoading?: boolean;
  isSuccess?: boolean;
  isError?: boolean;
}

// ✅ Discriminated union
interface Props {
  status: 'idle' | 'loading' | 'success' | 'error';
}
```

### Mistake: Over-generic props

```typescript
// ❌ Too flexible, loses type safety
interface TableProps {
  data: any[];
  columns: any[];
}

// ✅ Generic with constraints
interface TableProps<T extends Record<string, unknown>> {
  data: T[];
  columns: Column<T>[];
}
```
