# Holus Observatory — Acceptance Criteria

Target URL: https://frontend-six-rho-96.vercel.app
Local preview: http://localhost:3000

## Structure

Each scenario follows **Given-When-Then**:
- **Given** = starting state (page loaded, viewport size, etc.)
- **When** = user action (click, scroll, navigate)
- **Then** = what must be true (visible, clickable, accessible)

`/verify` reads these and generates Playwright tests. The human writes the criteria, the AI writes the test code.

---

## 1. About Page (Recruiter Landing)

### AC-001: Hero section renders
**Priority:** P0

Given the user navigates to /about
When the page loads
Then the heading "Holus Observatory" is visible
And "Live system with 32 AI agents" is visible
And a "View Dashboard" button/link is visible
And an "Engagement Tracker" button/link is visible

### AC-002: Agent loop phases render
**Priority:** P0

Given the user navigates to /about
When the page loads
Then these 4 phase titles are visible: "Observe", "Reason", "Act", "Evaluate"

### AC-003: Agent architecture section
**Priority:** P1

Given the user navigates to /about
When the page loads
Then "32 Agents, 4 Categories" heading is visible
And "Managers" text is visible
And "Specialists" text is visible
And "Evaluators" text is visible
And "Ops" text is visible

### AC-004: Products section
**Priority:** P1

Given the user navigates to /about
When the page loads
Then "Products Holus Promotes" heading is visible
And "Pilaster" text is visible
And "Genpeli" text is visible
And "Invoz" text is visible

### AC-005: Technical stack section
**Priority:** P1

Given the user navigates to /about
When the page loads
Then "Technical Stack" heading is visible
And "Claude Opus 4.6" text is visible
And "Next.js" text is visible

### AC-006: Built-by section with social links
**Priority:** P0

Given the user navigates to /about
When the page loads
Then "Juan Camilo Martinez" text is visible
And a link with aria-label "Personal website" exists
And a link with aria-label "LinkedIn profile" exists
And a link with aria-label "GitHub profile" exists

### AC-007: Explore demo section with navigation cards
**Priority:** P1

Given the user navigates to /about
When the page loads
Then "Explore the Demo" heading is visible
And links to Dashboard, Agents, Content Pipeline, Engagement, Followers, Evaluations are visible

---

## 2. Dashboard

### AC-008: Dashboard page loads with heading
**Priority:** P0

Given the user navigates to /
When the page loads
Then the heading "Dashboard" is visible
And "Holus autonomous marketing system" text is visible

### AC-009: KPI cards render
**Priority:** P1

Given the user navigates to /
When the page loads
Then at least 3 KPI cards are visible (elements with class containing "rounded-xl" inside a grid)

---

## 3. Engagement Tracker

### AC-010: Engagement page loads
**Priority:** P0

Given the user navigates to /engagement
When the page loads
Then the heading "Engagement Tracker" is visible
And "Likes, comments, shares, and impressions" text is visible

### AC-011: Platform filter buttons exist and work
**Priority:** P0

Given the user navigates to /engagement
When the page loads
Then a filter group with aria-label "Filter by platform" is visible
And buttons for "all", "linkedin", "instagram", "twitter" are visible
When the user clicks the "linkedin" button
Then the "linkedin" button has aria-checked="true"
And the "all" button has aria-checked="false"

### AC-012: Metric filter buttons exist
**Priority:** P0

Given the user navigates to /engagement
When the page loads
Then a filter group with aria-label "Filter by metric" is visible
And buttons for "impressions", "likes", "comments", "shares", "Eng. Rate" are visible

### AC-013: KPI cards show engagement data
**Priority:** P1

Given the user navigates to /engagement
When the page loads
Then "Impressions" text is visible
And "Likes" text is visible
And "Comments" text is visible
And "Shares" text is visible
And "Avg Eng. Rate" text is visible

### AC-014: Platform breakdown table renders
**Priority:** P1

Given the user navigates to /engagement
When the page loads
Then "Platform Breakdown (30d)" heading is visible
And a table with columns "Platform", "Impressions", "Likes", "Comments", "Shares", "Posts", "Eng. Rate" is visible

### AC-015: Engagement chart renders
**Priority:** P1

Given the user navigates to /engagement
When the page loads
Then an SVG element with aria-label "Engagement sparkline" is visible

---

## 4. Follower Tracker

### AC-016: Follower page loads
**Priority:** P0

