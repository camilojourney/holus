import { expect, test, type Page } from '@playwright/test';

const API_ORIGIN = 'https://api.camilomartinez.co/';
const CAPABILITY =
  'A versioned API for authenticated teams to publish, schedule, and manage social content across X, Threads, Instagram, Facebook, and LinkedIn from one integration.';

async function assertNoForbiddenDestinations(page: Page) {
  const hrefs = await page.locator('a[href]').evaluateAll((anchors) =>
    anchors.map((anchor) => (anchor as HTMLAnchorElement).href),
  );
  expect(hrefs.some((href) => href.includes('genai.camilomartinez.co'))).toBe(false);
  expect(hrefs.some((href) => href.startsWith('http://localhost:800'))).toBe(false);
}

test('recruiter landing tells the Holus story and links the API', async ({ page }) => {
  const localhostStreams: string[] = [];
  page.on('request', (request) => {
    const url = request.url();
    if (/localhost:800\d|127\.0\.0\.1:800\d/.test(url) && url.includes('trajectory')) {
      localhostStreams.push(url);
    }
  });

  await page.addInitScript(() => {
    const Original = window.EventSource;
    window.EventSource = class extends Original {
      constructor(url: string | URL, config?: EventSourceInit) {
        const value = String(url);
        if (/localhost|127\.0\.0\.1/.test(value)) {
          throw new Error(`localhost EventSource is forbidden in public demo: ${value}`);
        }
        super(url, config);
      }
    };
  });

  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Orchestration for AI content/i })).toBeVisible();
  await expect(page.getByText(/Holus is the single public product/i)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Run a generation demo' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Explore the API' }).first()).toHaveAttribute('href', API_ORIGIN);
  await expect(page.getByText(CAPABILITY)).toBeVisible();
  await expect(page.getByText(/Live events require an authenticated backend connection/i).first()).toBeVisible();
  const connectionBadge = page.locator('[data-connection-kind]').filter({ visible: true }).first();
  await expect(connectionBadge).toBeVisible();
  await expect(connectionBadge).toHaveText(/Connection required|Demo data/);
  await expect(page.getByRole('link', { name: 'Reliability' })).toBeVisible();
  await assertNoForbiddenDestinations(page);
  expect(localhostStreams).toEqual([]);
  await page.screenshot({
    path: `e2e/artifacts/landing-${test.info().project.name}.png`,
    fullPage: true,
  });
});

test('public content route shows only labelled representative output', async ({ page }) => {
  const observatoryRequests: string[] = [];
  page.on('request', (request) => {
    const url = request.url();
    if (/localhost:800\d|127\.0\.0\.1:800\d|observatory\.internal/i.test(url)) {
      observatoryRequests.push(url);
    }
  });

  await page.goto('/content');
  await expect(page.getByRole('heading', { name: 'Representative output' })).toBeVisible();
  await expect(page.getByText('Demo data - LinkedIn draft', { exact: true })).toBeVisible();
  await expect(page.getByText(/This public demo does not create a generation job/i)).toBeVisible();
  await expect(page.getByText(/Agent event stream/i)).toHaveCount(0);
  expect(observatoryRequests).toEqual([]);
});
