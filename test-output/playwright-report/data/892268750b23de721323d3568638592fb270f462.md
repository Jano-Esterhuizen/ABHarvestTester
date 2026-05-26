# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: api\post-api-auth-login-api-case-1.api.spec.ts >> API Tests - Auth >> API-1: Should return 200 on valid credentials for director
- Location: tests\api\post-api-auth-login-api-case-1.api.spec.ts:19:7

# Error details

```
Error: expect(received).toBe(expected) // Object.is equality

Expected: 200
Received: 400
```

# Test source

```ts
  1  | import { expect, test } from '@playwright/test';
  2  | 
  3  | const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
  4  | 
  5  | test.describe('API Tests - Auth', () => {
  6  |   let token: string;
  7  | 
  8  |   test.beforeAll(async ({ request }) => {
  9  |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  10 |       data: {
  11 |         username: 'director@abmail.co.za',
  12 |         password: 'Test1234'
  13 |       }
  14 |     });
  15 |     const json = await response.json();
  16 |     token = json.token;
  17 |   });
  18 | 
  19 |   test('API-1: Should return 200 on valid credentials for director', async ({ request }) => {
  20 |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  21 |       data: {
  22 |         username: 'director@abmail.co.za',
  23 |         password: 'Test1234'
  24 |       }
  25 |     });
> 26 |     expect(response.status()).toBe(200);
     |                               ^ Error: expect(received).toBe(expected) // Object.is equality
  27 |     const body = await response.json();
  28 |     expect.soft(body).toHaveProperty('token');
  29 |   });
  30 | 
  31 |   test('API-1: Should return 401 for invalid credentials', async ({ request }) => {
  32 |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  33 |       data: {
  34 |         username: 'invalid@abmail.co.za',
  35 |         password: 'WrongPassword'
  36 |       }
  37 |     });
  38 |     expect(response.status()).toBe(401);
  39 |   });
  40 | });
  41 | 
```