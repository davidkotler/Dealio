# TypeScript Patterns Reference

> Advanced TypeScript patterns for type-safe React components.

---

## Prop Interface Patterns

### Extending Native Elements

```tsx
// ✅ Correct: Extend without ref
interface ButtonProps extends ComponentPropsWithoutRef<'button'> {
  variant?: 'primary' | 'secondary';
  isLoading?: boolean;
}

// ✅ With ref forwarding
interface InputProps extends ComponentPropsWithRef<'input'> {
  label: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, ...props }, ref) => (
    <div>
      <label>{label}</label>
      <input ref={ref} {...props} />
      {error && <span className="error">{error}</span>}
    </div>
  )
);
```

### Discriminated Unions

```tsx
// Variant-based discrimination
type AlertProps =
  | { variant: 'info'; dismissible?: boolean }
  | { variant: 'error'; error: Error; onRetry?: () => void }
  | { variant: 'success'; autoHide?: boolean };

// Status-based discrimination (prefer over booleans)
type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };
```

### Polymorphic Components

```tsx
type AsProp<C extends ElementType> = { as?: C };

type PolymorphicProps<C extends ElementType, Props = {}> =
  Props &
  AsProp<C> &
  Omit<ComponentPropsWithoutRef<C>, keyof Props | 'as'>;

interface BoxOwnProps {
  padding?: 'sm' | 'md' | 'lg';
}

function Box<C extends ElementType = 'div'>({
  as,
  padding = 'md',
  ...props
}: PolymorphicProps<C, BoxOwnProps>) {
  const Component = as || 'div';
  return <Component className={`p-${padding}`} {...props} />;
}

// Usage
<Box>Default div</Box>
<Box as="section">Section element</Box>
<Box as={Link} href="/home">Router Link</Box>
```

---

## Generic Components

### List with Type Inference

```tsx
interface HasId {
  id: string | number;
}

interface ListProps<T extends HasId> {
  items: T[];
  renderItem: (item: T) => ReactNode;
  keyExtractor?: (item: T) => string;
}

function List<T extends HasId>({
  items,
  renderItem,
  keyExtractor = (item) => String(item.id),
}: ListProps<T>) {
  return (
    <ul>
      {items.map((item) => (
        <li key={keyExtractor(item)}>{renderItem(item)}</li>
      ))}
    </ul>
  );
}

// Type inference works automatically
<List
  items={users}
  renderItem={(user) => <span>{user.name}</span>}
/>
```

### Controlled/Uncontrolled Pattern

```tsx
interface ControlledProps<T> {
  value: T;
  onChange: (value: T) => void;
  defaultValue?: never;
}

interface UncontrolledProps<T> {
  value?: never;
  onChange?: (value: T) => void;
  defaultValue?: T;
}

type InputValueProps<T> = ControlledProps<T> | UncontrolledProps<T>;
```

---

## Type Guards

```tsx
// Runtime type narrowing
function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    'message' in error
  );
}

// Usage
catch (error) {
  if (isApiError(error)) {
    showToast(error.message);  // error is ApiError here
  }
}
```

---

## Branded Types

```tsx
// Prevent mixing up primitive IDs
type Brand<K, T> = K & { __brand: T };

type UserId = Brand<string, 'UserId'>;
type OrderId = Brand<string, 'OrderId'>;

function createUserId(id: string): UserId {
  return id as UserId;
}

function getUser(id: UserId): Promise<User> { /* ... */ }

const userId = createUserId('123');
const orderId = createOrderId('456');

getUser(userId);   // ✅ Works
getUser(orderId);  // ❌ Type error
```

---

## Event Handler Typing

```tsx
// Form submission with typed elements
interface FormElements {
  email: HTMLInputElement;
  password: HTMLInputElement;
}

function LoginForm() {
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const elements = e.currentTarget.elements as unknown as FormElements;
    login({
      email: elements.email.value,
      password: elements.password.value,
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      <input name="email" type="email" />
      <input name="password" type="password" />
      <button type="submit">Login</button>
    </form>
  );
}
```

---

## Utility Types for React

```tsx
// Extract props from component
type ButtonProps = ComponentProps<typeof Button>;

// Make all props optional except specified
type PartialExcept<T, K extends keyof T> = Partial<Omit<T, K>> & Pick<T, K>;

// Require at least one of the specified props
type RequireAtLeastOne<T, Keys extends keyof T = keyof T> =
  Pick<T, Exclude<keyof T, Keys>> &
  { [K in Keys]-?: Required<Pick<T, K>> & Partial<Pick<T, Exclude<Keys, K>>> }[Keys];
```

---

## tsconfig.json Essentials

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

---

## Anti-Patterns

| Pattern | Problem | Solution |
|---------|---------|----------|
| `useState<User>({} as User)` | Runtime crash on property access | `useState<User \| null>(null)` |
| `props: any` | No type safety | Define explicit interface |
| `// @ts-ignore` | Hides real bugs | Fix the type error |
| `as Type` assertion | Bypasses type system | Use type guards |
| `Function` type | No parameter/return info | `(arg: Type) => ReturnType` |