Given the user navigates to /followers
When the page loads
Then the heading "Follower Tracker" is visible
And "Follower growth, new follows, and unfollows" text is visible

### AC-017: Platform filter with aria semantics
**Priority:** P0

Given the user navigates to /followers
When the page loads
Then a filter group with aria-label "Filter by platform" is visible
When the user clicks the "instagram" button
Then the "instagram" button has aria-checked="true"

### AC-018: KPI cards show follower data
**Priority:** P1

Given the user navigates to /followers
When the page loads
Then "Total Followers" text is visible
And "Net Growth (30d)" text is visible
And "Growth Rate" text is visible
And "New Followers" text is visible
And "Unfollows" text is visible

### AC-019: Growth chart renders
**Priority:** P1

Given the user navigates to /followers
When the page loads
Then an SVG element with aria-label "Follower growth chart" is visible

### AC-020: Daily net change bar chart with legend
**Priority:** P1

Given the user navigates to /followers
When the page loads
Then "Daily Net Change" text is visible
And "Gained" legend label is visible
And "Lost" legend label is visible

### AC-021: Platform breakdown table
**Priority:** P1

Given the user navigates to /followers
When the page loads
Then "Platform Breakdown (30d)" heading is visible
And a table with columns "Platform", "Current", "New", "Unfollows", "Net", "Growth" is visible

---

## 5. Agents Page

### AC-022: Agents page loads
**Priority:** P0

Given the user navigates to /agents
When the page loads
Then the heading "Agents" is visible
And "All registered agents" text is visible

---

## 6. Content Pipeline

### AC-023: Content page loads
**Priority:** P0

Given the user navigates to /content
When the page loads
Then the heading "Content Pipeline" is visible

---

## 7. Evaluations

### AC-024: Evaluations page loads
**Priority:** P0

Given the user navigates to /evaluations
When the page loads
Then the heading "Evaluations" is visible

### AC-025: Heatmap has grid semantics
**Priority:** P1

Given the user navigates to /evaluations
When the page loads
Then an element with role="grid" and aria-label="Agent quality scores heatmap" is visible

---

## 8. Navigation & Layout

### AC-026: Sidebar navigation visible on desktop
**Priority:** P0

Given the viewport is 1440x900
When the user navigates to /
Then a nav element with aria-label "Main navigation" is visible
And links for "Dashboard", "Agents", "Content", "Engagement", "Followers", "Evaluations" are visible

### AC-027: Sidebar collapses on mobile
**Priority:** P0

Given the viewport is 375x667 (iPhone SE)
When the user navigates to /
Then a button with aria-label "Open navigation" is visible
And the nav element with aria-label "Main navigation" is not visible
When the user clicks the "Open navigation" button
Then the nav element with aria-label "Main navigation" is visible

### AC-028: Sidebar active page indicator
**Priority:** P1

Given the user navigates to /engagement
When the page loads
Then the "Engagement" nav link has aria-current="page"

### AC-029: Theme toggle
**Priority:** P1

Given the user navigates to /
When the page loads
Then a button with aria-label containing "Switch to" and "mode" is visible

---

## 9. Responsiveness

### AC-030: About page on mobile
**Priority:** P0

Given the viewport is 375x667
When the user navigates to /about
Then "Holus Observatory" heading is visible
And "Juan Camilo Martinez" is visible

### AC-031: Engagement page on mobile
**Priority:** P1

Given the viewport is 375x667
When the user navigates to /engagement
Then "Engagement Tracker" heading is visible
And the platform filter buttons are visible (flex-wrap should handle overflow)

### AC-032: Followers page on mobile
**Priority:** P1

Given the viewport is 375x667
When the user navigates to /followers
Then "Follower Tracker" heading is visible

---

## 10. Accessibility

### AC-033: All interactive elements meet 44px touch target
**Priority:** P0

Given the user navigates to /engagement
When the page loads
Then all buttons in the platform filter have a minimum height of 36px (py-2 = 8px padding + line height)

### AC-034: Focus rings on keyboard navigation
**Priority:** P1

Given the user navigates to /about
When the user tabs to an "Explore the Demo" card link
Then the focused element has a visible focus ring (outline or ring)

### AC-035: Chart SVGs have aria-labels
**Priority:** P1

Given the user navigates to /engagement
When the page loads
Then every SVG element has an aria-label attribute

Given the user navigates to /followers
When the page loads
Then every SVG element has an aria-label attribute
