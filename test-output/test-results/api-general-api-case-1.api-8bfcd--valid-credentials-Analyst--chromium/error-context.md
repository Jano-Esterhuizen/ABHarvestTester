# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: api\general-api-case-1.api.spec.ts >> API Tests >> API-1: POST /api/auth/login with valid credentials (Analyst)
- Location: tests\api\general-api-case-1.api.spec.ts:52:7

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
  5  | let directorToken: string;
  6  | let pmToken: string;
  7  | let analystToken: string;
  8  | 
  9  | test.beforeAll(async ({ request }) => {
  10 |   const directorResponse = await request.post(`${BASE_URL}/api/auth/login`, {
  11 |     data: { username: 'director@abmail.co.za', password: 'Test1234' },
  12 |   });
  13 |   directorToken = await directorResponse.json().then(data => data.token);
  14 | 
  15 |   const pmResponse = await request.post(`${BASE_URL}/api/auth/login`, {
  16 |     data: { username: 'pm@abmail.co.za', password: 'Test1234' },
  17 |   });
  18 |   pmToken = await pmResponse.json().then(data => data.token);
  19 | 
  20 |   const analystResponse = await request.post(`${BASE_URL}/api/auth/login`, {
  21 |     data: { username: 'analyst@abmail.co.za', password: 'Test1234' },
  22 |   });
  23 |   analystToken = await analystResponse.json().then(data => data.token);
  24 | });
  25 | 
  26 | test.describe('API Tests', () => {
  27 | 
  28 |   test('API-1: POST /api/auth/login with valid credentials (Director)', async ({ request }) => {
  29 |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  30 |       data: { username: 'director@abmail.co.za', password: 'Test1234' },
  31 |     });
  32 |     expect(response.status()).toBe(200);
  33 |     expect.soft(await response.json()).toHaveProperty('token');
  34 |   });
  35 | 
  36 |   test('API-1: POST /api/auth/login with invalid credentials', async ({ request }) => {
  37 |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  38 |       data: { username: 'wrong@user.com', password: 'WrongPassword' },
  39 |     });
  40 |     expect(response.status()).toBe(401);
  41 |     expect.soft(await response.json()).toHaveProperty('message');
  42 |   });
  43 | 
  44 |   test('API-1: POST /api/auth/login with valid credentials (Project Manager)', async ({ request }) => {
  45 |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  46 |       data: { username: 'pm@abmail.co.za', password: 'Test1234' },
  47 |     });
  48 |     expect(response.status()).toBe(200);
  49 |     expect.soft(await response.json()).toHaveProperty('token');
  50 |   });
  51 | 
  52 |   test('API-1: POST /api/auth/login with valid credentials (Analyst)', async ({ request }) => {
  53 |     const response = await request.post(`${BASE_URL}/api/auth/login`, {
  54 |       data: { username: 'analyst@abmail.co.za', password: 'Test1234' },
  55 |     });
> 56 |     expect(response.status()).toBe(200);
     |                               ^ Error: expect(received).toBe(expected) // Object.is equality
  57 |     expect.soft(await response.json()).toHaveProperty('token');
  58 |   });
  59 | 
  60 | });
  61 | 
```