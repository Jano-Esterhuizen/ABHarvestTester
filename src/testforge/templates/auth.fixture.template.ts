import { test as base, Page } from "@playwright/test";
import { getAccountByRole, AccountCredentials } from "../data/credentials/accounts";

type AuthFixtures = {
  authenticatedPage: Page;
  account: AccountCredentials;
};

export const test = base.extend<AuthFixtures & { role: string }>({
  role: ["user", { option: true }],

  account: async ({ role }, use) => {
    const account = getAccountByRole(role);
    await use(account);
  },

  authenticatedPage: async ({ page, account }, use) => {
    await page.goto("${LOGIN_URL}");
    await page.locator("${USERNAME_FIELD}").fill(account.username);
    await page.locator("${PASSWORD_FIELD}").fill(account.password);
    await page.locator("${SUBMIT_BUTTON}").click();
    await page.waitForLoadState("networkidle");
    await use(page);
  },
});

export { expect } from "@playwright/test";
