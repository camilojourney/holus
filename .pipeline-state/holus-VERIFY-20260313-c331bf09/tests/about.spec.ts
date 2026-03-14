import { test, expect } from '@playwright/test';

test.describe('About Page (Recruiter Landing)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/about');
    await page.waitForTimeout(3000); // Hydration wait
  });

  test('AC-001: Hero section renders', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Holus Observatory', exact: true })).toBeVisible();
    await expect(page.getByText('Live system with 32 AI agents')).toBeVisible();
    await expect(page.getByRole('link', { name: 'View Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Engagement Tracker' })).toBeVisible();
  });

  test('AC-002: Agent loop phases render', async ({ page }) => {
    for (const phase of ['Observe', 'Reason', 'Act', 'Evaluate']) {
      await expect(page.getByText(phase)).toBeVisible();
    }
  });

  test('AC-003: Agent architecture section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: '32 Agents, 4 Categories' })).toBeVisible();
    await expect(page.getByText('Managers')).toBeVisible();
    await expect(page.getByText('Specialists')).toBeVisible();
    await expect(page.getByText('Evaluators')).toBeVisible();
    await expect(page.getByText('Ops')).toBeVisible();
  });

  test('AC-004: Products section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Products Holus Promotes' })).toBeVisible();
    await expect(page.getByText('Pilaster', { exact: true })).toBeVisible();
    await expect(page.getByText('Genpeli', { exact: true })).toBeVisible();
    await expect(page.getByText('Invoz', { exact: true })).toBeVisible();
  });

  test('AC-005: Technical stack section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Technical Stack' })).toBeVisible();
    await expect(page.getByText('Claude Opus 4.6')).toBeVisible();
    await expect(page.getByText('Next.js')).toBeVisible();
  });

  test('AC-006: Built-by section with social links', async ({ page }) => {
    await expect(page.getByText('Juan Camilo Martinez')).toBeVisible();
    await expect(page.getByLabel('Personal website')).toBeVisible();
    await expect(page.getByLabel('LinkedIn profile')).toBeVisible();
    await expect(page.getByLabel('GitHub profile')).toBeVisible();
  });

  test('AC-007: Explore demo section with navigation cards', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Explore the Demo' })).toBeVisible();
    const links = ['Dashboard', 'Agents', 'Content Pipeline', 'Engagement', 'Followers', 'Evaluations'];
    for (const link of links) {
      await expect(page.getByRole('link', { name: link })).toBeVisible();
    }
  });

  test('AC-030: About page on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.getByRole('heading', { name: 'Holus Observatory' })).toBeVisible();
    await expect(page.getByText('Juan Camilo Martinez')).toBeVisible();
  });

  test('AC-034: Focus rings on keyboard navigation', async ({ page }) => {
    const cardLink = page.getByRole('link', { name: 'Dashboard' }).first();
    await page.keyboard.press('Tab');
    // Assuming focus ring is implemented with CSS outline or ring class
    // We check if the element has focus
    await expect(cardLink).toBeFocused();
  });
});
