import { test, expect } from '@playwright/test';

test.describe('Follower Tracker', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/followers');
    await page.waitForTimeout(3000); // Hydration wait
  });

  test('AC-016: Follower page loads', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Follower Tracker' })).toBeVisible();
    await expect(page.getByText('Follower growth, new follows, and unfollows')).toBeVisible();
  });

  test('AC-017: Platform filter with aria semantics', async ({ page }) => {
    const filterGroup = page.getByLabel('Filter by platform');
    await expect(filterGroup).toBeVisible();
    const instagramButton = filterGroup.getByRole('button', { name: 'instagram', exact: true });
    await instagramButton.click();
    await expect(instagramButton).toHaveAttribute('aria-checked', 'true');
  });

  test('AC-018: KPI cards show follower data', async ({ page }) => {
    const metrics = ['Total Followers', 'Net Growth (30d)', 'Growth Rate', 'New Followers', 'Unfollows'];
    for (const metric of metrics) {
      await expect(page.getByText(metric)).toBeVisible();
    }
  });

  test('AC-019, AC-035: Growth chart renders with accessibility', async ({ page }) => {
    const chart = page.locator('svg[aria-label="Follower growth chart"]');
    await expect(chart).toBeVisible();

    // AC-035: Every SVG element has an aria-label attribute
    const svgs = await page.locator('svg').all();
    for (const svg of svgs) {
      await expect(svg).toHaveAttribute('aria-label');
    }
  });

  test('AC-020: Daily net change bar chart with legend', async ({ page }) => {
    await expect(page.getByText('Daily Net Change')).toBeVisible();
    await expect(page.getByText('Gained')).toBeVisible();
    await expect(page.getByText('Lost')).toBeVisible();
  });

  test('AC-021: Platform breakdown table', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Platform Breakdown (30d)' })).toBeVisible();
    const table = page.getByRole('table');
    await expect(table).toBeVisible();
    const headers = ['Platform', 'Current', 'New', 'Unfollows', 'Net', 'Growth'];
    for (const header of headers) {
      await expect(table.getByRole('columnheader', { name: header })).toBeVisible();
    }
  });

  test('AC-032: Followers page on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.getByRole('heading', { name: 'Follower Tracker' })).toBeVisible();
  });
});
