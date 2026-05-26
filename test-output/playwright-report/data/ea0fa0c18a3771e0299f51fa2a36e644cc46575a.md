# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: api\auth-api-case-1.api.spec.ts >> Auth API Tests >> API-1: POST /api/auth/login - Valid credentials for any role
- Location: tests\api\auth-api-case-1.api.spec.ts:24:7

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
  5  | const CREDENTIALS = {
  6  |   director: { username: 'director@abmail.co.za', password: 'Test1234' },
  7  |   pm: { username: 'pm@abmail.co.za', password: 'Test1234' },
  8  |   analyst: { username: 'analyst@abmail.co.za', password: 'Test1234' },
  9  | };
  10 | 
  11 | let tokens: { [key: string]: string } = {};
  12 | 
  13 | test.beforeAll(async ({ request }) => {
  14 |   for (const role in CREDENTIALS) {
  15 |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  16 |       data: CREDENTIALS[role as keyof typeof CREDENTIALS],
  17 |     });
  18 |     const body = await response.json();
  19 |     tokens[role] = body.token;
  20 |   }
  21 | });
  22 | 
  23 | test.describe('Auth API Tests', () => {
  24 |   test('API-1: POST /api/auth/login - Valid credentials for any role', async ({ request }) => {
  25 |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  26 |       data: CREDENTIALS.director,
  27 |     });
  28 | 
> 29 |     expect(response.status()).toBe(200);
     |                               ^ Error: expect(received).toBe(expected) // Object.is equality
  30 |     const body = await response.json();
  31 |     expect.soft(body).toHaveProperty('token');
  32 |   });
  33 | 
  34 |   test('API-1: POST /api/auth/login - Invalid credentials', async ({ request }) => {
  35 |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  36 |       data: { username: 'invalid@abmail.co.za', password: 'wrongpassword' },
  37 |     });
  38 | 
  39 |     expect(response.status()).toBe(401);
  40 |     const body = await response.json();
  41 |     expect.soft(body).toHaveProperty('error', 'Invalid credentials');
  42 |   });
  43 | });
  44 | 
```