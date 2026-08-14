import { expect, test } from '@playwright/test';

test('studio runs only the local demo lifecycle', async ({ page }) => {
  const forbidden: string[] = [];
  page.on('request', (request) => {
    const url = request.url();
    if (
      url.includes('genai.camilomartinez.co') ||
      /localhost:800\d|127\.0\.0\.1:800\d/.test(url)
    ) {
      forbidden.push(url);
    }
  });

  await page.goto('/studio');
  await expect(page.getByRole('heading', { name: /bounded Holus generation request/i })).toBeVisible();
  await expect(page.getByText(/No live job is created/i)).toBeVisible();
  await page.getByRole('button', { name: 'Run demonstration' }).click();
  await expect(page.getByText(/holus-demo-/)).toBeVisible();
  await expect(page.getByText(/queued/i).first()).toBeVisible();
  await expect(page.getByText('Local placeholder', { exact: true })).toBeVisible({ timeout: 8_000 });
  await expect(page.getByText(/Demonstration complete/i)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Explore the API' }).first()).toHaveAttribute(
    'href',
    'https://api.camilomartinez.co/',
  );
  if (test.info().project.name === 'mobile') {
    const triggerBox = await page.getByRole('button', { name: 'Open navigation' }).boundingBox();
    const privateGenerationCopyBox = await page
      .getByText(/Genpeli remains a private generation system/i)
      .boundingBox();
    if (!triggerBox || !privateGenerationCopyBox) {
      throw new Error('Expected the mobile navigation trigger and generation description to be rendered.');
    }
    const overlapsPrivateGenerationCopy =
      triggerBox.x < privateGenerationCopyBox.x + privateGenerationCopyBox.width &&
      triggerBox.x + triggerBox.width > privateGenerationCopyBox.x &&
      triggerBox.y < privateGenerationCopyBox.y + privateGenerationCopyBox.height &&
      triggerBox.y + triggerBox.height > privateGenerationCopyBox.y;
    expect(overlapsPrivateGenerationCopy).toBe(false);
  }
  expect(forbidden).toEqual([]);
  await page.screenshot({
    path: `e2e/artifacts/studio-${test.info().project.name}.png`,
    fullPage: true,
  });
});

test('studio error path stays a labelled demonstration', async ({ page }) => {
  await page.goto('/studio');
  await page.getByRole('button', { name: 'Demonstrate error' }).click();
  await expect(page.getByText(/No live job was created/i)).toBeVisible({ timeout: 8_000 });
});
