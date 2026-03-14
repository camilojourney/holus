import { test, expect } from '@playwright/test';

test.describe('Agents Page', () => {
  test('AC-022: Agents page loads', async ({ page }) => {
    await page.goto('/agents');
    await page.waitForTimeout(3000);
    await expect(page.getByRole('heading', { name: 'Agents' })).toBeVisible();
    await expect(page.getByText('All registered agents')).toBeVisible();
  });
});
