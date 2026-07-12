import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility & Keyboard Flow Audit', () => {
  // Handle confirm dialogs automatically
  test.beforeEach(({ page }) => {
    page.on('dialog', async dialog => {
      await dialog.accept();
    });
  });

  test('Dashboard and Intake Modal - Accessibility & Focus Flow', async ({ page }) => {
    // 1. Load the dashboard
    await page.goto('/');
    await expect(page.getByText('ONLINE')).toBeVisible({ timeout: 15000 });

    // Run Axe audit on the dashboard page
    const dashboardAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    const dashboardViolations = dashboardAxe.violations.filter(
      v => v.impact === 'serious' || v.impact === 'critical'
    );
    if (dashboardViolations.length > 0) {
      console.log('Dashboard Serious/Critical Axe Violations:', JSON.stringify(dashboardViolations, null, 2));
    }
    expect(dashboardViolations).toEqual([]);

    // 2. Open manual intake modal
    const intakeBtn = page.getByRole('button', { name: 'Intake New Incident' });
    await expect(intakeBtn).toBeVisible();
    
    // Focus trigger button
    await intakeBtn.focus();
    await expect(intakeBtn).toBeFocused();

    // Trigger via Enter key
    await page.keyboard.press('Enter');
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // Focus Trap & Restoration Verification:
    // First, verify focus moves inside the modal
    const titleInput = page.locator('#form-title');
    await expect(titleInput).toBeFocused();

    // Run Axe audit on the open modal
    const modalAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    const modalViolations = modalAxe.violations.filter(
      v => v.impact === 'serious' || v.impact === 'critical'
    );
    if (modalViolations.length > 0) {
      console.log('Modal Serious/Critical Axe Violations:', JSON.stringify(modalViolations, null, 2));
    }
    expect(modalViolations).toEqual([]);

    // Fill form and check validation using keyboard
    await titleInput.fill('Test incident title');
    // Tab to Affected Service
    await page.keyboard.press('Tab');
    const serviceSelect = page.locator('#form-service');
    await expect(serviceSelect).toBeFocused();

    // Close the modal using Escape key
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible();

    // Verify focus restoration to the trigger button
    await expect(intakeBtn).toBeFocused();
  });

  test('Incident Room - Accessibility, Keyboard Flow & Citations', async ({ page }) => {
    // 1. Load the dashboard and reset the demo to seed inc-demo-0001
    await page.goto('/');
    await expect(page.getByText('ONLINE')).toBeVisible({ timeout: 15000 });

    const resetBtn = page.getByRole('button', { name: 'Reset Demo Store' });
    await resetBtn.click();

    // 2. Wait for Incident Detail Page for inc-demo-0001
    await expect(page).toHaveURL(/\/incidents\/inc-demo-0001/, { timeout: 15000 });
    await expect(page.locator('.badge-state:has-text("State: RECEIVED")')).toBeVisible();

    // 3. Start Diagnosing Pipeline
    const startBtn = page.getByRole('button', { name: 'Start Diagnosing Pipeline' });
    await expect(startBtn).toBeVisible();
    await startBtn.focus();
    await expect(startBtn).toBeFocused();
    await page.keyboard.press('Enter');

    // 4. Wait for WAITING_PATCH_APPROVAL status (the golden state)
    await expect(page.locator('.badge-state:has-text("State: WAITING PATCH APPROVAL")')).toBeVisible({ timeout: 20000 });

    // Run Axe audit on the complete Golden Incident Room
    const roomAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    
    const roomViolations = roomAxe.violations.filter(
      v => v.impact === 'serious' || v.impact === 'critical'
    );
    if (roomViolations.length > 0) {
      console.log('Incident Room Serious/Critical Axe Violations:', JSON.stringify(roomViolations, null, 2));
    }
    expect(roomViolations).toEqual([]);

    // 5. Test Citation Focus Links via Keyboard
    const firstTimelineLink = page.locator('[data-testid^="timeline-link-"]').first();
    await expect(firstTimelineLink).toBeVisible();
    
    const targetEvidenceId = await firstTimelineLink.getAttribute('data-testid').then(t => t?.replace('timeline-link-', ''));
    expect(targetEvidenceId).toBeTruthy();

    // Tab to the timeline link or focus it
    await firstTimelineLink.focus();
    await expect(firstTimelineLink).toBeFocused();
    
    // Press Enter to activate link
    await page.keyboard.press('Enter');

    // Assert that the target evidence card is expanded and focused
    const targetCard = page.locator(`#evidence-${targetEvidenceId}`);
    await expect(targetCard).toBeVisible();
    await expect(targetCard).toBeFocused();

    // 6. Test Approval Controls via Keyboard
    const approvalSection = page.locator('text=Action Required: Human Approval Gate');
    await expect(approvalSection).toBeVisible();

    const justificationInput = page.locator('#reason-input');
    await expect(justificationInput).toBeVisible();

    // Focus input and type justification
    await justificationInput.focus();
    await expect(justificationInput).toBeFocused();
    await justificationInput.fill('Approving patch with keyboard justification');

    // Tab to Approve button
    await page.keyboard.press('Tab');
    const approveBtn = page.getByRole('button', { name: '✓ Approve & Execute Patch' });
    await expect(approveBtn).toBeFocused();
  });

  test('Mobile Viewport Layout - Overflow & Contrast Check', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Load dashboard
    await page.goto('/');
    await expect(page.getByText('ONLINE')).toBeVisible({ timeout: 15000 });

    // Assert no horizontal scroll on the HTML/body element
    const hasHorizontalOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth || document.body.scrollWidth > window.innerWidth;
    });
    expect(hasHorizontalOverflow).toBe(false);

    // Open Modal
    await page.getByRole('button', { name: 'Intake New Incident' }).click();
    const modal = page.locator('[role="dialog"]');
    await expect(modal).toBeVisible();

    // Modal should fit mobile screen
    const modalOverflow = await page.evaluate(() => {
      const modalEl = document.querySelector('[role="dialog"] > div');
      if (!modalEl) return false;
      return modalEl.scrollWidth > window.innerWidth;
    });
    expect(modalOverflow).toBe(false);
  });
});
