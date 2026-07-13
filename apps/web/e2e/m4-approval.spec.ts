import { test, expect } from '@playwright/test';

test.describe.serial('M4 Approval UI', () => {
  test('should render the bounded remediation artifact and support approval with error surfacing', async ({ page }) => {
    // 1. Load the dashboard
    await page.goto('/');
    
    // Catch any 500 responses
    page.on('response', response => {
      expect(response.status()).not.toBe(500);
    });

    // Handle confirm dialogs automatically
    page.on('dialog', async dialog => {
      await dialog.accept();
    });

    // 2. Reset the demo to get a clean RECEIVED state for inc-demo-0001
    const resetBtn = page.getByRole('button', { name: 'Reset Demo Store' });
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();
    
    await expect(page).toHaveURL(/\/incidents\/inc-demo-0001/, { timeout: 15000 });
    
    // 3. Start the pipeline
    const startBtn = page.getByRole('button', { name: 'Start Diagnosing Pipeline' });
    await expect(startBtn).toBeVisible();
    await startBtn.click();
    
    // 4. Wait for WAITING PATCH APPROVAL
    await expect(page.locator('.badge-state:has-text("State: WAITING PATCH APPROVAL")')).toBeVisible({ timeout: 20000 });
    
    // 5. Verify the Approval Gate appears
    await expect(page.getByText('Action Required: Human Approval Gate')).toBeVisible();
    
    // 6. Verify bounded artifact components are rendered
    await expect(page.getByText('Bounded Remediation Artifact')).toBeVisible();
    await expect(page.getByText('Exact Files & Budgets:')).toBeVisible();
    await expect(page.getByText('Hash & Provenance:')).toBeVisible();
    await expect(page.getByText('Verification Commands:')).toBeVisible();
    await expect(page.getByText('Rollback Procedure:')).toBeVisible();
    await expect(page.getByText('Intended Changes:')).toBeVisible();
    await expect(page.getByTestId('remediation-artifact-hash')).toHaveText(/^sha256:/);
    await expect(page.getByText('Network: Denied')).toBeVisible();
    
    // 7. Verify we can't approve without justification
    await page.getByRole('button', { name: /Approve & Execute Patch/ }).click();
    await expect(page.getByText('A reason is required to decide on this request.', { exact: true })).toBeVisible();
    
    // 8. Provide justification and approve
    const reasonInput = page.locator('#reason-input');
    await reasonInput.fill('Looks good and bounded.');
    
    // Intercept the API to simulate stale response first (deterministic error behavior)
    let intercepted = false;
    await page.route('**/api/v1/approvals/*/decision', async route => {
      if (!intercepted && route.request().method() === 'POST') {
        intercepted = true;
        await route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Approval request is stale or already consumed.' })
        });
      } else {
        await route.continue();
      }
    });
    
    await page.getByRole('button', { name: /Approve & Execute Patch/ }).click();
    
    // Verify the error message surfaces in plain language
    await expect(page.getByText(/stale or already consumed/i, { exact: false })).toBeVisible();
    
    // 9. Click approve again (now goes to real local API)
    await page.getByRole('button', { name: /Approve & Execute Patch/ }).click();
    
    // 10. Verify state progresses
    await expect(page.locator('.badge-state:has-text("State: PATCHING")').or(page.locator('.badge-state:has-text("State: VERIFYING")')).or(page.locator('.badge-state:has-text("State: REVIEW READY")')).or(page.locator('.badge-state:has-text("State: WAITING PR APPROVAL")'))).toBeVisible({ timeout: 20000 });
  });

  test('should support rejection of the bounded remediation artifact', async ({ page }) => {
    // Handle confirm dialogs automatically
    page.on('dialog', async dialog => {
      await dialog.accept();
    });

    await page.goto('/');
    await page.getByRole('button', { name: 'Reset Demo Store' }).click();
    await expect(page).toHaveURL(/\/incidents\/inc-demo-0001/, { timeout: 15000 });
    await page.getByRole('button', { name: 'Start Diagnosing Pipeline' }).click();
    await expect(page.locator('.badge-state:has-text("State: WAITING PATCH APPROVAL")')).toBeVisible({ timeout: 20000 });
    
    const reasonInput = page.locator('#reason-input');
    await reasonInput.fill('Rejecting because it seems too broad.');
    
    await page.getByRole('button', { name: /Reject Patch/ }).click();
    
    // Wait for the decision to be recorded
    await expect(page.getByText('Approval Decision Record')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('.badge.badge-sev1', { hasText: 'REJECTED' })).toBeVisible();
  });
});
