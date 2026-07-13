import { expect, test } from '@playwright/test';

test('real local API completes the approved simulated draft-PR and resolution artifacts', async ({ page, request }) => {
  page.on('dialog', dialog => dialog.accept());
  page.on('response', response => expect(response.status()).not.toBe(500));

  await page.goto('/');
  await page.getByRole('button', { name: 'Reset Demo Store' }).click();
  await expect(page).toHaveURL(/\/incidents\/inc-demo-0001/, { timeout: 15_000 });

  await page.getByRole('button', { name: 'Start Diagnosing Pipeline' }).click();
  await expect(page.locator('.badge-state', { hasText: 'State: WAITING PATCH APPROVAL' })).toBeVisible({ timeout: 20_000 });

  await page.locator('#reason-input').fill('Approve the exact bounded candidate patch.');
  await page.getByRole('button', { name: /Approve & Execute Patch/ }).click();
  await expect(page.locator('.badge-state', { hasText: 'State: WAITING PR APPROVAL' })).toBeVisible({ timeout: 30_000 });

  await page.locator('#reason-input').fill('Approve one simulated offline draft-PR artifact.');
  await page.getByRole('button', { name: '✓ Approve & Create PR' }).click();

  await expect(page.locator('.badge-state', { hasText: 'State: RESOLUTION DRAFTED' })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText('Draft PR Integration')).toBeVisible();
  await expect(page.getByText('SIMULATED PROVIDER')).toBeVisible();
  await expect(page.getByRole('heading', { name: /Communications/ })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Postmortem Report' })).toBeVisible();
  await expect(page.getByText('Timeline Evidence')).toBeVisible();

  const actionsResponse = await request.get('http://127.0.0.1:8001/api/v1/incidents/inc-demo-0001/draft-pr');
  expect(actionsResponse.ok()).toBeTruthy();
  const action = await actionsResponse.json();
  expect(action.status).toBe('completed');
  expect(action.provider_mode).toBe('simulated');

  const approvalsResponse = await request.get('http://127.0.0.1:8001/api/v1/incidents/inc-demo-0001/approvals');
  expect(approvalsResponse.ok()).toBeTruthy();
  const approvals = await approvalsResponse.json();
  expect(approvals.filter((approval: { approval_type: string }) => approval.approval_type === 'CREATE_DRAFT_PR')).toHaveLength(1);
});
