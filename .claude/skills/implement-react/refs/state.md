# State Management Reference

> Decision framework for state classification and tool selection.

---

## State Classification Framework

### Step 1: Identify Source

| Source | Classification | Tool |
|--------|----------------|------|
| API/Database | **Server State** | TanStack Query |
| User interaction | **Client State** | useState/Zustand |
| URL/Route | **URL State** | searchParams |
| Form input | **Form State** | React Hook Form |

### Step 2: Determine Scope

| Scope | Strategy |
|-------|----------|
| Single component | `useState` |
| Parent + children | Lift state to parent |
| Sibling components | Lift to common ancestor |
| Distant components | Context or Zustand |
| Entire app | Zustand |

---

## Server State (TanStack Query)

### Query Key Factory Pattern

```tsx
// Create once per feature, use everywhere
export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (filters: UserFilters) => [...userKeys.lists(), filters] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
};

// Consistent invalidation
queryClient.invalidateQueries({ queryKey: userKeys.all });      // All
queryClient.invalidateQueries({ queryKey: userKeys.lists() });  // Lists only
queryClient.invalidateQueries({ queryKey: userKeys.detail(id) }); // Specific
```

### Query Options Pattern (v5)

```tsx
// Define once, reuse everywhere
export const userDetailOptions = (id: string) => queryOptions({
  queryKey: userKeys.detail(id),
  queryFn: () => fetchUser(id),
  staleTime: 5 * 60 * 1000,
});

// In component
const { data } = useQuery(userDetailOptions(userId));

// In prefetch
await queryClient.prefetchQuery(userDetailOptions(userId));

// In cache read
const cached = queryClient.getQueryData(userDetailOptions(userId).queryKey);
```

### Stale Time Strategy

| Data Type | Stale Time | Rationale |
|-----------|------------|-----------|
| User profile | 5-15 min | Changes rarely |
| Dashboard metrics | 30s-2min | Should feel "live" |
| Static config | 30+ min | Almost never changes |
| Real-time data | 0 | Always refetch |
| Search results | 1 min | Balance freshness + perf |

### Optimistic Updates

```tsx
const mutation = useMutation({
  mutationFn: updateTodo,
  onMutate: async (newTodo) => {
    // Cancel outgoing queries
    await queryClient.cancelQueries({ queryKey: todoKeys.detail(newTodo.id) });

    // Snapshot previous value
    const previous = queryClient.getQueryData(todoKeys.detail(newTodo.id));

    // Optimistically update
    queryClient.setQueryData(todoKeys.detail(newTodo.id), newTodo);

    // Return rollback context
    return { previous };
  },
  onError: (err, newTodo, context) => {
    // Rollback on error
    queryClient.setQueryData(todoKeys.detail(newTodo.id), context?.previous);
  },
  onSettled: () => {
    // Always refetch after mutation settles
    queryClient.invalidateQueries({ queryKey: todoKeys.all });
  },
});
```

---

## Client State

### useState vs useReducer

| Scenario | Choice |
|----------|--------|
| Single primitive value | `useState` |
| Multiple related values | `useState` (object) or `useReducer` |
| Complex transitions | `useReducer` |
| Next state depends on previous | `useReducer` |
| State machine behavior | `useReducer` |

### useReducer with TypeScript

```tsx
type State = {
  count: number;
  step: number;
};

type Action =
  | { type: 'INCREMENT' }
  | { type: 'DECREMENT' }
  | { type: 'SET_STEP'; payload: number }
  | { type: 'RESET' };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'INCREMENT':
      return { ...state, count: state.count + state.step };
    case 'DECREMENT':
      return { ...state, count: state.count - state.step };
    case 'SET_STEP':
      return { ...state, step: action.payload };
    case 'RESET':
      return { count: 0, step: 1 };
  }
}
```

### Zustand Store Pattern

```tsx
interface AuthStore {
  // State
  user: User | null;
  token: string | null;

  // Actions (collocated with state)
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  devtools(
    persist(
      (set) => ({
        user: null,
        token: null,

        login: async (credentials) => {
          const { user, token } = await authApi.login(credentials);
          set({ user, token });
        },

        logout: () => set({ user: null, token: null }),
      }),
      { name: 'auth-storage' }
    )
  )
);

// ✅ Export granular selectors (not full store)
export const useUser = () => useAuthStore((s) => s.user);
export const useIsAuthenticated = () => useAuthStore((s) => s.user !== null);
```

### Context vs Zustand

| Criteria | Context | Zustand |
|----------|---------|---------|
| Re-renders | All consumers | Only selected slice |
| DevTools | No | Yes |
| Persistence | Manual | Built-in middleware |
| Server Components | Works | Needs client boundary |
| Complexity | Low | Medium |

**Decision:** Context for low-frequency (theme, auth status). Zustand for high-frequency (UI state, filters).

---

## URL State

### What Belongs in URL

| State Type | URL? | Rationale |
|------------|------|-----------|
| Filters/sort | ✅ | Shareable, bookmarkable |
| Pagination | ✅ | Browser back works |
| Selected tab | ✅ | Direct link to tab |
| Modal open | ❌ | Not shareable |
| Form values | ❌ | Transient, sensitive |
| Expanded rows | ❌ | UI state |

### URL + React Query Integration

```tsx
function UserList() {
  const searchParams = useSearchParams();
  const page = Number(searchParams.get('page')) || 1;
  const sort = searchParams.get('sort') || 'name';

  // URL params drive query key → automatic refetch on URL change
  const { data } = useQuery({
    queryKey: userKeys.list({ page, sort }),
    queryFn: () => fetchUsers({ page, sort }),
  });

  return <UserTable data={data} />;
}
```

---

## Form State

### Complexity Matrix

| Form Type | Strategy |
|-----------|----------|
| Single field | Controlled `useState` |
| 2-3 fields, no validation | Uncontrolled with refs |
| Multiple fields + validation | React Hook Form |
| Complex conditional logic | React Hook Form + custom hooks |
| Wizard/multi-step | React Hook Form + form state machine |

### React Hook Form + Zod

```tsx
const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Min 8 characters'),
});

type FormData = z.infer<typeof schema>;

function LoginForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = (data: FormData) => login(data);

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}

      <input type="password" {...register('password')} />
      {errors.password && <span>{errors.password.message}</span>}

      <button type="submit">Login</button>
    </form>
  );
}
```

---

## Anti-Patterns

### ❌ Server Data in Client Store

```tsx
// ❌ Wrong
interface AppStore {
  users: User[];  // Server data in Zustand!
  loadUsers: () => void;
}

// ✅ Correct
// users → TanStack Query
// AppStore → only UI preferences
```

### ❌ Derived State Stored

```tsx
// ❌ Wrong
const [items, setItems] = useState<Item[]>([]);
const [filteredItems, setFilteredItems] = useState<Item[]>([]);  // Derived!

useEffect(() => {
  setFilteredItems(items.filter(i => i.active));
}, [items]);

// ✅ Correct
const [items, setItems] = useState<Item[]>([]);
const filteredItems = useMemo(() => items.filter(i => i.active), [items]);
```

### ❌ State Located Too High

```tsx
// ❌ Wrong: modal state in App when only one component uses it
interface AppState {
  isModalOpen: boolean;
}

// ✅ Correct: state colocated with Modal component
function FeatureWithModal() {
  const [isOpen, setIsOpen] = useState(false);
  return <Modal open={isOpen} onClose={() => setIsOpen(false)} />;
}
```
