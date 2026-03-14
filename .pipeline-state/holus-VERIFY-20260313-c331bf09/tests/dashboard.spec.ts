import { test, expect } from '@playwright/test';

test.describe('Dashboard and Navigation', () => {
  test('AC-008, AC-026: Dashboard page loads with navigation (Desktop)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.waitForTimeout(3000); // Hydration wait

    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByText('Holus autonomous marketing system')).toBeVisible();

    // AC-026: Sidebar navigation visible on desktop
    const nav = page.getByRole('navigation', { name: 'Main navigation' });
    await expect(nav).toBeVisible();
    const links = ['Dashboard', 'Agents', 'Content', 'Engagement', 'Followers', 'Evaluations'];
    for (const link of links) {
      await expect(nav.getByRole('link', { name: link })).toBeVisible();
    }
  });

  test('AC-009: KPI cards render', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    // At least 3 KPI cards (elements with class containing "rounded-xl" inside a grid)
    const kpiCards = page.locator('.grid .rounded-xl');
    const count = await kpiCards.count();
    expect(count).toBeGreaterThanOrEqual(3);
  });

  test('AC-027: Sidebar collapses on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');
    await page.waitForTimeout(3000);

    const openButton = page.getByLabel('Open navigation');
    await expect(openButton).toBeVisible();

    const nav = page.getByRole('navigation', { name: 'Main navigation' });
    await expect(nav).not.toBeVisible();

    await openButton.click();
    await expect(nav).toBeVisible();
  });

  test('AC-029: Theme toggle', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(3000);
    const themeButton = page.locator('button[aria-label*="Switch to"][aria-label*="mode"]');
    await expect(themeButton).toBeVisible();
  });
});
