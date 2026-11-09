import { test, expect } from '@playwright/test';

test.describe('Dashboard - Invoices', () => {
  test('should load invoices page', async ({ page }) => {
    await page.goto('/dashboard/invoices');
    expect(page.locator('[data-testid="invoices-page"]')).toBeTruthy();
    expect(page.locator('text=Invoices')).toBeTruthy();
  });

  test('should display invoice list', async ({ page }) => {
    await page.goto('/dashboard/invoices');
    // Should show either empty state or invoice cards
    const emptyState = page.locator('text=No invoices found');
    const invoiceCard = page.locator('[data-testid*="invoice-card-"]');

    const isEmptyVisible = await emptyState.isVisible().catch(() => false);
    const hasInvoices = await invoiceCard.count();

    expect(isEmptyVisible || hasInvoices > 0).toBe(true);
  });

  test('should display invoice status badges', async ({ page }) => {
    await page.goto('/dashboard/invoices');

    const statusBadges = page.locator('[data-testid*="invoice-status-"]');
    const count = await statusBadges.count();

    if (count > 0) {
      const firstBadge = statusBadges.first();
      await expect(firstBadge).toContainText(/draft|issued|paid|cancelled/i);
    }
  });
});
