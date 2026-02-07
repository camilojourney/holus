# Changelog Entry Template

> Use this format for user-facing release notes

---

## [Version] - YYYY-MM-DD

### Added
<!-- New features -->
- Feature description - brief explanation of what it does

### Changed
<!-- Changes to existing functionality -->
- Change description - what changed and why it matters

### Fixed
<!-- Bug fixes -->
- Bug fix description - what was broken, now works

### Deprecated
<!-- Features that will be removed in future -->
- Feature being deprecated - what to use instead

### Removed
<!-- Features removed in this version -->
- Feature removed - alternative if any

### Security
<!-- Security-related changes -->
- Security improvement - what was addressed

---

# Examples

## [1.2.0] - 2026-02-01

### Added
- **Audit dashboard** - Compare two release candidates side-by-side with highlighted differences
- **Outcome tagging** - Mark runs as success, failure, or needs follow-up

### Changed
- Improved record loading performance by 40%
- Updated core UI components for consistency and accessibility

### Fixed
- Fixed issue where required form field would lose focus while typing
- Fixed race condition in sequential ID generation

---

# Writing Guidelines

1. **Lead with user benefit** - Not "Added new database field" but "Now you can filter by date"

2. **Be specific** - Not "Fixed bug" but "Fixed issue where..."

3. **Order by importance** - Most impactful changes first

4. **Use action verbs** - Added, Changed, Fixed, Improved, Removed

5. **Link issues if public** - "Fixed login error (#123)"

6. **Skip internal changes** - Don't include refactors, dependency updates, or CI changes unless they affect users
