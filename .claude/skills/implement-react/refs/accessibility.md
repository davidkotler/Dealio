# Accessibility Reference

> ARIA patterns and keyboard navigation by component type.

---

## Core Principles

1. **Semantic HTML first** — Use native elements before ARIA
2. **Keyboard accessible** — All interactions work without mouse
3. **Focus management** — Visible focus, logical order, trapped when needed
4. **Screen reader friendly** — Content announced properly
5. **No color-only information** — Use icons, text, patterns too

---

## Semantic HTML Priority

| Need | Use | Not |
|------|-----|-----|
| Clickable action | `<button>` | `<div onClick>` |
| Navigation link | `<a href>` | `<span onClick>` |
| Form input | `<input>`, `<select>` | Custom div |
| List of items | `<ul>`, `<ol>` | Nested divs |
| Table data | `<table>` | Grid of divs |
| Section heading | `<h1>`-`<h6>` | Styled `<div>` |

---

## Component Patterns

### Button

```tsx
// ✅ Native button
<button type="button" onClick={handleClick}>
  Click me
</button>

// ✅ Icon button with accessible name
<button type="button" aria-label="Close dialog" onClick={onClose}>
  <XIcon aria-hidden="true" />
</button>

// ✅ Loading state
<button type="submit" disabled={isLoading} aria-busy={isLoading}>
  {isLoading ? 'Saving...' : 'Save'}
</button>
```

### Link

```tsx
// ✅ Internal navigation
<Link href="/dashboard">Dashboard</Link>

// ✅ External link
<a href="https://example.com" target="_blank" rel="noopener noreferrer">
  External Site
  <span className="sr-only">(opens in new tab)</span>
</a>

// ✅ Link styled as button (still navigates)
<Link href="/signup" className="btn-primary">Sign Up</Link>
```

### Form Field

```tsx
// ✅ Proper label association
<div>
  <label htmlFor="email">Email</label>
  <input
    id="email"
    type="email"
    aria-required="true"
    aria-invalid={!!errors.email}
    aria-describedby={errors.email ? 'email-error' : undefined}
  />
  {errors.email && (
    <span id="email-error" role="alert">
      {errors.email}
    </span>
  )}
</div>

// ✅ Required field indicator
<label htmlFor="name">
  Name
  <span aria-hidden="true">*</span>
  <span className="sr-only">(required)</span>
</label>
```

### Modal / Dialog

```tsx
import { useRef, useEffect } from 'react';

function Modal({ isOpen, onClose, title, children }: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      previousFocus.current = document.activeElement as HTMLElement;
      modalRef.current?.focus();
    } else {
      previousFocus.current?.focus();  // Return focus
    }
  }, [isOpen]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      ref={modalRef}
      tabIndex={-1}
    >
      <h2 id="modal-title">{title}</h2>
      {children}
      <button onClick={onClose} aria-label="Close">×</button>
    </div>
  );
}
```

**Modal requirements:**







- `role="dialog"` and `aria-modal="true"`
- `aria-labelledby` pointing to title
- Focus trapped inside modal
- Escape key closes modal
- Focus returns to trigger on close

### Tabs

```tsx
function Tabs({ tabs, activeTab, onChange }: TabsProps) {
  return (
    <div>
      <div role="tablist" aria-label="Content tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            id={`tab-${tab.id}`}
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            tabIndex={activeTab === tab.id ? 0 : -1}
            onClick={() => onChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {tabs.map((tab) => (
        <div
          key={tab.id}
          role="tabpanel"
          id={`panel-${tab.id}`}
          aria-labelledby={`tab-${tab.id}`}
          hidden={activeTab !== tab.id}
        >
          {tab.content}
        </div>
      ))}

    </div>

  );

}

```



**Tab keyboard navigation:**

- Arrow keys move between tabs
- Tab key moves to panel content
- Home/End jump to first/last tab

### Dropdown Menu

```tsx
function Menu({ trigger, items }: MenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const handleKeyDown = (e: KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex(i => Math.min(i + 1, items.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex(i => Math.max(i - 1, 0));
        break;
      case 'Enter':
      case ' ':
        if (activeIndex >= 0) items[activeIndex].onClick();
        setIsOpen(false);
        break;
      case 'Escape':
        setIsOpen(false);
        break;
    }
  };

  return (
    <div>
      <button
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen(!isOpen)}
      >
        {trigger}
      </button>

      {isOpen && (
        <ul role="menu" onKeyDown={handleKeyDown}>
          {items.map((item, index) => (
            <li
              key={item.id}
              role="menuitem"
              tabIndex={index === activeIndex ? 0 : -1}
              aria-current={index === activeIndex}
              onClick={item.onClick}
            >
              {item.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### Live Regions

```tsx
// Status updates (polite - waits for pause)
<div role="status" aria-live="polite">
  {message}
</div>

// Urgent alerts (assertive - interrupts)
<div role="alert" aria-live="assertive">
  {errorMessage}
</div>

// Progress updates
<div role="status" aria-live="polite" aria-atomic="true">
  Loading: {progress}%
</div>
```

---

## Skip Link

```tsx
function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 focus:z-50 focus:p-4 focus:bg-white"
    >
      Skip to main content
    </a>
  );
}

function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <SkipLink />
      <header>...</header>
      <main id="main-content" tabIndex={-1}>
        {children}
      </main>
    </>
  );
}
```

---

## Screen Reader Only (sr-only)

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
```

---

## Focus Management

### Visible Focus

```css
/* Never remove outlines without alternative */
:focus {
  outline: 2px solid #4F46E5;
  outline-offset: 2px;
}

/* Focus-visible for keyboard only */
:focus:not(:focus-visible) {
  outline: none;
}

:focus-visible {
  outline: 2px solid #4F46E5;
  outline-offset: 2px;
}
```

### Focus Trap (for modals)

```tsx
import { FocusTrap } from '@radix-ui/react-focus-trap';

function Modal({ children }: ModalProps) {
  return (
    <FocusTrap>
      <div role="dialog">{children}</div>
    </FocusTrap>
  );
}
```

---

## Use Radix UI / React Aria

For complex patterns, use battle-tested libraries:

```tsx
// Radix UI - handles all ARIA automatically
import * as Dialog from '@radix-ui/react-dialog';

<Dialog.Root>
  <Dialog.Trigger>Open</Dialog.Trigger>
  <Dialog.Portal>
    <Dialog.Overlay />
    <Dialog.Content>
      <Dialog.Title>Edit Profile</Dialog.Title>
      <Dialog.Close>×</Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal>
</Dialog.Root>
```

---

## Testing Accessibility

```tsx
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

test('component has no accessibility violations', async () => {
  const { container } = render(<Button>Click me</Button>);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

---

## Checklist

- [ ] All interactive elements are focusable
- [ ] Focus order follows visual order
- [ ] Focus is visible on all elements
- [ ] Modals trap focus and handle Escape
- [ ] Form inputs have labels
- [ ] Images have alt text
- [ ] Color is not sole information carrier
- [ ] Text has sufficient contrast (4.5:1 minimum)
- [ ] Page has skip link
- [ ] Dynamic content uses live regions
