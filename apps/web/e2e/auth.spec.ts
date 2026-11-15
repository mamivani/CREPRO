import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should load login page', async ({ page }) => {
    await page.goto('/auth/login');
    expect(page.locator('text=Login to CREPRO')).toBeTruthy();
  });

  test('should have OAuth buttons', async ({ page }) => {
    await page.goto('/auth/login');

    const microsoftButton = page.locator('[data-testid="microsoft-login"]');
    const googleButton = page.locator('[data-testid="google-login"]');
    const appleButton = page.locator('[data-testid="apple-login"]');

    await expect(microsoftButton).toBeVisible();
    await expect(googleButton).toBeVisible();
    await expect(appleButton).toBeVisible();
  });

  test('should have local login form', async ({ page }) => {
    await page.goto('/auth/login');

    const emailInput = page.locator('[data-testid="email-input"]');
    const passwordInput = page.locator('[data-testid="password-input"]');
    const submitButton = page.locator('[data-testid="local-login-button"]');

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(submitButton).toBeVisible();
  });

  test('should validate email input', async ({ page }) => {
    await page.goto('/auth/login');

    const emailInput = page.locator('[data-testid="email-input"]');
    const passwordInput = page.locator('[data-testid="password-input"]');

    await emailInput.fill('invalid-email');
    await passwordInput.fill('password123');

    // HTML5 validation should prevent submission
    const form = page.locator('[data-testid="local-login-form"]');
    const isValid = await form.evaluate((el: HTMLFormElement) => el.checkValidity());

    expect(isValid).toBe(false);
  });

  test('should accept valid email', async ({ page }) => {
    await page.goto('/auth/login');

    const emailInput = page.locator('[data-testid="email-input"]');
    const passwordInput = page.locator('[data-testid="password-input"]');

    await emailInput.fill('user@example.com');
    await passwordInput.fill('password123');

    const form = page.locator('[data-testid="local-login-form"]');
    const isValid = await form.evaluate((el: HTMLFormElement) => el.checkValidity());

    expect(isValid).toBe(true);
  });
});
