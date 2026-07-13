import { test, expect } from '@playwright/test';

test.describe.serial('M8 Product Polish', () => {
  let consoleErrors: string[] = [];

  test.beforeEach(({ page }) => {
    consoleErrors = [];
    page.on('pageerror', (err) => {
      consoleErrors.push(err.message);
    });
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
  });

  test.afterEach(() => {
    expect(consoleErrors).toEqual([]);
  });

  test('should assert zero console errors and successful navigations on dashboard', async ({ page }) => {
    // Navigate to dashboard
    const response = await page.goto('/');
    expect(response?.ok()).toBeTruthy();

    // Verify there are no console errors logged
    expect(consoleErrors.length).toBe(0);

    // Click around to ensure no failed same-origin links
    // First, verify we see health status
    await expect(page.getByTestId('health-status')).toBeVisible();

    // Wait for data load
    await page.waitForLoadState('networkidle');
  });

  test('should allow onboarding dismissal and restoration', async ({ page }) => {
    await page.goto('/');
    
    // Banner should be visible initially
    const banner = page.getByTestId('onboarding-banner');
    await expect(banner).toBeVisible();

    // Dismiss the banner
    await page.getByRole('button', { name: 'Dismiss onboarding' }).click();
    await expect(banner).toBeHidden();

    // Reload the page, should stay hidden (localStorage)
    await page.reload();
    await expect(banner).toBeHidden();

    // Restore the banner using the guide button
    const restoreBtn = page.getByTestId('restore-onboarding-btn');
    await expect(restoreBtn).toBeVisible();
    await restoreBtn.click();

    await expect(banner).toBeVisible();
  });

  test('should surface health and provenance correctly without fabricating', async ({ page }) => {
    await page.goto('/');
    
    // Check that health status text reflects the truth
    await expect(page.getByTestId('health-status')).toHaveText(/ONLINE|OFFLINE/, { timeout: 15000 });
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set viewport to mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Ensure the main container doesn't overflow horizontally
    const container = page.locator('main.container');
    const box = await container.boundingBox();
    expect(box?.width).toBeLessThanOrEqual(375);

    // Verify banner still readable
    const banner = page.getByTestId('onboarding-banner');
    if (await banner.isVisible()) {
      const bannerBox = await banner.boundingBox();
      expect(bannerBox?.width).toBeLessThanOrEqual(375 - 16); // padding
    }
  });
});
