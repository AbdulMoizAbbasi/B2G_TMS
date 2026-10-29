# JazzRadar / B2G TMS — Security Testing and Verification

## Existing automated tests

`backend/tests/test_auth_sessions.py` contains a `unittest` suite using FastAPI `TestClient`, temporary SQLite, and a controllable clock. Test names cover:

- JWT-key validation; login creates a session and preserves the 60-minute token lifetime.
- Protected access before and at idle expiry; ordinary protected calls do not extend activity; activity uses server time and cannot revive an expired session.
- Reauthentication, old-session invalidation, wrong password, expired JWT, missing session claim, revoked session, inactive account, and concurrent activity/reauthentication.
- Role/admin dependency checks and coordinator-region helper behavior.
- Admin-only scraper checkpoint and import authorization/dispatch.
- Retired local document endpoints absent; manual URL/list/detail behavior; scraper URL mapping/persistence; guarded file cleanup during tender deletion.

The test database is SQLite, not MariaDB. These tests do not establish production migration behavior, browser automation behavior, comprehensive authorization coverage for every route/object, live portal TLS, external integration security, or deployment controls. No frontend test script or frontend test framework is configured in `frontend/package.json`.

## Available prior command records

The following results were recorded in this workspace before this documentation task; they were not rerun as part of creating these documents:

| Command | Recorded result | Limitation |
|---|---|---|
| `backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v` | 18 tests passed. | Local regression suite only; does not establish compliance or production security. |
| `backend/.venv/Scripts/python.exe -m compileall -q backend` | Passed. | Syntax/bytecode compilation only. |
| `npm run build` in `frontend/` | Passed. | Build success is not a security test. |
| `git diff --check` | Passed with existing line-ending warnings. | Whitespace/conflict-marker check only. |
| `npm run lint` in `frontend/` | Failed with five errors and one warning in existing `AllTenders.jsx`, `Overview.jsx`, and `TenderDetail.jsx`. | Must be rerun after lint fixes; no frontend tests were run. |

Do not treat these historical results as a sign-off for this release. Retain current CI output for the exact candidate build before approval.

## Test gaps and recommended tests

### API authorization and session controls

- Exercise every route with no token, invalid token, each role, inactive user, and revoked/idle session.
- Add direct object-ID and cross-region tests for list/detail/participation/delegation/overview/employees/document metadata.
- Test missing, invalid, rotated and valid service-key behavior for `/api/internal/alerts/pending-participation`, without exposing keys in output.
- Test login rate limiting and credential error/log redaction when implemented.
- Validate the MariaDB migration on a disposable, isolated CI database; never use production data for destructive migration tests.

### Input and injection

- Test request-body size and tender-count limits, long fields, malformed JSON, unexpected fields, Unicode/encoding boundaries, and unsupported portal values.
- Exercise all dynamic search/sort/filter inputs with SQL-injection payloads and verify parameterized query behavior.
- Check stored external URL schemes and browser link handling.

### Scraper and persistence

- Mock portal responses; test mapping, malformed records, duplicate identity, DB failures, partial batch commits, and checkpoint non-advancement.
- Test import activity limits and admin authorization before any processor invocation.
- Add deterministic TLS-context assertions for Punjab and configured-credential assertions for Sindh; do not use live network targets in unit tests.

### Deployment and assurance

- Run dependency and container-image scans; produce SBOM and retain results with the build.
- Verify TLS, headers, CORS, public port exposure, docs/OpenAPI visibility, database reachability/grants, and container runtime user in the deployment environment.
- Obtain annual independent third-party penetration-test report, retest evidence, and finding closure/acceptance records.
- Test backup restore for MariaDB and mounted runtime files and preserve approved recovery objectives.
