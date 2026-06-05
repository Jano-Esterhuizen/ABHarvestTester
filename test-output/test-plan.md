### Test Plan for Automation Playground Application

#### 1. API Tests

| ID  | Method | Endpoint           | Role      | Priority | Assertions                                                                                                 |
|-----|--------|--------------------|-----------|----------|------------------------------------------------------------------------------------------------------------|
| API-1 | GET    | /api/cities        | User      | P1       | Should retrieve all cities; response status 200; response contains city list and server instance info.    |
| API-2 | GET    | /api/cities/{id}   | User      | P1       | Valid ID returns city details with 200 status. Invalid ID returns 404.                                    |
| API-3 | POST   | /api/cities        | Admin     | P1       | Successful creation returns 201; validation errors return 400; duplicate cities return 409.                |
| API-4 | DELETE | /api/cities/{id}   | Admin     | P1       | Valid ID should soft delete city; 200 response; non-existent ID returns 404.                              |
| API-5 | GET    | /api/weather       | User      | P1       | Should return all weather data associated with cities; response with 200 status; data correctly formatted. |
| API-6 | GET    | /api/weather/{id}  | User      | P1       | Valid weather ID returns data; invalid ID returns 404.                                                    |
| API-7 | POST   | /api/weather       | Admin     | P1       | Successful creation returns 201; invalid or missing fields return 400; invalid cityId returns 404.        |
| API-8 | DELETE | /api/weather/{id}  | Admin     | P1       | Soft delete operation returns 200; non-existing record returns 404.                                       |
| API-9 | GET    | /health            | System Admin | P0     | Should return healthy status as 200; unhealthy status returns 503.                                        |

#### 2. UI Tests

| ID  | Page                   | Role      | Actions                       | Assertions                                                                                                            |
|-----|------------------------|-----------|-------------------------------|----------------------------------------------------------------------------------------------------------------------|
| UI-1 | City List Page         | User      | Load page                   | Page loads and displays the list of cities; validate data against the API response.                                 |
| UI-2 | City Details Page      | User      | Click on a city             | Details show correct city information; link fetches data from API correctly.                                       |
| UI-3 | Add City Form          | Admin     | Submit valid data           | City is added successfully; success message appears and data is validated via API.                                  |
| UI-4 | Weather Dashboard       | User      | View weather data           | Weather data is displayed; matches API response; includes correct reverse relationships to city info.              |
| UI-5 | Health Check Interface  | System Admin | View health status        | Displays status based on API call; correctly reflects backend health status.                                       |

#### 3. E2E Journeys

| ID  | Steps                                                                         | Assertions                                                                                     |
|-----|-------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------|
| E2E-1 | User logs in -> Navigate to City List Page -> Click on a city -> View details | City details match the API response; proper instance info present; all linked data displayed.  |
| E2E-2 | Admin adds a new city -> Validate on City List Page -> Open Weather Dashboard  | Newly added city appears on the list; weather dashboard updates to show weather for the new city. |
| E2E-3 | User views health check -> React to unhealthy status                        | User receives appropriate feedback; automatic redirects or alerts occur accordingly.           |

#### 4. Negative/Security Tests

| ID  | Test Type          | Description                                                               | Priority | Assertions                                                                                   |
|-----|--------------------|---------------------------------------------------------------------------|----------|----------------------------------------------------------------------------------------------|
| NEG-1 | Input Validation    | Attempt to add city with missing required fields                        | P0       | Should return 400; specific validation error messages provided.                             |
| NEG-2 | SQL Injection       | Attempt SQL injection in city name during POST request                 | P0       | Should be rejected; no database errors; response should sanitize input and return 400.      |
| NEG-3 | Unauthorized Access | Attempt to access API endpoints without authorization                    | P0       | Should return 401 or 403; unauthorized actions must be blocked and logged.                  |
| NEG-4 | Invalid Path        | Request a non-existent API endpoint                                      | P0       | Response status should be 404; should not crash API or reveal unnecessary information.       |
| NEG-5 | Boundary Values     | Test city ID with boundary values (negative, zero, excessively high)   | P1       | Properly handle edge cases; return 400 for negative/zero; return 404 for excessively high IDs. |
| NEG-6 | Duplicate Entry     | Attempt to add a duplicate city that already exists                     | P1       | Should return 409 conflict; respective error message detailing the conflict is shown.        |


This structured test plan prioritizes essential aspects of API, UI, and E2E testing while considering various negative and security tests. Each ID represents a distinct test that contributes to maintaining the robustness and reliability of the Automation Playground application.