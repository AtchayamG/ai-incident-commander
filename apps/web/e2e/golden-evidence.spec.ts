import { test, expect } from '@playwright/test';

test.describe('Incident Commander - Golden Evidence and Timeline E2E Scenario', () => {
  test('should reset demo, start pipeline, and verify the complete golden evidence bundle', async ({ page }) => {
    // Catch any 500 responses
    page.on('response', response => {
      expect(response.status()).not.toBe(500);
    });

    // Handle confirm dialogs automatically
    page.on('dialog', async dialog => {
      await dialog.accept();
    });

    // 1. Go to dashboard page
    await page.goto('/');
    await expect(page.getByText('ONLINE')).toBeVisible({ timeout: 15000 });

    // 2. Reset the demo to get a clean RECEIVED state for inc-demo-0001
    const resetBtn = page.getByRole('button', { name: 'Reset Demo Store' });
    await expect(resetBtn).toBeVisible();
    await resetBtn.click();

    // 3. The page should redirect to the incident room for inc-demo-0001
    await expect(page).toHaveURL(/\/incidents\/inc-demo-0001/, { timeout: 15000 });

    // 4. Verify initial state is RECEIVED
    await expect(page.locator('.badge-state:has-text("State: RECEIVED")')).toBeVisible();

    // 5. Start the pipeline
    const startBtn = page.getByRole('button', { name: 'Start Diagnosing Pipeline' });
    await expect(startBtn).toBeVisible();
    await startBtn.click();

    // 6. Assert pipeline progress checklist panel appears
    const progressPanel = page.locator('[data-testid="pipeline-progress-panel"]');
    await expect(progressPanel).toBeVisible();

    // 7. Wait for pipeline to complete and transit to WAITING_PATCH_APPROVAL
    await expect(page.locator('.badge-state:has-text("State: WAITING PATCH APPROVAL")')).toBeVisible({ timeout: 20000 });
    await expect(progressPanel).not.toBeVisible();

    // 8. Assert action required approval gate is present
    await expect(page.getByText('Action Required: Human Approval Gate')).toBeVisible();

    // 9. Assert 8 golden evidence cards are rendered
    const cards = page.locator('.evidence-card');
    await expect(cards).toHaveCount(8);

    // 10. Assert required alert, deployment, commit, stack, and runbook evidence exist
    // Metric alert
    const alertCard = page.locator('[data-testid="evidence-card-metric"]').filter({ hasText: 'rose from 0.2% to 12.4%' });
    await expect(alertCard).toBeVisible();

    // Deploy
    const deployCard = page.locator('[data-testid="evidence-card-deploy"]').filter({ hasText: 'Version 2026.07.13.4' });
    await expect(deployCard).toBeVisible();

    // Commit
    const commitCard = page.locator('[data-testid="evidence-card-diff"]').filter({ hasText: 'Commit c7f2e9a' });
    await expect(commitCard).toBeVisible();

    // Stack trace
    const stackCard = page.locator('[data-testid="evidence-card-log"]').filter({ hasText: 'stack trace points at src/checkout.ts' });
    await expect(stackCard).toBeVisible();

    // Runbook
    const runbookCard = page.locator('[data-testid="evidence-card-manual"]').filter({ hasText: 'check deployment correlation first' });
    await expect(runbookCard).toBeVisible();

    // 11. Assert stable timeline chronology and sorting
    const timelineItems = page.locator('.timeline-item');
    const count = await timelineItems.count();
    expect(count).toBe(8);

    const descriptions: string[] = [];
    const timestamps: number[] = [];

    for (let i = 0; i < count; i++) {
      const descText = await timelineItems.nth(i).locator('p').innerText();
      descriptions.push(descText);

      const timeText = await timelineItems.nth(i).locator('.timeline-time').innerText();
      timestamps.push(new Date(timeText).getTime());
    }

    // Verify chronological sorting (stamps are ascending)
    const sortedTimestamps = [...timestamps].sort((a, b) => a - b);
    expect(timestamps).toEqual(sortedTimestamps);

    // Verify the causal story order: commit -> deploy -> incident start
    const commitIdx = descriptions.findIndex(d => d.includes('Commit c7f2e9a'));
    const deployIdx = descriptions.findIndex(d => d.includes('Version 2026.07.13.4'));
    const startIdx = descriptions.findIndex(d => d.includes('Incident start'));

    expect(commitIdx).toBeGreaterThanOrEqual(0);
    expect(deployIdx).toBeGreaterThanOrEqual(0);
    expect(startIdx).toBeGreaterThanOrEqual(0);
    expect(commitIdx).toBeLessThan(deployIdx);
    expect(deployIdx).toBeLessThan(startIdx);

    // 12. Verify Timeline focus links
    // Find the first timeline item that has a link and click it
    const firstTimelineWithLink = timelineItems.filter({ has: page.locator('[data-testid^="timeline-link-"]') }).first();
    const linkBtn = firstTimelineWithLink.locator('[data-testid^="timeline-link-"]');
    const evidenceId = await linkBtn.getAttribute('data-testid').then(t => t?.replace('timeline-link-', ''));
    
    expect(evidenceId).toBeTruthy();
    
    // Clicking the link should expand the target card
    await linkBtn.click();
    
    const targetCard = page.locator(`[data-evidence-id="${evidenceId}"]`);
    await expect(targetCard).toBeVisible();
    await expect(targetCard.locator('[data-testid="evidence-content"]')).toBeVisible();

    // 13. Expand the commit card and assert provenance, simulated, and redacted labels
    const commitCardId = await commitCard.getAttribute('data-evidence-id');
    const expandBtn = commitCard.locator(`[data-testid="evidence-expand-${commitCardId}"]`);
    
    // Check if collapsed, if so click it
    const isExpanded = await expandBtn.getAttribute('aria-expanded');
    if (isExpanded !== 'true') {
      await expandBtn.click();
    }

    // Badges / Labels
    await expect(commitCard.locator('[data-testid="evidence-simulated-label"]')).toBeVisible();
    await expect(commitCard.locator('[data-testid="evidence-provider"]')).toHaveText(/fixture-/);
    await expect(commitCard.locator('[data-testid="evidence-source"]')).toHaveText(/simulated:/);
    await expect(commitCard.locator('[data-testid="evidence-display-ref"]')).toHaveText(/simulated:\/\/checkout-api\//);
    await expect(commitCard.locator('[data-testid="evidence-hash"]')).toHaveText(/sha256:/);

    // Inside expanded area
    await expect(commitCard.locator('[data-testid="evidence-content"]')).toBeVisible();
    await expect(commitCard.locator('[data-testid="evidence-provenance"]')).toBeVisible();

    // Let's also check the stack trace card which has redacted secrets
    const stackCardId = await stackCard.getAttribute('data-evidence-id');
    const stackExpandBtn = stackCard.locator(`[data-testid="evidence-expand-${stackCardId}"]`);
    if (await stackExpandBtn.getAttribute('aria-expanded') !== 'true') {
      await stackExpandBtn.click();
    }
    await expect(stackCard.locator('[data-testid="evidence-redacted-label"]')).toBeVisible();
    await expect(stackCard.locator('[data-testid="evidence-redaction-rules"]')).toBeVisible();
  });
});
