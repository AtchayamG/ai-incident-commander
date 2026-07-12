import { test, expect } from '@playwright/test';

test.describe('Incident Commander - Creation and Dashboard Flow', () => {
  test('should create an incident, show it on the dashboard, navigate to details, and verify metadata', async ({ page }) => {
    // 1. Load the dashboard
    await page.goto('/');
    
    // Wait for the app to load and ensure the health status is ONLINE
    await expect(page.getByText('ONLINE')).toBeVisible({ timeout: 15000 });

    // 2. Open manual intake modal
    await page.getByRole('button', { name: 'Intake New Incident' }).click();

    // 3. Validate required fields (submit empty form)
    await page.getByRole('button', { name: 'Intake Incident' }).click();
    await expect(page.locator('#title-error')).toHaveText('Incident title is required.');
    await expect(page.locator('#summary-error')).toHaveText('A brief summary of the issue is required.');

    // 4. Fill form with valid and unique data
    const uniqueId = Date.now();
    const title = `E2E Test Incident - ${uniqueId}`;
    const service = 'payment-gateway';
    const environment = 'production';
    const severity = 'SEV2';
    const summary = `Detailed summary for unique E2E test incident ${uniqueId}`;

    await page.locator('#form-title').fill(title);
    await page.locator('#form-service').selectOption(service);
    await page.locator('#form-environment').selectOption(environment);
    await page.locator('#form-severity').selectOption(severity);
    await page.locator('#form-summary').fill(summary);

    // 5. Submit the form
    await page.getByRole('button', { name: 'Intake Incident' }).click();

    // The app redirects to /incidents/inc-xxxx
    // Let's wait for navigation to the details page
    await expect(page).toHaveURL(/\/incidents\/inc-/, { timeout: 15000 });

    // Find the incident ID from the URL or header
    const currentUrl = page.url();
    const matches = currentUrl.match(/\/incidents\/(inc-\d+)/);
    if (!matches) {
      throw new Error(`Failed to extract incident ID from URL: ${currentUrl}`);
    }
    const incidentId = matches[1];
    console.log(`Successfully created incident with ID: ${incidentId}`);

    const evidenceResponse = await page.request.get(
      `http://localhost:8001/api/v1/incidents/${incidentId}/evidence`,
    );
    expect(evidenceResponse.ok()).toBeTruthy();

    // Verify detail page has correct initial values
    await expect(page.getByRole('heading', { name: title })).toBeVisible();

    // 6. Go back to the dashboard
    await page.getByRole('button', { name: 'Back to Incident Dashboard' }).click();
    await expect(page).toHaveURL('/');

    // 7. Verify the incident is listed in the dashboard table
    const rowLocator = page.locator(`tr.incident-row:has-text("${incidentId}")`);
    await expect(rowLocator).toBeVisible();
    await expect(rowLocator.locator(`text=${title}`)).toBeVisible();
    await expect(rowLocator.locator(`text=${service}`)).toBeVisible();
    await expect(rowLocator.locator('text=SEV2 - Major')).toBeVisible();

    // 8. Open its detail route by clicking the row
    await rowLocator.click();
    await expect(page).toHaveURL(`/incidents/${incidentId}`);

    // 9. Assert details on the page: severity, service, state, simulated labeling
    await expect(page.getByRole('heading', { name: title })).toBeVisible();
    
    // Severity
    await expect(page.locator(`.badge:has-text("SEV2 - Major")`)).toBeVisible();
    
    // Service
    await expect(page.locator(`strong:has-text("${service}")`)).toBeVisible();
    
    // State (should initially be RECEIVED)
    await expect(page.locator(`.badge-state:has-text("State: RECEIVED")`)).toBeVisible();

    // Simulated labeling
    await expect(page.getByText('SIMULATED DATA')).toBeVisible();
  });
});
