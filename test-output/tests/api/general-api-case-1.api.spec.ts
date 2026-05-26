import { expect, test } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

let token: string;

async function login(username: string, password: string, request: any) {
  const response = await request.post(`${BASE_URL}/api/auth/login`, {
    data: {
      username,
      password,
    },
  });
  const body = await response.json();
  return { token: body.token, status: response.status() };
}

test.beforeAll(async ({ request }) => {
  const directorLogin = await login('director@abmail.co.za', 'Test1234', request);
  token = directorLogin.token;
});

test.describe('API Tests', () => {
  test('API-1: Login with valid credentials - Director should succeed', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        username: 'director@abmail.co.za',
        password: 'Test1234',
      },
    });

    expect(response.status()).toBe(200);
    const body = await response.json();
    expect.soft(body).toHaveProperty('token');
  });

  test('API-1: Login with invalid credentials - Should return 401', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        username: 'invalid@abmail.co.za',
        password: 'wrongpassword',
      },
    });

    expect(response.status()).toBe(401);
    const body = await response.json();
    expect.soft(body).toMatchObject({ message: 'Invalid credentials' });
  });
});
