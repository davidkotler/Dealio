# Component Patterns Reference

> Composition patterns and decision framework for component architecture.

---

## Pattern Decision Matrix

| Scenario | Pattern | Example |
|----------|---------|---------|
| Related UI with shared implicit state | Compound Components | Tabs, Select, Accordion |
| Flexible content injection | Slots / Children | Card with header/footer |
| Component wraps multiple element types | Polymorphic | Button as link or button |
| Consumer needs render control | Render Props | DataFetcher |
| Cross-cutting UI concerns | Provider Pattern | Theme, Toast |

---

## Compound Components

**Use when:** Parent and children share state implicitly without prop drilling.

```tsx
// Context for implicit state sharing
const SelectContext = createContext<SelectContextValue | null>(null);

function useSelectContext() {
  const ctx = useContext(SelectContext);
  if (!ctx) throw new Error('Select.Option must be used within Select');
  return ctx;
}

// Parent component provides context
function Select({ children, value, onChange }: SelectProps) {
  return (
    <SelectContext.Provider value={{ value, onChange }}>
      <div role="listbox">{children}</div>
    </SelectContext.Provider>
  );
}

// Child component consumes context
function Option({ value, children }: OptionProps) {
  const { value: selected, onChange } = useSelectContext();
  return (
    <div
      role="option"
      aria-selected={selected === value}
      onClick={() => onChange(value)}
    >
      {children}
    </div>
  );
}

// Attach sub-components for discoverable API
Select.Option = Option;

// Usage: declarative, flexible
<Select value={selected} onChange={setSelected}>
  <Select.Option value="a">Option A</Select.Option>
  <Select.Option value="b">Option B</Select.Option>
</Select>
```

**Checklist:**







- [ ] Context throws helpful error if used outside provider
- [ ] Sub-components attached to parent (e.g., `Tabs.Tab`)
- [ ] Context value is memoized to prevent re-renders

---

## Polymorphic Components

**Use when:** Same component renders as different HTML elements.

```tsx
type AsProp<C extends ElementType> = { as?: C };

type PolymorphicProps<C extends ElementType, Props = {}> =
  Props &
  AsProp<C> &
  Omit<ComponentPropsWithoutRef<C>, keyof Props | 'as'>;

interface ButtonOwnProps {
  variant?: 'primary' | 'secondary';
}

function Button<C extends ElementType = 'button'>({
  as,
  variant = 'primary',
  ...props
}: PolymorphicProps<C, ButtonOwnProps>) {
  const Component = as || 'button';
  return <Component className={`btn-${variant}`} {...props} />;
}

// Usage
<Button>Click me</Button>                        // renders <button>
<Button as="a" href="/home">Go home</Button>     // renders <a>
<Button as={Link} to="/dashboard">Dashboard</Button>  // renders Router Link
```

---

## Slot-Based Composition

**Use when:** Parent needs to place children in specific locations.

```tsx
interface CardProps {
  header?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

function Card({ header, children, footer }: CardProps) {
  return (
    <div className="card">
      {header && <div className="card-header">{header}</div>}
      <div className="card-body">{children}</div>
      {footer && <div className="card-footer">{footer}</div>}
    </div>
  );
}

// Usage
<Card
  header={<h2>Title</h2>}
  footer={<button>Submit</button>}

>

  Main content here

</Card>

```



**Slots vs Compound Components:**

- **Slots**: Fixed structure, optional sections
- **Compound**: Flexible structure, implicit state sharing

---

## Container/Presenter Split

**Use when:** Separating data fetching from rendering.

```tsx
// Presenter: Pure rendering, props only, easily testable
interface UserListViewProps {
  users: User[];
  onSelect: (id: string) => void;
  selectedId: string | null;
}

function UserListView({ users, onSelect, selectedId }: UserListViewProps) {
  return (
    <ul>
      {users.map(user => (
        <li
          key={user.id}
          onClick={() => onSelect(user.id)}
          aria-selected={selectedId === user.id}
        >
          {user.name}
        </li>
      ))}
    </ul>
  );
}

// Container: Orchestrates data, handles loading/error
function UserListContainer({ departmentId }: { departmentId: string }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { data, isLoading, error } = useUsers(departmentId);

  if (isLoading) return <Skeleton />;
  if (error) return <ErrorMessage error={error} />;
  if (!data?.length) return <EmptyState />;

  return (
    <UserListView
      users={data}
      onSelect={setSelectedId}
      selectedId={selectedId}
    />
  );
}
```

---

## Render Props (Modern Usage)

**Use when:** Consumer needs control over rendering, but component provides data/logic.

```tsx
interface RenderBag<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
}

interface DataFetcherProps<T> {
  url: string;
  children: (bag: RenderBag<T>) => ReactNode;
}

function DataFetcher<T>({ url, children }: DataFetcherProps<T>) {
  const { data, isLoading, error } = useFetch<T>(url);
  return <>{children({ data, isLoading, error })}</>;
}

// Usage
<DataFetcher<User[]> url="/api/users">
  {({ data, isLoading }) =>
    isLoading ? <Spinner /> : <UserList users={data ?? []} />
  }
</DataFetcher>
```

**Note:** Custom hooks often replace render props in modern React.

---

## Server/Client Component Composition

**Pattern:** Pass Server Components through Client Component children.

```tsx
// modal.tsx (Client Component)
'use client';
export function Modal({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  return isOpen && <div className="modal">{children}</div>;
}

// page.tsx (Server Component)
import { Modal } from './modal';
import { ProductDetails } from './product-details';  // Server Component

export default function Page() {
  return (
    <Modal>
      <ProductDetails />  {/* Stays a Server Component! */}
    </Modal>
  );
}
```

---

## Common Mistakes

### ❌ Nested Component Definitions

```tsx
// ❌ Bad: Child recreated every render, loses state
function Parent() {
  function Child() {
    return <div>Bad</div>;
  }
  return <Child />;
}

// ✅ Good: Defined outside
function Child() {
  return <div>Good</div>;
}

function Parent() {
  return <Child />;
}
```

### ❌ Props Requiring Implementation Knowledge

```tsx
// ❌ Bad: Leaks internal class names
interface ModalProps {
  contentClassName?: string;
  overlayClassName?: string;
}

// ✅ Good: Semantic props
interface ModalProps {
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'fullscreen';
}
```

### ❌ Boolean Props for Mutually Exclusive States

```tsx
// ❌ Bad: Impossible state possible (isLoading && isSuccess)
interface Props {
  isLoading?: boolean;
  isSuccess?: boolean;
  isError?: boolean;
}

// ✅ Good: Discriminated union
interface Props {
  status: 'idle' | 'loading' | 'success' | 'error';
}
```

### ❌ Over-Generic Props

```tsx
// ❌ Bad: Lost type safety
interface TableProps {
  data: any[];
  columns: any[];
}

// ✅ Good: Generic with constraints
interface TableProps<T extends Record<string, unknown>> {
  data: T[];
  columns: Column<T>[];
}
```

---

## Callback Props Pattern

```tsx
// ✅ Include relevant context in callbacks
interface ListItemProps {
  item: Item;
  onSelect: (item: Item) => void;  // Caller has context
}

// ❌ Bad: Caller doesn't know which item
interface ListItemProps {
  item: Item;
  onSelect: () => void;  // No context
}

// For events, include both event and data
interface RowProps {
  row: Row;
  onRowClick: (row: Row, event: React.MouseEvent) => void;
}
```
