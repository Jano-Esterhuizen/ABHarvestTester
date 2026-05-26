import { expect, test } from '@playwright/test';
import { ActionsPage } from './pages/pages-ui-case-1.page';
import { ClientsPage } from './pages/pages-ui-case-1.page';
import { HomePage } from './pages/pages-ui-case-1.page';
import { ClientsNewPage } from './pages/pages-ui-case-1.page';
import { AdminPage } from './pages/pages-ui-case-1.page';

// tests/HomePage.spec.ts

const homePage = new HomePage(page);
const actionsPage = new ActionsPage(page);
const adminPage = new AdminPage(page);
const clientsPage = new ClientsPage(page);
const clientsNewPage = new ClientsNewPage(page);

test.describe('Page Navigation Tests', () => {
    test.beforeAll(async ({ request }) => {
        await homePage.login('director@abmail.co.za', 'Test1234');
    });

    test('should navigate to Actions page and check header', async ({ page }) => {
        await page.goto('http://localhost:3000/actions');
        expect(await actionsPage.isHeaderVisible()).toBeTruthy();
    });

    test('should navigate to Admin page and check header', async ({ page }) => {
        await page.goto('http://localhost:3000/admin');
        expect(await adminPage.isHeaderVisible()).toBeTruthy();
    });

    test('should navigate to Clients page and check header', async ({ page }) => {
        await page.goto('http://localhost:3000/clients');
        expect(await clientsPage.isHeaderVisible()).toBeTruthy();
    });

    test('should create a new client', async ({ page }) => {
        await page.goto('http://localhost:3000/clients/new');
        await clientsNewPage.createClient('New Client');
        expect(await page.url()).toContain('/clients');
    });
});
