# Accessibility Design Reference

> ARIA patterns, semantic HTML decisions, and keyboard navigation planning.

---

## Semantic HTML Decision Table

| Interactive Element | Correct Element | Never Use |
|---------------------|-----------------|-----------|
| Click triggers action | `<button>` | `<div onClick>` |
| Navigate to page | `<a href>` | `<span onClick>` |
| Submit form | `<button type="submit">` | `<div>` |
| Toggle setting | `<input type="checkbox">` | `<div>` |
| Select one of many | `<input type="radio">` | `<div>` |
| Text input | `<input>` or `<textarea>` | `<div contenteditable>` |
| List of items | `<ul>/<ol>` + `<li>` | `<div>` + `<div>` |
| Data table | `<table>` + proper structure | CSS grid of divs |

---

## Component-Specific ARIA Requirements

### Button

**Design requirements:**





- Native `<button>` element
- `aria-label` if icon-only
- `aria-pressed` if toggle
- `aria-expanded` if controls expandable region
- `aria-disabled` (not just `disabled`) for styled disabled state

```typescript
interface AccessibleButtonDesign {
  element: 'button';
  requiredAria: {
    'aria-label'?: string;     // If icon-only
    'aria-pressed'?: boolean;  // If toggle
    'aria-expanded'?: boolean; // If controls menu/accordion
  };
  keyboardSupport: ['Enter', 'Space'];
}
```



### Link



**Design requirements:**

- Native `<a>` with `href`
- External links: `target="_blank"` + `rel="noopener noreferrer"`
- `aria-current="page"` for current nav item
- Skip link for keyboard users

```typescript
interface AccessibleLinkDesign {
  element: 'a';
  requiredAttributes: {
    href: string;  // Always present
  };
  conditionalAttributes: {

    rel: 'noopener noreferrer';  // Security

    'aria-current': 'page';  // Current nav
  };

}
```


### Modal/Dialog


**Design requirements:**

- `role="dialog"` or `role="alertdialog"`
- `aria-modal="true"`
- `aria-labelledby` pointing to title
- Focus trap (Tab/Shift+Tab cycles within)
- Escape key closes
- Return focus to trigger on close

```typescript
interface AccessibleModalDesign {
  element: 'div';
  requiredAria: {
    role: 'dialog' | 'alertdialog';
    'aria-modal': true;
    'aria-labelledby': string;  // ID of title element
  };
  focusManagement: {
    trapFocus: true;
    initialFocus: 'first-focusable' | 'close-button' | 'specific-element';
    returnFocusTo: 'trigger-element';

  };
  keyboardSupport: {
    Escape: 'close';

    Tab: 'cycle-forward';
    'Shift+Tab': 'cycle-backward';
  };

}
```


### Tabs

**Design requirements:**

- `role="tablist"` on container
- `role="tab"` on each tab
- `role="tabpanel"` on each panel
- `aria-selected` on active tab
- `aria-controls` linking tab to panel
- Arrow key navigation between tabs

```typescript
interface AccessibleTabsDesign {
  tablist: {
    role: 'tablist';
    'aria-label': string;  // Describe the tab group
  };
  tab: {
    role: 'tab';
    'aria-selected': boolean;

    tabIndex: 0 | -1;  // 0 for selected, -1 for others
  };
  tabpanel: {

    role: 'tabpanel';
    'aria-labelledby': string;  // ID of tab
    tabIndex: 0;  // Focusable for keyboard users
  };

  keyboardSupport: {
    ArrowLeft: 'previous-tab';
    ArrowRight: 'next-tab';
    Home: 'first-tab';

    End: 'last-tab';
  };
}
```


### Combobox (Autocomplete)

**Design requirements:**

- `role="combobox"` on input
- `aria-expanded` indicating dropdown state
- `aria-activedescendant` for highlighted option
- `aria-autocomplete` describing behavior
- `role="listbox"` on dropdown
- `role="option"` on each item

```typescript
interface AccessibleComboboxDesign {
  input: {
    role: 'combobox';

    'aria-expanded': boolean;
    'aria-haspopup': 'listbox';
    'aria-autocomplete': 'list' | 'both' | 'inline';
    'aria-activedescendant'?: string;  // ID of highlighted option
  };

  listbox: {
    role: 'listbox';
    'aria-label': string;
  };
  option: {

    role: 'option';
    'aria-selected': boolean;
  };
  keyboardSupport: {
    ArrowDown: 'next-option | open';

    ArrowUp: 'previous-option';
    Enter: 'select-option';
    Escape: 'close';
  };
}

```

### Form Field


**Design requirements:**

- `<label>` associated via `htmlFor` or wrapping
- `aria-describedby` for help text
- `aria-invalid` for error state
- `aria-required` for required fields

- Error messages in `aria-describedby` region

```typescript
interface AccessibleFormFieldDesign {
  label: {
    element: 'label';

    htmlFor: string;  // Input ID
  };
  input: {
    id: string;  // Matches label htmlFor
    'aria-describedby'?: string;  // Help text + error IDs
    'aria-invalid'?: boolean;

    'aria-required'?: boolean;
  };
  errorMessage: {
    id: string;  // Referenced in aria-describedby
    role: 'alert';  // For immediate announcement
  };

}
```

