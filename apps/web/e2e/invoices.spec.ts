import { test, expect } from '@playwright/test';

test.describe('Dashboard - Invoices', () => {
  test('should load invoices page', async ({ page }) => {
    await page.goto('/dashboard/invoices');
    expect(page.locator('[data-testid="invoices-page"]')).toBeTruthy();
    expect(page.locator('text=Invoices')).toBeTruthy();
  });

  test('should display invoice list', async ({ page }) => {
    await page.goto('/dashboard/invoices');
    // Should show either empty state or invoice cards once loading resolves.
    // Use an auto-retrying assertion instead of an immediate check to avoid
    // racing the async fetch (loading -> empty/list) that happens on mount.
    const emptyState = page.locator('text=No invoices found');
    const invoiceCard = page.locator('[data-testid*="invoice-card-"]');

    await expect(emptyState.or(invoiceCard.first())).toBeVisible();
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
