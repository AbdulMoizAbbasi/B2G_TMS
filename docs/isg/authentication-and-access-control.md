# JazzRadar / B2G TMS — Authentication and Access Control

## Passwords and tokens

`backend/auth.py` hashes passwords with bcrypt (`bcrypt.hashpw` and generated salt) and verifies them with `bcrypt.checkpw`. Login compares the supplied username and password and rejects inactive accounts. No login lockout or rate-limit implementation was found in the inspected routes; do not assume one exists outside the repository.

JWTs use HS256, include user ID (`sub`), username, role, session ID (`sid`), issue time, and expiry, and retain a 60-minute lifetime. `validate_jwt_secret()` loads project-root `.env` without overriding existing environment values and rejects missing, empty, known placeholder, or under-32-byte keys. JWT payloads are signed, not encrypted. The application does not persist bearer tokens themselves.

## Server-side session lifecycle

`AuthSession` in `backend/database/models/auth_session.py` stores a unique session ID, user ID, creation time, server-recorded last activity, and revocation time/reason. `database/migrations/001_add_auth_sessions.sql` creates the table and indexes. The migration is manual; existing DB volumes require explicit migration and are not updated by changing the schema dump.

`get_current_user()` decodes the JWT, requires a session ID, loads the user, rejects inactive/missing users, and checks that the corresponding session exists, is not revoked, and has not been idle for 300 seconds. Existing tokens without `sid` require a fresh login. JWT expiry remains 60 minutes.

Only `POST /api/auth/activity` updates activity. The endpoint accepts an empty body, takes no client timestamp, and uses an atomic conditional update so an expired/revoked session is not revived. Regular protected requests and polling do not extend server-side activity.

`POST /api/auth/reauthenticate` verifies the submitted password for an active user, conditionally revokes the old session, then inserts a new session and issues a replacement JWT. Incorrect passwords do not update activity. The old token is rejected on later protected requests. A JWT that has itself expired cannot be used for reauthentication; ordinary login is required. `POST /api/auth/logout` revokes a still-valid session and returns success; the frontend clears local state without waiting for that request to complete.

## Frontend lock and token handling

`frontend/src/auth/AuthContext.jsx` tracks pointer, click, keyboard, touch, wheel, and scroll events; it throttles backend activity calls and checks elapsed time on tab visibility changes. `ProtectedRoute.jsx` wraps protected routes and shows `LockScreen.jsx` while locked. Reauthentication replaces the browser token and clears lock state while preserving the mounted route where possible. Axios in `frontend/src/api.js` attaches the token from `localStorage` and broadcasts structured authentication errors. Cross-tab state uses browser storage events.

The frontend lock hides protected UI but is not server enforcement. Backend session checks enforce the timeout. The bearer token is accessible to JavaScript in `localStorage`; an XSS vulnerability could expose it. Browser transport is HTTP in the checked-in Compose/Nginx setup unless external infrastructure adds TLS.

## Roles and authorization

Application roles are `ADMIN`, `COORDINATOR`, and `VIEWER`, backed by `roles` and `users` records. `require_admin`, `require_coordinator`, and `require_viewer` all depend on `get_current_user()`.

- **ADMIN:** user and employee administration; manual tender creation/update/deletion and region assignment; start scraper; inspect scraper status/checkpoint; import supported Punjab and Balochistan scraper payloads.
- **COORDINATOR:** participation updates, tender delegation, and assignment-email workflow. Resource operations check the coordinator’s assigned region and, where implemented, positive relevance. A missing coordinator record is rejected.
- **VIEWER:** read-only role in the UI. Authenticated read endpoints use `get_current_user()` and do not necessarily distinguish viewer from other roles; mutation endpoints apply their own role dependencies.
- **Service integration:** `/api/internal/alerts/pending-participation` uses `ALERT_SERVICE_KEY`, not a user JWT. The route compares the supplied header with configured value; a missing configured value produces an error when called.

Frontend route hiding is not an authorization control. See [API authorization matrix](api-authorization-matrix.md) for route-by-route dependencies and scoping.

## Tests and evidence

`backend/tests/test_auth_sessions.py` covers signing-key validation, login/session issuance and JWT lifetime, idle expiry, activity timing, reauthentication/revocation, invalid and legacy tokens, inactive users, role checks, concurrency races, scraper checkpoint authorization, scraper import authorization, route retirement, URL/metadata persistence, and deletion cleanup. The tests use a temporary SQLite database and a controllable clock for session expiry. They do not establish comprehensive endpoint-by-endpoint role enforcement, production MariaDB migration correctness, frontend lock behavior through browser automation, or external infrastructure settings.

Available prior run record in this workspace: 18 backend tests passed; backend compilation and frontend build passed. `npm run lint` was previously recorded as failing on existing frontend lint errors. These are local test results, not security certification or production evidence.

## Migration and operational caveats

Apply the auth-session SQL migration before deploying code that requires `auth_sessions`; do not recreate a persistent DB volume for this purpose. Existing tokens without session IDs will require login after enforcement is enabled. Session revocation is database-backed; changing the JWT key would invalidate all existing JWT signatures. No key rotation was performed as part of documentation.
