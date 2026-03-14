import { test, expect } from '@playwright/test';

test.describe('Content Pipeline', () => {
  test('AC-023: Content page loads', async ({ page }) => {
    await page.goto('/content');
    await page.waitForTimeout(3000);
    await expect(page.getByRole('heading', { name: 'Content Pipeline' })).toBeVisible();
  });
});
