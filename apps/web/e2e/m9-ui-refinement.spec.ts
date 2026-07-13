import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

test.describe.serial('M9 UI Refinement & Screenshot Capture', () => {
  const screenshotDir = path.resolve(__dirname, '..', '..', '..', 'docs', 'submission', 'screenshots');

  // Handle dialog alerts automatically
  test.beforeEach(({ page }) => {
    page.on('dialog', async dialog => {
      await dialog.accept();
    });
  });

  test('should assert layout boundaries and capture the 4 golden screenshots', async ({ page }) => {
    // 1. Dashboard Viewport and Screenshot (01-dashboard.png)
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('/');

    // Wait for the page and API status to settle
    await expect(page.getByTestId('health-status')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('ONLINE')).toBeVisible();

    // Verify Onboarding banner is present
    await expect(page.getByTestId('onboarding-banner')).toBeVisible();

    // Take Dashboard Screenshot
    const dashboardPath = path.join(screenshotDir, '01-dashboard.png');
    await page.screenshot({ path: dashboardPath });
    console.log(`Captured 01-dashboard.png at ${dashboardPath}`);

    // Verify 375px mobile viewport containment on Dashboard
    await page.setViewportSize({ width: 375, height: 800 });
    const mainContainer = page.locator('main.container');
    const containerBox = await mainContainer.boundingBox();
    expect(containerBox?.width).toBeLessThanOrEqual(375);

    // 2. Incident Room - Reset & WAITING_PATCH_APPROVAL (02-investigation-approval.png)
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('/');
    const resetBtn = page.getByRole('button', { name: 'Reset Demo Store' });
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();

    // The page should redirect to the incident room for inc-demo-0001
    await expect(page).toHaveURL(/\/incidents\/inc-demo-0001/, { timeout: 15000 });
    await expect(page.locator('.badge-state:has-text("State: RECEIVED")')).toBeVisible();

    // Start pipeline
    const startBtn = page.getByRole('button', { name: 'Start Diagnosing Pipeline' });
    await expect(startBtn).toBeVisible();
    await startBtn.click();

    // Wait for WAITING PATCH APPROVAL
    await expect(page.locator('.badge-state:has-text("State: WAITING PATCH APPROVAL")')).toBeVisible({ timeout: 25000 });

    // Verify layout boundaries and hash containment
    const hashLabel = page.getByTestId('remediation-artifact-hash');
    await expect(hashLabel).toBeVisible();
    const hashBox = await hashLabel.boundingBox();
    // Hash should wrap and not overflow parent boundary
    const parentCard = page.locator('.card:has([data-testid="remediation-artifact-hash"])');
    const parentBox = await parentCard.boundingBox();
    if (hashBox && parentBox) {
      expect(hashBox.width).toBeLessThan(parentBox.width);
    }

    // Check no horizontal overflow at desktop
    const bodyWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(bodyWidth).toBeLessThanOrEqual(1440);

    // Take Investigation & Approval Screenshot
    const invApprovalPath = path.join(screenshotDir, '02-investigation-approval.png');
    await page.screenshot({ path: invApprovalPath });
    console.log(`Captured 02-investigation-approval.png at ${invApprovalPath}`);

    // Verify no horizontal overflow at 768px on incident details page
    await page.setViewportSize({ width: 768, height: 1000 });
    const midWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(midWidth).toBeLessThanOrEqual(768);

    // Verify no horizontal overflow at 375px on incident details page
    await page.setViewportSize({ width: 375, height: 1000 });
    const mobileWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(mobileWidth).toBeLessThanOrEqual(375);

    // 3. Incident Room - WAITING_PR_APPROVAL (03-review-approval.png)
    await page.setViewportSize({ width: 1440, height: 1000 });
    // Fill justification and approve the patch
    const reasonInput = page.locator('#reason-input');
    await reasonInput.fill('Remediation patch looks bounded and correct. Approving.');

    const approvePatchBtn = page.getByRole('button', { name: /Approve & Execute Patch/ });
    await expect(approvePatchBtn).toBeEnabled();
    await approvePatchBtn.click();

    // Wait for the pipeline to transition to WAITING_PR_APPROVAL
    await expect(page.locator('.badge-state:has-text("State: WAITING PR APPROVAL")')).toBeVisible({ timeout: 25000 });

    // Assert key verification cards are visible in order
    await expect(page.getByText('Action Required: Human Approval Gate')).toBeVisible();
    await expect(page.getByText('Verification Results')).toBeVisible();
    await expect(page.getByText('Generated Diff Patch')).toBeVisible();

    // Check no horizontal overflow at desktop
    const desktopWidth3 = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(desktopWidth3).toBeLessThanOrEqual(1440);

    // Take Review & PR Approval Screenshot
    const reviewApprovalPath = path.join(screenshotDir, '03-review-approval.png');
    await page.screenshot({ path: reviewApprovalPath });
    console.log(`Captured 03-review-approval.png at ${reviewApprovalPath}`);

    // 4. Incident Room - RESOLUTION_DRAFTED (04-resolution-package.png)
    // Fill justification and approve the PR creation
    await reasonInput.fill('Code matches and tests pass. Approving PR creation.');
    const approvePRBtn = page.getByRole('button', { name: /Approve & Create PR/ });
    await expect(approvePRBtn).toBeEnabled();
    await approvePRBtn.click();

    // Wait for state to progress to RESOLUTION_DRAFTED
    await expect(page.locator('.badge-state:has-text("State: RESOLUTION DRAFTED")')).toBeVisible({ timeout: 25000 });

    // Assert resolution package components are visible
    await expect(page.getByText('Pull Request Status')).toBeVisible();
    await expect(page.getByText('Communications')).toBeVisible();
    await expect(page.getByText('Postmortem Report')).toBeVisible();

    // Check no horizontal overflow at desktop
    const desktopWidth4 = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(desktopWidth4).toBeLessThanOrEqual(1440);

    // Take Resolution Package Screenshot
    const resolutionPath = path.join(screenshotDir, '04-resolution-package.png');
    await page.screenshot({ path: resolutionPath });
    console.log(`Captured 04-resolution-package.png at ${resolutionPath}`);
  });

  test('all rendered internal links resolve without an HTTP error', async ({ page }) => {
    const paths = ['/', '/incidents/inc-demo-0001'];
    for (const route of paths) {
      await page.goto(route);
      const hrefs = await page.locator('a[href]').evaluateAll(anchors =>
        anchors
          .map(anchor => anchor.getAttribute('href'))
          .filter((href): href is string => Boolean(href) && href!.startsWith('/')),
      );
      for (const href of [...new Set(hrefs)]) {
        const response = await page.request.get(href);
        expect(response.status(), `${route} links to failing ${href}`).toBeLessThan(400);
      }
    }
  });
});
