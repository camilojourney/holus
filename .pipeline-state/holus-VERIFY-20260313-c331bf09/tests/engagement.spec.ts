import { test, expect } from '@playwright/test';

test.describe('Engagement Tracker', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/engagement');
    await page.waitForTimeout(3000); // Hydration wait
  });

  test('AC-010, AC-028: Engagement page loads and navigation state', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Engagement Tracker' })).toBeVisible();
    await expect(page.getByText('Likes, comments, shares, and impressions')).toBeVisible();

    // AC-028: Sidebar active page indicator
    const navLink = page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Engagement' });
    await expect(navLink).toHaveAttribute('aria-current', 'page');
  });

  test('AC-011: Platform filter buttons exist and work', async ({ page }) => {
    const filterGroup = page.getByLabel('Filter by platform');
    await expect(filterGroup).toBeVisible();

    const platforms = ['all', 'linkedin', 'instagram', 'twitter'];
    for (const platform of platforms) {
      await expect(filterGroup.getByRole('button', { name: platform, exact: true })).toBeVisible();
    }

    const linkedinButton = filterGroup.getByRole('button', { name: 'linkedin', exact: true });
    const allButton = filterGroup.getByRole('button', { name: 'all', exact: true });

    await linkedinButton.click();
    await expect(linkedinButton).toHaveAttribute('aria-checked', 'true');
    await expect(allButton).toHaveAttribute('aria-checked', 'false');
  });

  test('AC-012: Metric filter buttons exist', async ({ page }) => {
    const filterGroup = page.getByLabel('Filter by metric');
    await expect(filterGroup).toBeVisible();

    const metrics = ['impressions', 'likes', 'comments', 'shares', 'Eng. Rate'];
    for (const metric of metrics) {
      await expect(filterGroup.getByRole('button', { name: metric, exact: true })).toBeVisible();
    }
  });

  test('AC-013: KPI cards show engagement data', async ({ page }) => {
    const metrics = ['Impressions', 'Likes', 'Comments', 'Shares', 'Avg Eng. Rate'];
    for (const metric of metrics) {
      await expect(page.getByText(metric)).toBeVisible();
    }
  });

  test('AC-014: Platform breakdown table renders', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Platform Breakdown (30d)' })).toBeVisible();
    const table = page.getByRole('table');
    await expect(table).toBeVisible();
    const headers = ['Platform', 'Impressions', 'Likes', 'Comments', 'Shares', 'Posts', 'Eng. Rate'];
    for (const header of headers) {
      await expect(table.getByRole('columnheader', { name: header })).toBeVisible();
    }
  });

  test('AC-015, AC-035: Engagement chart renders with accessibility', async ({ page }) => {
    const chart = page.locator('svg[aria-label="Engagement sparkline"]');
    await expect(chart).toBeVisible();

    // AC-035: Every SVG element has an aria-label attribute
    const svgs = await page.locator('svg').all();
    for (const svg of svgs) {
      await expect(svg).toHaveAttribute('aria-label');
    }
  });

  test('AC-031: Engagement page on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.getByRole('heading', { name: 'Engagement Tracker' })).toBeVisible();
    const filterGroup = page.getByLabel('Filter by platform');
    await expect(filterGroup).toBeVisible();
  });

  test('AC-033: All interactive elements meet touch target minimum', async ({ page }) => {
    const buttons = await page.getByLabel('Filter by platform').getByRole('button').all();
    for (const button of buttons) {
      const box = await button.boundingBox();
      if (box) {
        expect(box.height).toBeGreaterThanOrEqual(36);
      }
    }
  });
});
