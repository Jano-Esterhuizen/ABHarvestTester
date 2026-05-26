# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: ui\pages-ui-case-1.ui.spec.ts >> UI Tests >> Dashboard Page loads
- Location: tests\ui\pages-ui-case-1.ui.spec.ts:73:9

# Error details

```
TypeError: _pagesUiCase.HomePage is not a constructor
```

# Test source

```ts
  1   | import { expect, test } from '@playwright/test';
  2   | import { ClientsPage } from './pages/pages-ui-case-1.page';
  3   | import { HomePage } from './pages/pages-ui-case-1.page';
  4   | import { LoginPage } from './pages/pages-ui-case-1.page';
  5   | import { DashboardPage } from './pages/pages-ui-case-1.page';
  6   | import { HelpPage } from './pages/pages-ui-case-1.page';
  7   | import { ProjectsPage } from './pages/pages-ui-case-1.page';
  8   | import { ProfilePage } from './pages/pages-ui-case-1.page';
  9   | import { ActionsPage } from './pages/pages-ui-case-1.page';
  10  | import { NewClientPage } from './pages/pages-ui-case-1.page';
  11  | import { AdminPage } from './pages/pages-ui-case-1.page';
  12  | import { PortfolioPage } from './pages/pages-ui-case-1.page';
  13  | 
  14  | // Test Spec for Home, Actions, Admin, Clients, New Client, Dashboard, Help, Login, Portfolio, Profile, Projects
  15  | 
  16  | test.describe('UI Tests', () => {
  17  |     let homePage: HomePage;
  18  |     let actionsPage: ActionsPage;
  19  |     let adminPage: AdminPage;
  20  |     let clientsPage: ClientsPage;
  21  |     let newClientPage: NewClientPage;
  22  |     let dashboardPage: DashboardPage;
  23  |     let helpPage: HelpPage;
  24  |     let loginPage: LoginPage;
  25  |     let portfolioPage: PortfolioPage;
  26  |     let profilePage: ProfilePage;
  27  |     let projectsPage: ProjectsPage;
  28  | 
  29  |     test.beforeEach(async ({ page }) => {
> 30  |         homePage = new HomePage(page);
      |                    ^ TypeError: _pagesUiCase.HomePage is not a constructor
  31  |         actionsPage = new ActionsPage(page);
  32  |         adminPage = new AdminPage(page);
  33  |         clientsPage = new ClientsPage(page);
  34  |         newClientPage = new NewClientPage(page);
  35  |         dashboardPage = new DashboardPage(page);
  36  |         helpPage = new HelpPage(page);
  37  |         loginPage = new LoginPage(page);
  38  |         portfolioPage = new PortfolioPage(page);
  39  |         profilePage = new ProfilePage(page);
  40  |         projectsPage = new ProjectsPage(page);
  41  |     });
  42  | 
  43  |     test('Home Page loads', async ({ page }) => {
  44  |         await homePage.navigate();
  45  |         await homePage.isLoaded();
  46  |         expect(await page.title()).toContain("ProjectControl");
  47  |     });
  48  | 
  49  |     test('Actions Page loads', async ({ page }) => {
  50  |         await actionsPage.navigate();
  51  |         await actionsPage.isLoaded();
  52  |         expect(await page.title()).toContain("Actions");
  53  |     });
  54  |     
  55  |     test('Admin Page loads', async ({ page }) => {
  56  |         await adminPage.navigate();
  57  |         await adminPage.isLoaded();
  58  |         expect(await page.title()).toContain("Admin");
  59  |     });
  60  | 
  61  |     test('Clients Page loads', async ({ page }) => {
  62  |         await clientsPage.navigate();
  63  |         await clientsPage.isLoaded();
  64  |         expect(await page.title()).toContain("Clients");
  65  |     });
  66  | 
  67  |     test('New Client Page loads', async ({ page }) => {
  68  |         await newClientPage.navigate();
  69  |         await newClientPage.isLoaded();
  70  |         expect(await page.title()).toContain("New Client");
  71  |     });
  72  | 
  73  |     test('Dashboard Page loads', async ({ page }) => {
  74  |         await dashboardPage.navigate();
  75  |         await dashboardPage.isLoaded();
  76  |         expect(await page.title()).toContain("Dashboard");
  77  |     });
  78  | 
  79  |     test('Help Page loads', async ({ page }) => {
  80  |         await helpPage.navigate();
  81  |         await helpPage.isLoaded();
  82  |         expect(await page.title()).toContain("Help");
  83  |     });
  84  | 
  85  |     test('Login succeeds for Director', async ({ page }) => {
  86  |         await loginPage.navigate();
  87  |         await loginPage.login('director@abmail.co.za', 'Test1234');
  88  |         expect(await page.title()).toContain("Dashboard");
  89  |     });
  90  | 
  91  |     test('Portfolio Page loads', async ({ page }) => {
  92  |         await portfolioPage.navigate();
  93  |         await portfolioPage.isLoaded();
  94  |         expect(await page.title()).toContain("Portfolio");
  95  |     });
  96  | 
  97  |     test('Profile Page loads', async ({ page }) => {
  98  |         await profilePage.navigate();
  99  |         await profilePage.isLoaded();
  100 |         expect(await page.title()).toContain("Profile");
  101 |     });
  102 | 
  103 |     test('Projects Page loads', async ({ page }) => {
  104 |         await projectsPage.navigate();
  105 |         await projectsPage.isLoaded();
  106 |         expect(await page.title()).toContain("Projects");
  107 |     });
  108 | });
  109 | 
```