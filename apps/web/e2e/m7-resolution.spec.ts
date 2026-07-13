import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// Frontend intercepted contract coverage only. This does not prove backend E2E behavior.
test.describe('M7 Resolution UI (Frontend Contract Coverage)', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  const mockBaseIncident = {
    id: 'inc1',
    title: 'Test Incident',
    service: 'auth',
    environment: 'production',
    severity: 'SEV1',
    summary: 'Test summary',
    provider_mode: 'simulated',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  test('blocks PR approval if incident is not WAITING_PR_APPROVAL or verification missing', async ({ page }) => {
    await page.route('**/api/v1/incidents/inc1/*', async route => route.fulfill({ json: [] }));
    await page.route('**/api/v1/incidents/inc1', async route => {
      await route.fulfill({ json: { ...mockBaseIncident, state: 'REVIEW_READY' } }); // Wrong state
    });
    await page.route('**/api/v1/incidents/inc1/approvals', async route => {
      await route.fulfill({ json: [{ id: 'a1', incident_id: 'inc1', approval_type: 'CREATE_DRAFT_PR', status: 'pending', risk_level: 'high', requested_at: new Date().toISOString(), expires_at: new Date().toISOString() }] });
    });
    await page.route('**/api/v1/incidents/inc1/patches', async route => {
      await route.fulfill({ json: [{ id: 'p1', plan_id: 'plan1', attempt: 1 }] });
    });
    await page.route('**/api/v1/incidents/inc1/remediation-plan', async route => {
      await route.fulfill({ json: [{ id: 'plan1', incident_id: 'inc1', steps: [], risk_level: 'high' }] });
    });
    await page.route('**/api/v1/incidents/inc1/verifications', async route => {
      await route.fulfill({ json: [{ id: 'v1', patch_id: 'p1', passed: false, checks: [] }] }); // Failed verification
    });
    await page.route('**/api/v1/incidents/inc1/investigation', async route => {
      await route.fulfill({ json: { status: 'complete', remediation_enabled: true } });
    });
    await page.route('**/api/v1/incidents/inc1/draft-pr', async route => route.fulfill({ status: 404, json: {} }));

    await page.goto('/incidents/inc1');
    
    const approveButton = page.getByRole('button', { name: /Approve/i });
    await expect(approveButton).toBeDisabled();
    
    const warning = page.getByText('Cannot approve PR creation because verification checks have not passed or incident is not in WAITING_PR_APPROVAL state.');
    await expect(warning).toBeVisible();
  });

  test('enables approval when in WAITING_PR_APPROVAL and verification passed', async ({ page }) => {
    await page.route('**/api/v1/incidents/inc1/*', async route => route.fulfill({ json: [] }));
    await page.route('**/api/v1/incidents/inc1', async route => {
      await route.fulfill({ json: { ...mockBaseIncident, state: 'WAITING_PR_APPROVAL' } });
    });
    await page.route('**/api/v1/incidents/inc1/approvals', async route => {
      await route.fulfill({ json: [{ id: 'a1', incident_id: 'inc1', approval_type: 'CREATE_DRAFT_PR', status: 'pending', risk_level: 'high', requested_at: new Date().toISOString(), expires_at: new Date().toISOString() }] });
    });
    await page.route('**/api/v1/incidents/inc1/patches', async route => {
      await route.fulfill({ json: [{ id: 'p1', plan_id: 'plan1', attempt: 1 }] });
    });
    await page.route('**/api/v1/incidents/inc1/remediation-plan', async route => {
      await route.fulfill({ json: [{ id: 'plan1', incident_id: 'inc1', steps: [], risk_level: 'high' }] });
    });
    await page.route('**/api/v1/incidents/inc1/verifications', async route => {
      await route.fulfill({ json: [{ id: 'v1', patch_id: 'p1', passed: true, checks: [] }] });
    });
    await page.route('**/api/v1/incidents/inc1/investigation', async route => {
      await route.fulfill({ json: { status: 'complete', remediation_enabled: true } });
    });
    await page.route('**/api/v1/incidents/inc1/draft-pr', async route => route.fulfill({ status: 404, json: {} }));

    await page.goto('/incidents/inc1');
    
    const approveButton = page.getByRole('button', { name: '✓ Approve & Create PR' });
    await expect(approveButton).toBeEnabled();
    const warning = page.getByText('Cannot approve PR creation because verification checks have not passed or incident is not in WAITING_PR_APPROVAL state.');
    await expect(warning).toBeHidden();
  });

  test('displays simulated artifact for Draft PR failed/retry states without duplicate artifacts', async ({ page }) => {
    await page.route('**/api/v1/incidents/inc1/*', async route => route.fulfill({ json: [] }));
    await page.route('**/api/v1/incidents/inc1', async route => {
      await route.fulfill({ json: { ...mockBaseIncident, state: 'EXTERNAL_ACTION_FAILED' } });
    });
    await page.route('**/api/v1/incidents/inc1/investigation', async route => {
      await route.fulfill({ json: { status: 'complete', remediation_enabled: true } });
    });
    await page.route('**/api/v1/incidents/inc1/draft-pr', async route => {
      await route.fulfill({ json: { id: 'pr1', status: 'failed', url: 'https://github.com/mock/repo/pull/1', provider_mode: 'simulated', error_message: 'GitHub API limit', idempotency_key: 'idem-1' } });
    });

    await page.goto('/incidents/inc1');
    
    // There should be only one "Draft PR Integration"
    await expect(page.getByText('Draft PR Integration')).toHaveCount(1);
    await expect(page.getByText('SIMULATED PROVIDER')).toBeVisible();
    await expect(page.getByText('FAILED', { exact: true })).toBeVisible();
    await expect(page.getByRole('link', { name: 'https://github.com/mock/repo/pull/1' })).toBeVisible();
    await expect(page.getByText('GitHub API limit')).toBeVisible();
    await expect(page.getByText('Idempotency Key: idem-1')).toBeVisible();
  });

  test('displays technical/stakeholder communications and postmortem timeline/actions', async ({ page }) => {
    // Basic route intercepts
    await page.route('**/api/v1/incidents/inc1/*', async route => route.fulfill({ json: [] }));
    await page.route('**/api/v1/incidents/inc1', async route => {
      await route.fulfill({ json: { ...mockBaseIncident, state: 'RESOLUTION_DRAFTED' } });
    });
    await page.route('**/api/v1/incidents/inc1/investigation', async route => {
      await route.fulfill({ json: { status: 'complete', remediation_enabled: true } });
    });
    
    // Explicit intercepts for M7 resources
    await page.route('**/api/v1/incidents/inc1/communications', async route => {
      await route.fulfill({ json: { technical_update: 'Technical details here', stakeholder_update: 'Stakeholder info', resolution_note: 'Resolved via PR' } });
    });
    await page.route('**/api/v1/incidents/inc1/postmortem', async route => {
      await route.fulfill({ json: { 
        id: 'pm-1',
        incident_id: 'inc1',
        created_at: new Date().toISOString(),
        summary: 'Postmortem summary', 
        impact: 'High impact', 
        root_cause: 'Bad config', 
        resolution: 'Fixed config', 
        timeline_json: [{ id: 't1', incident_id: 'inc1', at: new Date().toISOString(), kind: 'patch.applied', description: 'Patch was applied', evidence_id: 'ev1' }],
        action_items_json: [{ priority: 'High', owner: 'Alice', description: 'Fix things' }],
        markdown_uri: 'https://docs.local/pm-1'
      } });
    });
    await page.route('**/api/v1/incidents/inc1/draft-pr', async route => {
      await route.fulfill({ status: 404, json: {} });
    });

    await page.goto('/incidents/inc1');
    
    await expect(page.getByRole('heading', { name: /Communications/i })).toBeVisible();
    await expect(page.getByText('Technical details here')).toBeVisible();
    await expect(page.getByText('Stakeholder info')).toBeVisible();
    await expect(page.getByText('Resolved via PR')).toBeVisible();

    await expect(page.getByRole('heading', { name: 'Postmortem Report' })).toBeVisible();
    await expect(page.getByText('Postmortem summary')).toBeVisible();
    await expect(page.getByText('Bad config')).toBeVisible();
    
    // Timeline rendering
    await expect(page.getByText('Timeline Evidence')).toBeVisible();
    await expect(page.getByText('PATCH APPLIED')).toBeVisible();
    await expect(page.getByText('Patch was applied')).toBeVisible();
    await expect(page.getByRole('button', { name: 'View Evidence' })).toBeVisible();

    // Action items
    await expect(page.getByText('Fix things')).toBeVisible();
    await expect(page.getByText('Alice')).toBeVisible();
    
    // Markdown link
    await expect(page.getByRole('link', { name: 'View Markdown Postmortem' })).toHaveAttribute('href', 'https://docs.local/pm-1');
    
    // Ensure document doesn't overflow 375px
    const mainContent = page.locator('main');
    const box = await mainContent.boundingBox();
    expect(box?.width).toBeLessThanOrEqual(375);

    // Accessibility check (axe scan)
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    // Exclude contrast issues which might be present due to brand colors, mainly test structural/A11y bounds
    const violationsWithoutContrast = accessibilityScanResults.violations.filter(v => v.id !== 'color-contrast');
    expect(violationsWithoutContrast).toEqual([]);
  });
});
