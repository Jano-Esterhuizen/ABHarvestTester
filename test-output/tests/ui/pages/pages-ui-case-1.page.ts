import { Page } from '@playwright/test';

// pom/HomePage.ts
export class HomePage {
    // Locators
    constructor(private page: Page) {}

    private loginButton = '[data-testid="login-button"]';
    private errorMessage = '[data-testid="error-message"]';

    // Methods
    async login(username: string, password: string) {
        await this.page.fill('[data-testid="username-input"]', username);
        await this.page.fill('[data-testid="password-input"]', password);
        await this.page.click(this.loginButton);
        await this.page.waitForLoadState('networkidle');
    }

    async getErrorMessage() {
        return await this.page.textContent(this.errorMessage);
    }
}

// pom/ActionsPage.ts
export class ActionsPage {
    private header = '[data-testid="actions-header"]';

    constructor(private page: Page) {}

    async isHeaderVisible() {
        return await this.page.isVisible(this.header);
    }
}

// pom/AdminPage.ts
export class AdminPage {
    private header = '[data-testid="admin-header"]';

    constructor(private page: Page) {}

    async isHeaderVisible() {
        return await this.page.isVisible(this.header);
    }
}

// pom/ClientsPage.ts
export class ClientsPage {
    private header = '[data-testid="clients-header"]';

    constructor(private page: Page) {}

    async isHeaderVisible() {
        return await this.page.isVisible(this.header);
    }
}

// pom/ClientsNewPage.ts
export class ClientsNewPage {
    private saveButton = '[data-testid="save-client"]';
    constructor(private page: Page) {}

    private nameInput = '[data-testid="client-name-input"]';

    async createClient(name: string) {
        await this.page.fill(this.nameInput, name);
        await this.page.click(this.saveButton);
        await this.page.waitForLoadState('networkidle');
    }
}
