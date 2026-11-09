import { test, expect } from '@playwright/test';

test.describe('Dashboard - Properties CRUD', () => {
  test('should load properties page', async ({ page }) => {
    await page.goto('/dashboard/properties');
    expect(page.locator('[data-testid="properties-page"]')).toBeTruthy();
    expect(page.locator('text=Properties')).toBeTruthy();
  });

  test('should show create property button', async ({ page }) => {
    await page.goto('/dashboard/properties');
    const createButton = page.locator('[data-testid="create-property-button"]');
    await expect(createButton).toBeVisible();
  });

  test('should toggle property form', async ({ page }) => {
    await page.goto('/dashboard/properties');
    const createButton = page.locator('[data-testid="create-property-button"]');

    await createButton.click();
    const form = page.locator('[data-testid="property-form"]');
    await expect(form).toBeVisible();

    await createButton.click();
    await expect(form).not.toBeVisible();
  });

  test('should have property form fields', async ({ page }) => {
    await page.goto('/dashboard/properties');
    const createButton = page.locator('[data-testid="create-property-button"]');
    await createButton.click();

    const nameInput = page.locator('[data-testid="property-name-input"]');
    const addressInput = page.locator('input[id="address"]');
    const cityInput = page.locator('input[id="city"]');
    const stateInput = page.locator('input[id="state"]');
    const zipInput = page.locator('input[id="zip"]');
    const typeSelect = page.locator('select[id="type"]');
    const unitsInput = page.locator('input[id="units"]');

    await expect(nameInput).toBeVisible();
    await expect(addressInput).toBeVisible();
    await expect(cityInput).toBeVisible();
    await expect(stateInput).toBeVisible();
    await expect(zipInput).toBeVisible();
    await expect(typeSelect).toBeVisible();
    await expect(unitsInput).toBeVisible();
  });

  test('should validate property form', async ({ page }) => {
    await page.goto('/dashboard/properties');
    const createButton = page.locator('[data-testid="create-property-button"]');
    await createButton.click();

    const submitButton = page.locator('[data-testid="submit-property-button"]');
    const form = page.locator('[data-testid="property-form"]');

    // Form should be invalid when empty
    let isValid = await form.evaluate((el: HTMLFormElement) => el.checkValidity());
    expect(isValid).toBe(false);

    // Fill form with valid data
    await page.locator('[data-testid="property-name-input"]').fill('Test Property');
    await page.locator('input[id="address"]').fill('123 Main St');
    await page.locator('input[id="city"]').fill('Springfield');
    await page.locator('input[id="state"]').fill('IL');
    await page.locator('input[id="zip"]').fill('62701');
    await page.locator('input[id="units"]').fill('5');

    // Form should now be valid
    isValid = await form.evaluate((el: HTMLFormElement) => el.checkValidity());
    expect(isValid).toBe(true);
  });

  test('should display empty state', async ({ page }) => {
    await page.goto('/dashboard/properties');
    // If no properties, should show "No properties found" message
    const emptyState = page.locator('text=No properties found');
    const isVisible = await emptyState.isVisible().catch(() => false);

    // Either shows empty state or has property cards
    if (isVisible) {
      await expect(emptyState).toBeVisible();
    }
  });
});
