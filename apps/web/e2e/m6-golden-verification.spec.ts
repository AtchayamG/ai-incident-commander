import { expect, test } from '@playwright/test';

test('real local API requests PR approval only after deterministic verification passes', async ({ page, request }) => {
  page.on('dialog', dialog => dialog.accept());
  page.on('response', response => expect(response.status()).not.toBe(500));

  await page.goto('/');
  await page.getByRole('button', { name: 'Reset Demo Store' }).click();
  await expect(page).toHaveURL(/\/incidents\/inc-demo-0001/, { timeout: 15_000 });

  await page.getByRole('button', { name: 'Start Diagnosing Pipeline' }).click();
  await expect(page.locator('.badge-state', { hasText: 'State: WAITING PATCH APPROVAL' })).toBeVisible({ timeout: 20_000 });

  await page.locator('#reason-input').fill('Approve the exact bounded patch for deterministic verification.');
  await page.getByRole('button', { name: /Approve & Execute Patch/ }).click();

  await expect(page.locator('.badge-state', { hasText: 'State: WAITING PR APPROVAL' })).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText('✅ Verification Passed', { exact: true })).toBeVisible();

  const response = await request.get('http://127.0.0.1:8001/api/v1/incidents/inc-demo-0001/verifications');
  expect(response.ok()).toBeTruthy();
  const runs = await response.json();
  expect(runs).toHaveLength(1);
  expect(runs[0].passed).toBe(true);
  expect(runs[0].checks.map((check: { name: string; passed: boolean }) => check.name)).toEqual(
    expect.arrayContaining(['targeted_test', 'test', 'lint', 'typecheck', 'regression_test', 'risk_review']),
  );
  expect(runs[0].checks.every((check: { passed: boolean }) => check.passed)).toBe(true);
});
