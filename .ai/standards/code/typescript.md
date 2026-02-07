# TypeScript Standards

## Configuration

Use strict mode and fail fast on unsafe patterns.

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

## Core Rules

- Prefer `unknown` over `any`
- Add explicit return types to exported functions
- Validate external input at boundaries
- Model domain concepts with clear interfaces/types
- Avoid hidden nullable behavior

## Naming

| Category | Convention |
|----------|------------|
| variables/functions | camelCase |
| types/interfaces/classes | PascalCase |
| constants | SCREAMING_SNAKE_CASE |
| booleans | `is*`, `has*`, `should*` |

## Error Handling

- Use typed error classes for known failure modes
- Return actionable error messages at API/UI boundaries
- Never swallow errors silently
- Preserve context when rethrowing

## Imports/Exports

- Prefer named exports
- Keep imports grouped: external, internal alias, relative
- Use `import type` for type-only imports

## Safety Checklist

- [ ] No `any` in new code
- [ ] No unchecked external input
- [ ] No nullable access without guard/fallback
- [ ] No implicit return type on exported functions
