import { expect, test } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

test.describe('API Tests for /api/auth/login', () => {
  
  let directorToken: string;
  let pmToken: string;
  let analystToken: string;

  test.beforeAll(async ({ request }) => {
    // Arrange: Login to get tokens for different roles
    const directorResponse = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        username: 'director@abmail.co.za',
        password: 'Test1234'
      }
    });
    directorToken = directorResponse.json().token;

    const pmResponse = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        username: 'pm@abmail.co.za',
        password: 'Test1234'
      }
    });
    pmToken = pmResponse.json().token;

    const analystResponse = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        username: 'analyst@abmail.co.za',
        password: 'Test1234'
      }
    });
    analystToken = analystResponse.json().token;
  });

  test('API-1: Should return 200 on valid credentials for director', async ({ request }) => {
    // Act
    const response = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        username: 'director@abmail.co.za',
        password: 'Test1234'
      }
    });

    // Assert
    expect(response.status()).toBe(200);
    expect.soft(response.json()).toHaveProperty('token');
  });

  test('API-1: Should return 401 for invalid credentials', async ({ request }) => {
    // Act
    const response = await request.post(`${BASE_URL}/api/auth/login`, {
      data: {
        username: 'invalid@abmail.co.za',
        password: 'WrongPassword'
      }
    });

    // Assert
    expect(response.status()).toBe(401);
    expect.soft(response.json()).toHaveProperty('error');
  });
});
