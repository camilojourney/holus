# React Standards

## Component Design

- Prefer function components
- Keep components focused on one responsibility
- Co-locate small helper logic with component when appropriate
- Extract reusable logic into hooks

## Props and State

- Use typed props interfaces
- Keep state minimal and derived when possible
- Prefer controlled inputs for forms
- Avoid duplicating server state into local state unnecessarily

## Performance

- Memoize only when profiling indicates benefit
- Use stable callbacks for deep prop trees
- Virtualize large lists
- Avoid expensive work during render

## UI Quality

- Handle loading, empty, error, success states explicitly
- Keep actions clear and reversible where possible
- Preserve keyboard navigation and visible focus
- Respect reduced-motion preferences

## Testability

- Separate view logic from business logic
- Avoid hidden side effects in render paths
- Keep components deterministic for same inputs

## Checklist

- [ ] Props/state typed
- [ ] All core UI states covered
- [ ] Accessibility basics included
- [ ] No obvious re-render hotspots
