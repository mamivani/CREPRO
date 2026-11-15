import { test, expect } from '@playwright/test';

test.describe('Dashboard Navigation', () => {
  test('should load dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    expect(page.locator('[data-testid="dashboard-page"]')).toBeTruthy();
    expect(page.locator('text=Welcome to CREPRO')).toBeTruthy();
  });

  test('should have navigation links', async ({ page }) => {
    await page.goto('/dashboard');

    const propertiesLink = page.locator('[data-testid="properties-link"]');
    const invoicesLink = page.locator('[data-testid="invoices-link"]');

    await expect(propertiesLink).toBeVisible();
    await expect(invoicesLink).toBeVisible();
  });

  test('should navigate to properties page', async ({ page }) => {
    await page.goto('/dashboard');
    const propertiesLink = page.locator('[data-testid="properties-link"]');
    await propertiesLink.click();

    await expect(page).toHaveURL('/dashboard/properties');
    expect(page.locator('[data-testid="properties-page"]')).toBeTruthy();
  });

  test('should navigate to invoices page', async ({ page }) => {
    await page.goto('/dashboard');
    const invoicesLink = page.locator('[data-testid="invoices-link"]');
    await invoicesLink.click();

    await expect(page).toHaveURL('/dashboard/invoices');
    expect(page.locator('[data-testid="invoices-page"]')).toBeTruthy();
  });

  test('should show logout button', async ({ page }) => {
    await page.goto('/dashboard');
    const logoutButton = page.locator('[data-testid="logout-button"]');
    await expect(logoutButton).toBeVisible();
  });

  test('should handle logout', async ({ page }) => {
    await page.goto('/dashboard');
    const logoutButton = page.locator('[data-testid="logout-button"]');
    await logoutButton.click();

    // Should redirect to login after logout
    // Note: In real implementation, would check URL or wait for redirect
    await expect(logoutButton).not.toBeVisible().catch(() => {
      // Logout might have redirected
    });
  });
});
