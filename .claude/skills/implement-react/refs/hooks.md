# Hooks Reference

> Custom hooks, effect patterns, and avoiding common pitfalls.

---

## Rules of Hooks

1. **Only call at top level** — never inside loops, conditions, or nested functions
2. **Only call from React functions** — components or custom hooks
3. **Custom hooks must start with `use`** followed by capital letter

---

## Effect Patterns

### Cleanup Pattern

```tsx
// ✅ Always cleanup subscriptions, timers, event listeners
useEffect(() => {
  const controller = new AbortController();

  fetchData(url, { signal: controller.signal })
    .then(setData)
    .catch(err => {
      if (!controller.signal.aborted) setError(err);
    });

  return () => controller.abort();  // Cleanup
}, [url]);
```

### Event Listener Hook

```tsx
function useEventListener<K extends keyof WindowEventMap>(
  eventName: K,
  handler: (event: WindowEventMap[K]) => void,
  element: HTMLElement | Window = window
) {
  // Keep handler in ref to avoid effect re-runs
  const savedHandler = useRef(handler);

  useLayoutEffect(() => {
    savedHandler.current = handler;
  }, [handler]);

  useEffect(() => {
    const listener = (event: WindowEventMap[K]) => savedHandler.current(event);
    element.addEventListener(eventName, listener);
    return () => element.removeEventListener(eventName, listener);
  }, [eventName, element]);
}
```

### Debounced Value Hook

```tsx
function useDebouncedValue<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Usage
const [query, setQuery] = useState('');
const debouncedQuery = useDebouncedValue(query, 300);

const { data } = useQuery({
  queryKey: ['search', debouncedQuery],
  queryFn: () => search(debouncedQuery),
  enabled: debouncedQuery.length > 2,
});
```

### Previous Value Hook

```tsx
function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T>();

  useEffect(() => {
    ref.current = value;
  }, [value]);

  return ref.current;
}

// Usage
function Counter({ count }: { count: number }) {
  const prevCount = usePrevious(count);
  return <span>Current: {count}, Previous: {prevCount ?? 'N/A'}</span>;
}
```

### Toggle Hook

```tsx
function useToggle(initialValue = false) {
  const [value, setValue] = useState(initialValue);
  const toggle = useCallback(() => setValue(v => !v), []);
  return [value, toggle, setValue] as const;
}

// Usage
const [isOpen, toggleOpen, setIsOpen] = useToggle();
```

---

## Stale Closure Problem

The #1 source of React bugs. Occurs when callbacks capture outdated values.

### ❌ Problem: Stale Value in Interval

```tsx
function Counter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      console.log(count);        // Always logs initial value (0)
      setCount(count + 1);       // Always sets to 1
    }, 1000);
    return () => clearInterval(id);
  }, []);  // Empty deps = count captured at 0

  return <span>{count}</span>;  // Shows 1 forever
}
```

### ✅ Solution 1: Functional Update

```tsx
useEffect(() => {
  const id = setInterval(() => {
    setCount(c => c + 1);  // Functional update - always has latest
  }, 1000);
  return () => clearInterval(id);
}, []);
```

### ✅ Solution 2: Ref for Latest Value

```tsx
function useLatest<T>(value: T) {
  const ref = useRef(value);
  ref.current = value;
  return ref;
}

function Counter() {
  const [count, setCount] = useState(0);
  const countRef = useLatest(count);

  useEffect(() => {
    const id = setInterval(() => {
      console.log(countRef.current);  // Always latest
    }, 1000);
    return () => clearInterval(id);
  }, []);
}
```

---

## Dependency Array Patterns

### ✅ Include All Dependencies

```tsx
// ✅ Correct
useEffect(() => {
  fetchData(userId, filter);
}, [userId, filter]);  // All used values listed
```

### ❌ Object/Array Dependencies Trap

```tsx
// ❌ Infinite loop - new object reference each render
function Component({ userId }: Props) {
  const options = { userId, limit: 10 };  // New object every render!

  useEffect(() => {
    fetchData(options);
  }, [options]);  // Never stable
}

// ✅ Solution 1: Memoize
const options = useMemo(() => ({ userId, limit: 10 }), [userId]);

// ✅ Solution 2: Use primitives directly
useEffect(() => {
  fetchData({ userId, limit: 10 });
}, [userId]);  // Only primitive in deps
```

### Never Lie About Dependencies

```tsx
// ❌ Never suppress warnings like this
useEffect(() => {
  doSomething(value);
}, []);  // eslint-disable-line react-hooks/exhaustive-deps

// ✅ If you truly don't want re-runs, use ref
const valueRef = useRef(value);
valueRef.current = value;

useEffect(() => {
  doSomething(valueRef.current);
}, []);  // Now it's honest
```

---

## Derived State: Don't Use Effects

### ❌ Anti-Pattern: useEffect for Derived State

```tsx
// ❌ Wrong: Unnecessary effect, double render
const [items, setItems] = useState<Item[]>([]);
const [filteredItems, setFilteredItems] = useState<Item[]>([]);

useEffect(() => {
  setFilteredItems(items.filter(i => i.active));
}, [items]);
```

### ✅ Compute During Render

```tsx
// ✅ Correct: Compute inline or with useMemo
const [items, setItems] = useState<Item[]>([]);
const filteredItems = useMemo(
  () => items.filter(i => i.active),
  [items]
);

// Or for simple derivations, just compute inline
const isEmpty = items.length === 0;
const total = items.reduce((sum, i) => sum + i.price, 0);
```

---

## Async in useEffect

### ❌ Wrong: Async Function Directly

```tsx
// ❌ Effects can't be async
useEffect(async () => {  // Returns Promise, not cleanup
  const data = await fetchData();
  setData(data);
}, []);
```

### ✅ Correct: IIFE or Separate Function

```tsx
// ✅ Option 1: IIFE with AbortController
useEffect(() => {
  const controller = new AbortController();

  (async () => {
    try {
      const data = await fetchData({ signal: controller.signal });
      if (!controller.signal.aborted) setData(data);
    } catch (err) {
      if (!controller.signal.aborted) setError(err);
    }
  })();

  return () => controller.abort();
}, []);

// ✅ Option 2: Named function
useEffect(() => {
  let cancelled = false;

  async function load() {
    const data = await fetchData();
    if (!cancelled) setData(data);
  }

  load();
  return () => { cancelled = true; };
}, []);
```

---

## Custom Hook Best Practices

### Return Tuple with `as const`

```tsx
// ✅ Tuple return with const assertion
function useToggle(initial = false) {
  const [value, setValue] = useState(initial);
  const toggle = useCallback(() => setValue(v => !v), []);
  return [value, toggle, setValue] as const;
}

// Allows destructuring with proper types
const [isOpen, toggleOpen, setIsOpen] = useToggle();
```

### Return Object for Many Values

```tsx
// ✅ Object return for 4+ values
function useForm<T>(initialValues: T) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});

  return {
    values,
    errors,
    setField: (name: keyof T, value: T[keyof T]) => { /* ... */ },
    validate: () => { /* ... */ },
    reset: () => setValues(initialValues),
  };
}
```

### Stable References

```tsx
// ✅ Memoize callbacks returned from hooks
function useApi() {
  const fetch = useCallback(async (url: string) => {
    // ...
  }, []);  // Stable reference

  return { fetch };
}
```
