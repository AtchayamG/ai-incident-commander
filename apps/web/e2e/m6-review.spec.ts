import { test, expect } from '@playwright/test';

test.describe('M6 Review Package UX', () => {
  // Use incident with ID from seed data that reaches the PR/review state,
  // or we can intercept API requests to mock the verification run state for these specific tests.
  
  test.beforeEach(async ({ page, request }) => {
    // We want to test against the app, we can intercept network calls if the M5 backend doesn't exist yet,
    // but the prompt says: "using real local API setup where available." and "Do not mock success in production code."
    // However, in Playwright, intercepting to test frontend states is standard.
    // The prompt says: "If M5 data required for a final scenario does not exist yet, implement a truthful empty/pending state and document the exact integration seam. Do not mock success in production code."
    // We're just testing the frontend logic.
  });

  test('blocks PR approval if verification is missing', async ({ page }) => {
    // Intercept API calls to simulate an incident in WAITING_PR_APPROVAL state with NO verification run
    await page.route('**/api/v1/incidents/test-inc', async route => {
      await route.fulfill({
        json: {
          id: 'test-inc',
          title: 'Test Incident',
          state: 'WAITING_PR_APPROVAL',
          provider_mode: 'simulated',
          severity: 'SEV1',
        }
      });
    });
    await page.route('**/api/v1/incidents/test-inc/approvals', async route => {
      await route.fulfill({
        json: [{
          id: 'app-1',
          incident_id: 'test-inc',
          approval_type: 'CREATE_DRAFT_PR',
          status: 'pending',
          risk_level: 'low',
          reason: 'Please approve PR',
          requested_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 86400000).toISOString(),
        }]
      });
    });
    await page.route('**/api/v1/incidents/test-inc/patches', async route => {
      await route.fulfill({
        json: [{
          id: 'patch-1',
          plan_id: 'plan-1',
          attempt: 1,
          diff: '+ added line',
          files_changed: 1,
          lines_changed: 1
        }]
      });
    });
    await page.route('**/api/v1/incidents/test-inc/remediation-plan', async route => {
      await route.fulfill({
        json: [{
          id: 'plan-1',
          incident_id: 'test-inc',
          summary: 'Fix something',
          steps: [],
          risk_level: 'low'
        }]
      });
    });
    // Missing verification
    await page.route('**/api/v1/incidents/test-inc/verifications', async route => {
      await route.fulfill({ json: [] });
    });
    // Other endpoints
    await page.route('**/api/v1/incidents/test-inc/investigation', async route => {
      await route.fulfill({ status: 404, json: { detail: 'not available in this state fixture' } });
    });
    await page.route('**/api/v1/incidents/test-inc/*', async route => {
      await route.fallback();
    });

    await page.goto('/incidents/test-inc');
    
    // Expect the unmet prerequisite warning
    await expect(page.getByText('Cannot approve PR creation because verification checks have not passed or incident is not in WAITING_PR_APPROVAL state.')).toBeVisible();
    
    // Expect the approve button to be disabled
    const approveBtn = page.getByRole('button', { name: '✓ Approve & Create PR' });
    await expect(approveBtn).toBeDisabled();
    
    // Expect verification status to be pending
    await expect(page.getByText('Pending / Not Started')).toBeVisible();
  });

  test('blocks PR approval if verification failed', async ({ page }) => {
    // Intercept API calls to simulate an incident with a FAILED verification run
    await page.route('**/api/v1/incidents/test-inc', async route => {
      await route.fulfill({
        json: {
          id: 'test-inc',
          title: 'Test Incident',
          state: 'WAITING_PR_APPROVAL',
          provider_mode: 'simulated',
          severity: 'SEV1',
        }
      });
    });
    await page.route('**/api/v1/incidents/test-inc/approvals', async route => {
      await route.fulfill({
        json: [{
          id: 'app-1',
          incident_id: 'test-inc',
          approval_type: 'CREATE_DRAFT_PR',
          status: 'pending',
          risk_level: 'low',
          reason: 'Please approve PR',
          requested_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 86400000).toISOString(),
        }]
      });
    });
    await page.route('**/api/v1/incidents/test-inc/patches', async route => {
      await route.fulfill({
        json: [{
          id: 'patch-1',
          plan_id: 'plan-1',
          attempt: 1,
          diff: '+ added line',
          files_changed: 1,
          lines_changed: 1
        }]
      });
    });
    await page.route('**/api/v1/incidents/test-inc/remediation-plan', async route => {
      await route.fulfill({
        json: [{
          id: 'plan-1',
          incident_id: 'test-inc',
          summary: 'Fix something',
          steps: [],
          risk_level: 'low'
        }]
      });
    });
    // Failed verification
    await page.route('**/api/v1/incidents/test-inc/verifications', async route => {
      await route.fulfill({
        json: [{
          id: 'verif-1',
          patch_id: 'patch-1',
          passed: false,
          checks: [
            { name: 'Unit Tests', passed: false, detail: 'Failed 1 test' }
          ]
        }]
      });
    });
    // Other endpoints
    await page.route('**/api/v1/incidents/test-inc/investigation', async route => {
      await route.fulfill({ status: 404, json: { detail: 'not available in this state fixture' } });
    });
    await page.route('**/api/v1/incidents/test-inc/*', async route => {
      await route.fallback();
    });

    await page.goto('/incidents/test-inc');
    
    // Expect the unmet prerequisite warning
    await expect(page.getByText('Cannot approve PR creation because verification checks have not passed or incident is not in WAITING_PR_APPROVAL state.')).toBeVisible();
    
    // Expect the approve button to be disabled
    const approveBtn = page.getByRole('button', { name: '✓ Approve & Create PR' });
    await expect(approveBtn).toBeDisabled();
    
    // Expect verification status to be failed
    await expect(page.getByText('Verification Failed')).toBeVisible();
    await expect(page.getByText('Unit Tests')).toBeVisible();
    await expect(page.getByText('Failed 1 test')).toBeVisible();
  });

  test('allows PR approval if verification passed', async ({ page }) => {
    // Intercept API calls to simulate an incident with a PASSED verification run
    await page.route('**/api/v1/incidents/test-inc', async route => {
      await route.fulfill({
        json: {
          id: 'test-inc',
          title: 'Test Incident',
          state: 'WAITING_PR_APPROVAL',
          provider_mode: 'simulated',
          severity: 'SEV1',
        }
      });
    });
    await page.route('**/api/v1/incidents/test-inc/approvals', async route => {
      await route.fulfill({
        json: [{
          id: 'app-1',
          incident_id: 'test-inc',
          approval_type: 'CREATE_DRAFT_PR',
          status: 'pending',
          risk_level: 'low',
          reason: 'Please approve PR',
          requested_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 86400000).toISOString(),
        }]
      });
    });
    await page.route('**/api/v1/incidents/test-inc/patches', async route => {
      await route.fulfill({
        json: [{
          id: 'patch-1',
          plan_id: 'plan-1',
          attempt: 1,
          diff: '+ added line',
          files_changed: 1,
          lines_changed: 1
        }]
      });
    });
    await page.route('**/api/v1/incidents/test-inc/remediation-plan', async route => {
      await route.fulfill({
        json: [{
          id: 'plan-1',
          incident_id: 'test-inc',
          summary: 'Fix something',
          steps: [],
          risk_level: 'low'
        }]
      });
    });
    // Passed verification
    await page.route('**/api/v1/incidents/test-inc/verifications', async route => {
      await route.fulfill({
        json: [{
          id: 'verif-1',
          patch_id: 'patch-1',
          passed: true,
          checks: [
            { name: 'Unit Tests', passed: true, detail: 'All tests passed' }
          ]
        }]
      });
    });
    // Other endpoints
    await page.route('**/api/v1/incidents/test-inc/investigation', async route => {
      await route.fulfill({ status: 404, json: { detail: 'not available in this state fixture' } });
    });
    await page.route('**/api/v1/incidents/test-inc/*', async route => {
      await route.fallback();
    });

    await page.goto('/incidents/test-inc');
    
    // Expect the unmet prerequisite warning to NOT be visible
    await expect(page.getByText('Prerequisite Unmet')).toBeHidden();
    
    // Expect the approve button to be enabled
    const approveBtn = page.getByRole('button', { name: 'Approve & Create PR' });
    await expect(approveBtn).toBeEnabled();
    
    // Expect verification status to be passed
    await expect(page.getByText('Verification Passed')).toBeVisible();
    await expect(page.getByText('Unit Tests')).toBeVisible();
    await expect(page.getByText('All tests passed')).toBeVisible();
  });
});
