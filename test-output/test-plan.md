Here is the structured test plan covering API, UI, and E2E layers with specific assertions:

### 1. API Tests

| ID  | Method | Endpoint                                     | Role           | Priority | Assertions                                                  |
|-----|--------|----------------------------------------------|----------------|----------|------------------------------------------------------------|
| API-1 | POST   | /api/auth/login                              | Any            | P0       | 1. Should return 200 on valid credentials.<br>2. Should return 401 for invalid credentials.<br>3. Should return 400 for missing fields. |
| API-2 | POST   | /api/auth/logout                             | Any            | P0       | 1. Should return 200 on successful logout.<br>2. Should return 401 if not authenticated. |
| API-3 | POST   | /api/auth/signup                             | Any            | P0       | 1. Should return 201 on successful signup.<br>2. Should return 400 for duplicate email.<br>3. Should return 422 for validation errors. |
| API-4 | GET    | /api/v1/admin/audit-log/export              | admin, director| P0       | 1. Should return 403 for non-authorized roles.<br>2. Should return 200 for authorized roles with valid requests. |
| API-5 | PATCH  | /api/v1/admin/branding                       | admin          | P1       | 1. Should return 403 for non-admin roles.<br>2. Should return 200 for valid request.<br>3. Should return 400 for invalid body. |
| API-6 | PATCH  | /api/v1/admin/organisation                   | admin          | P1       | 1. Should return 200 on success.<br>2. Should return 403 for non-admin.<br>3. Should return 400 for invalid request. |
| API-7 | GET    | /api/v1/admin/roles                          | admin, director| P1       | 1. Should return roles list for authorized users.<br>2. Should return 403 for unauthorized users. |
| API-8 | POST   | /api/v1/admin/users/invite                  | admin          | P1       | 1. Should return 200 on successful invite.<br>2. Should return 400 on duplicate invite. |
| API-9 | GET    | /api/v1/clients                              | Any            | P1       | 1. Should return 200 for valid request.<br>2. Should return 401 if not authenticated. |
| API-10 | POST   | /api/v1/projects                             | Any            | P1       | 1. Should return 201 on successful creation.<br>2. Should return 400 for invalid input. |
| API-11 | GET   | /api/v1/notifications                        | Any            | P2       | 1. Should handle no notifications gracefully (return 200 with an empty array).<br>2. Should return 401 if not authenticated. |
| API-12 | PATCH | /api/v1/clients/:clientId                   | admin, director| P1       | 1. Should return 200 for valid updates.<br>2. Should return 404 if clientId does not exist. |
| API-13 | DELETE | /api/v1/clients/:clientId                   | admin, director| P1       | 1. Should return 204 on successful deletion.<br>2. Should return 404 for non-existent clientId. |
| API-14 | POST   | /api/v1/projects/:projectId/ai/chat/:agentType | Any         | P2       | 1. Should return 400 for unsupported agentType.<br>2. Should return 401 if not authenticated. |

### 2. UI Tests

| ID  | Page                      | Role       | Actions                | Assertions                                                  |
|-----|---------------------------|------------|------------------------|------------------------------------------------------------|
| UI-1 | Login Page                | Any        | Submit valid credentials | 1. Should redirect to dashboard.<br>2. Should show success message. |
| UI-2 | Login Page                | Any        | Submit invalid credentials | 1. Should show error message.<br>2. Should not redirect. |
| UI-3 | Signup Page               | Any        | Submit valid data       | 1. Should redirect to login page<br>2. Should show success message. |
| UI-4 | Client Listing            | admin      | View client details     | 1. Should display client information correctly.<br>2. Should show edit/delete options. |
| UI-5 | Project Creation          | admin      | Fill out form and submit | 1. Should create project and display success notification.<br>2. Should show the new project in listing. |
| UI-6 | Notifications Page        | Any        | Mark all as read        | 1. Should mark notifications as read.<br>2. No unread notifications should appear in the list. |
| UI-7 | Client Form               | admin      | Submit invalid data      | 1. Should show validation errors.<br>2. Should not redirect. |

### 3. E2E Journeys

| ID  | Steps                                                                              | Assertions                                                  |
|-----|------------------------------------------------------------------------------------|------------------------------------------------------------|
| E2E-1 | 1. Go to Login Page <br> 2. Enter valid credentials <br> 3. Click Login          | 1. Should redirect to dashboard.<br>2. User's name shows on the dashboard. |
| E2E-2 | 1. Go to Signup Page <br> 2. Fill out valid signup form <br> 3. Click Signup   | 1. Should redirect to Login page.<br>2. Success notification should be visible. |
| E2E-3 | 1. Login as Admin <br> 2. Go to Clients Page <br> 3. Click on a client entry    | 1. Should redirect to Client details page.<br>2. Client info should be displayed. |
| E2E-4 | 1. Go to Project Creation Page <br> 2. Fill out form <br> 3. Submit           | 1. Should create the project.<br>2. Should redirect to Project Listing.<br>3. New project should be visible. |

### 4. Negative/Security Tests

| ID  | Test Description                                  | Priority | Assertions                                                  |
|-----|--------------------------------------------------|----------|------------------------------------------------------------|
| NEG-1 | Attempt access to /api/v1/admin/audit-log/export without authentication    | P0       | 1. Should return 401 Unauthorized.                         |
| NEG-2 | Attempt to create a role with missing required fields | P1       | 1. Should return 400 for missing fields.                  |
| NEG-3 | Attempt to access /api/v1/clients/:clientId with an unauthorized role | P0       | 1. Should return 403 Forbidden.                            |
| NEG-4 | Attempt to update a non-existent client         | P1       | 1. Should return 404 Not Found.                            |
| NEG-5 | Submit invalid data type in numeric field (e.g. string instead of number) | P2       | 1. Should return 400 for invalid input.                    |
| NEG-6 | Attempt unauthorized actions for various roles (e.g. admin role trying user actions) | P0  | 1. Should return 403 Forbidden for actions not allowed.    |
| NEG-7 | Attempt to hack session by replaying valid requests with an old token | P0       | 1. Should return an error regarding session expiration.     |

This test plan is structured to ensure comprehensive coverage of functionalities focusing on critical areas for validation, performance, security, and proper user experience.