import { test, expect } from '@playwright/test';

test.describe('Evaluations', () => {
  test('AC-024: Evaluations page loads', async ({ page }) => {
    await page.goto('/evaluations');
    await page.waitForTimeout(3000);
    await expect(page.getByRole('heading', { name: 'Evaluations' })).toBeVisible();
  });

  test('AC-025: Heatmap has grid semantics', async ({ page }) => {
    await page.goto('/evaluations');
    await page.waitForTimeout(3000);
    await expect(page.getByRole('grid', { name: 'Agent quality scores heatmap' })).toBeVisible();
  });
});
