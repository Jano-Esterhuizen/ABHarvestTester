import { expect, test } from '@playwright/test';

const baseURL = process.env.BASE_URL || 'http://localhost:3000';

const credentials = {
  director: { username: 'director@abmail.co.za', password: 'Test1234' },
  pm: { username: 'pm@abmail.co.za', password: 'Test1234' },
  analyst: { username: 'analyst@abmail.co.za', password: 'Test1234' },
};

let tokens: Record<string, string> = {};

test.beforeAll(async ({ request }) => {
  for (const role in credentials) {
    const response = await request.post(`${baseURL}/api/auth/login`, {
      data: credentials[role as keyof typeof credentials],
    });
    tokens[role] = (await response.json()).token; // Awaiting response.json() to fix type error
  }
});

test.describe('Auth API Tests', () => {
  test('API-1: Should return 200 on valid credentials for any role', async ({ request }) => {
    const response = await request.post(`${baseURL}/api/auth/login`, {
      data: credentials.director,
    });
    expect(response.status()).toBe(200);
    expect.soft((await response.json())).toHaveProperty('token');
  });

  test('API-1: Should return 401 for invalid credentials', async ({ request }) => {
    const response = await request.post(`${baseURL}/api/auth/login`, {
      data: { username: 'wrong@abmail.co.za', password: 'WrongPassword' },
    });
    expect(response.status()).toBe(401);
    expect.soft((await response.json())).toHaveProperty('error');
  });
});