### Toast/Notification

**Design requirements:**

- `role="status"` for non-urgent
- `role="alert"` for urgent
- `aria-live="polite"` or `aria-live="assertive"`
- Content read by screen reader when added

```typescript
interface AccessibleToastDesign {
  urgency: 'polite' | 'assertive';
  container: {
    role: 'status' | 'alert';
    'aria-live': 'polite' | 'assertive';
    'aria-atomic': true;  // Read entire region, not just changes
  };
}
```

---

## Keyboard Navigation Patterns

### Focus Management Rules

| Scenario | Focus Behavior |
|----------|----------------|
| Modal opens | Focus first focusable or close button |
| Modal closes | Return focus to trigger element |
| Dropdown opens | Focus first item |
| Dropdown closes (Escape) | Return focus to trigger |
| Dropdown closes (selection) | Focus trigger, announce selection |
| Page navigation (SPA) | Focus main content heading |
| Form error | Focus first field with error |

### Tab Order Design

```typescript
interface TabOrderDesign {
  // Positive tabindex is an anti-pattern
  rule: 'Use tabIndex={0} for focusable, tabIndex={-1} for programmatic focus only';

  // Skip link pattern
  skipLink: {
    position: 'First focusable element';
    target: 'Main content (#main)';
    visible: 'On focus only';
  };

  // Logical order
  verify: 'Tab order matches visual order and reading order';
}
```

### Arrow Key Patterns

| Component | Arrow Behavior |
|-----------|----------------|
| Tabs | Left/Right moves between tabs |
| Menu | Up/Down moves between items |
| Grid | All arrows move between cells |
| Combobox | Up/Down moves in dropdown |
| Radio group | Arrows move selection |
| Tree | Arrows navigate + expand/collapse |

---

## Design Phase Checklist

### For Every Component

- [ ] Correct semantic element chosen
- [ ] Keyboard trigger (if interactive): Enter and/or Space
- [ ] Focus style visible (don't remove outline without replacement)
- [ ] Color contrast planned (4.5:1 for text, 3:1 for UI)

### For Forms


- [ ] Every input has associated label
- [ ] Required fields marked visually AND with `aria-required`
- [ ] Error messages linked via `aria-describedby`
- [ ] Error announcement strategy (live region or focus)
- [ ] Submit via Enter key works


### For Dynamic Content

- [ ] Live regions for async updates users should know about
- [ ] Loading states announced (`aria-busy` or live region)
- [ ] Focus management after content changes

### For Navigation


- [ ] Skip link present
- [ ] Current page indicated (`aria-current="page"`)
- [ ] Landmark regions defined (`<main>`, `<nav>`, `<aside>`)
- [ ] Heading hierarchy (h1 → h2 → h3, no skipping)

---


## Anti-Patterns to Catch

### 1. Div as Button

```tsx
// ❌ Design flaw

<div onClick={handleClick}>Submit</div>

// ✅ Correct design
<button onClick={handleClick}>Submit</button>
```

**Why it matters:**

- No keyboard support (Enter/Space)
- Not announced as button
- No focus indicator
- Can't be disabled properly

### 2. Click-Only Interactions

```tsx
// ❌ Design flaw
<div onClick={toggle}>Show Details</div>

// ✅ Correct design
<button onClick={toggle} aria-expanded={isOpen}>
  Show Details
</button>
```

### 3. Missing Label Association

```tsx
// ❌ Design flaw
<span>Email</span>
<input type="email" />

// ✅ Correct design
<label htmlFor="email">Email</label>
<input id="email" type="email" />
```

### 4. Color-Only Information

```tsx
// ❌ Design flaw
// Red = error, green = success (color blind users can't see)

// ✅ Correct design
// Icon + color + text label
<span className="error">
  <ErrorIcon /> Invalid email address
</span>
```

### 5. Focus Trap Without Escape

```tsx
// ❌ Design flaw
// Modal traps focus but Escape doesn't work

// ✅ Correct design
// Escape key always closes, focus returns to trigger
```

---

## Headless UI Libraries

For complex patterns, design should specify use of accessible headless libraries:

| Component | Recommended Library |
|-----------|---------------------|
| Modal/Dialog | Radix Dialog, React Aria |
| Combobox | Radix Combobox, Downshift |
| Tabs | Radix Tabs, React Aria |
| Menu/Dropdown | Radix Dropdown, React Aria |
| Tooltip | Radix Tooltip |
| Toast | Radix Toast |

**Why:** These handle ARIA attributes, focus management, and keyboard navigation automatically.

**Design artifact should specify:**
```markdown
## Accessibility Implementation

**Library:** Radix UI
**Components:** Dialog, Tabs, DropdownMenu

**Custom requirements beyond library defaults:**
- Focus first name input on dialog open (not default close button)
- Announce tab panel content on tab change
```
