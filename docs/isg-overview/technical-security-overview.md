# JazzRadar / B2G Tender Management System — Technical Security Overview

## Authentication and access control

- Passwords are hashed and verified with bcrypt (`backend/auth.py`). Passwords are not stored as plaintext by the application.
- Access tokens are JWTs signed with HS256. The configured signing key is validated for presence, placeholder values, and minimum length; the token lifetime is 60 minutes (`backend/auth.py`). No key value is included here.
- Each new login creates a server-side record in `auth_sessions`, linked to a user. The backend validates the JWT session identifier, revocation state, idle age, and account status on protected requests (`backend/main.py`, `backend/database/models/auth_session.py`).
- Server and frontend inactivity controls use a five-minute idle period. The frontend sends throttled activity signals after browser interaction; ordinary API calls do not extend server-side idle time. Reauthentication verifies the password, revokes the previous session, and returns a replacement token. Logout revokes the current session.
- Roles include `ADMIN`, `COORDINATOR`, and `VIEWER`. Backend dependencies enforce role checks; coordinator-specific operations also use coordinator-region assignments. UI route visibility is not the authorization boundary.
- These controls do not establish a formal login lockout policy; none is claimed in this overview.

## Data and storage

MariaDB stores users and password hashes, roles, coordinator/region records, tenders, source URLs, document metadata, assignments, participation decisions, relevance data, and server-side authentication sessions. Compose persists database files in the named `mariadb_data` volume. The backend also mounts `./data` for application state such as scraper checkpoints. Application source retains external document URLs and metadata; the local document-download and retrieval routes have been retired.

Database encryption at rest: **not verified**. Database connection encryption: **not verified**. Backup encryption, retention, access restrictions, and restore testing: **not verified**.

## Cryptography and transport distinctions

| Control | Evidence and boundary |
| --- | --- |
| Password protection | bcrypt password hashing in backend authentication code. Hashing is one-way password storage protection, not encryption. |
| JWT integrity | HS256 signing and verification using configured `JWT_SECRET_KEY`; signing provides integrity/authenticity, not token confidentiality. |
| Browser/API transport | Checked-in Nginx listens on port 80 and proxies `/api/` to FastAPI over HTTP. Compose publishes port 80 and backend port 8000. HTTPS/TLS at the deployment boundary: **not verified**. |
| Database transport | SQLAlchemy/PyMySQL connects to MariaDB; repository configuration does not establish TLS for that connection. Database connection encryption: **not verified**. |
| Data at rest | Compose declares a MariaDB named volume and host-mounted application data. Repository configuration does not establish volume or filesystem encryption. Database encryption at rest: **not verified**. |

The local configuration does not prove which ports or services are reachable in any deployed environment.

## Technology and integrations

React and React Router provide the browser application; Axios calls a FastAPI/Python 3.12 API served by Uvicorn. SQLAlchemy and PyMySQL connect to MariaDB 10.11. Scraper modules use Python HTTP/HTML tooling to retrieve and map data from Federal PPRA, Punjab PPRA, Balochistan PPRA, KP PPRA, and Sindh PPRA. An administrator-triggered scraper runs in a FastAPI background task. The coordinator assignment-email endpoint sends a payload to Power Automate using a configured flow URL.

## Current repository deployment configuration

Docker Compose defines frontend, backend, and MariaDB services. Nginx publishes port 80; FastAPI publishes port 8000; MariaDB has no host port mapping in the Compose file. Nginx serves the built React app and proxies `/api/` to the backend over the Compose network. The backend uses a host-mounted `./data` directory; MariaDB uses a named volume and an initialization SQL mount. FastAPI's default OpenAPI/docs routes are enabled in source. The backend container does not declare a non-root user. These statements describe repository configuration only, not runtime deployment state.

## External integrations

- Procurement portals provide source tender information to scraper clients.
- Power Automate receives assignment notification payloads, including tender and source/document URL fields.
- An internal pending-participation alerts API is protected by a configured service-key header.

No conclusion about the security posture, availability, or ownership of external services is inferred from these integrations. This overview is for initial technical discussion and does not claim that the application is fully secure, OWASP compliant, or ISG approved.
