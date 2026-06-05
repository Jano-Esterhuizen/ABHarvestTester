import { expect, test } from '@playwright/test';

test.describe('API Tests for Automation Playground Application', () => {
  const BASE_URL = 'http://localhost:8000';

  test('API-1: Should retrieve all cities', async ({ request }) => {
    // Arrange
    // Create any necessary data if required (not specified in the test plan)
    
    // Act
    const response = await request.get(`${BASE_URL}/api/cities`);

    // Assert
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('cities');
    expect(body.cities).toBeInstanceOf(Array);
  });

  test('API-2: Should return city details for a given city', async ({ request }) => {
    // Arrange
    const cityId = 1; // Sample city ID, adjust if necessary

    // Act
    const response = await request.get(`${BASE_URL}/api/cities/${cityId}`);

    // Assert
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('city');
    expect(body.city.id).toBe(cityId);
  });
});
