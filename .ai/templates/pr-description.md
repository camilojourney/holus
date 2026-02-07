# PR Description Template

> Use this for all pull request descriptions

---

## Summary

<!-- 1-2 sentences describing what this PR does -->

---

## Changes

<!-- List files changed and what changed in each -->

- `path/to/file.ts` - Description of change
- `path/to/another.ts` - Description of change

---

## Type of Change

<!-- Check all that apply -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactor (no functional changes)
- [ ] Performance improvement

---

## Testing

<!-- How was this tested? -->

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

**Test coverage:** X%

---

## Checklist

<!-- Must all be checked before merge -->

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Security checklist completed (if applicable)
- [ ] Documentation updated (if user-facing)
- [ ] No console.log statements left
- [ ] No commented-out code left

---

## Screenshots

<!-- If UI changes, add before/after screenshots -->

| Before | After |
|--------|-------|
| (screenshot) | (screenshot) |

---

## Rollback Plan

<!-- How to revert if something goes wrong -->

```bash
git revert <commit-hash>
```

Or: "Safe to rollback via deployment platform UI"

---

## Related Issues

<!-- Link any related issues -->

Closes #XXX
