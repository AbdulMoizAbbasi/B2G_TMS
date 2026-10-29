# JazzRadar / B2G TMS — System Architecture

**Review status:** source-based architecture description, inspected 29 October 2026. This document describes the repository configuration and implementation; it does not establish how any deployed environment is configured.

## Purpose and scope

JazzRadar / B2G Tender Management System collects procurement-tender data, scores and stores it, and provides authenticated users with tender review, assignment, participation, and reporting workflows. This document covers the React web application, FastAPI API, MariaDB persistence, in-process scrapers, file-based scraper checkpoints, and integrations visible in source.

Local document downloading and local-file retrieval API routes have been removed from the current source. Tender URLs and `TenderDocument` metadata remain in the schema and application responses. Existing files may remain in `data`; tender deletion retains guarded cleanup behavior.

## Components and communication

```mermaid
flowchart LR
  subgraph Host[Host running local Docker Compose]
    subgraph Compose[Compose default network]
      Browser[User browser]
      subgraph Front[frontend service]
        React[React SPA\nVite build]
        Nginx[Nginx\nport 80]
      end
      subgraph Back[backend service]
        API[FastAPI + Uvicorn\nport 8000]
        Scrapers[In-process scraper\nportal adapters + orchestration]
        State[Mounted ./data\ncheckpoints + retained files]
      end
      subgraph DBService[mariadb service]
        DB[(MariaDB 10.11\nmariadb_data volume)]
      end
    end
    HostData[Host ./data directory]
  end
  Portals[External procurement portals]
  Flow[Power Automate flow\nconfigured endpoint]
  Alert[External alert consumer]

  Browser -->|HTTP :80 in Compose config| Nginx
  Nginx -->|HTTP proxy /api/*| API
  API -->|SQLAlchemy + PyMySQL| DB
  API -->|trigger and execute| Scrapers
  Scrapers -->|HTTP(S) portal requests| Portals
  Scrapers -->|tender, relevance, metadata writes| DB
  API <-->|checkpoint read/write; delete cleanup| State
  State --- HostData
  API -->|HTTP POST, configured URL| Flow
  Alert -->|service-key protected request| API
```

The diagram represents only connections confirmed by repository code and Compose configuration. The alert consumer is a logical external caller: the repository defines a service-key-protected endpoint but does not define that caller as a Compose service. The Power Automate endpoint is configured at runtime; the external service and its network placement are not present in the repository.

## Technology and responsibilities

| Component | Source evidence | Responsibility |
|---|---|---|
| Web UI | `frontend/src/App.jsx`, `frontend/src/auth/AuthContext.jsx`, `frontend/src/api.js` | React routes, login/lock state, role-aware presentation, bearer-token API requests. |
| Web server / proxy | `frontend/Dockerfile`, `frontend/nginx.conf` | Serves built static assets and proxies `/api/` to `backend:8000`. Configured for HTTP port 80. |
| API | `backend/main.py`, `backend/auth.py` | Authentication/session enforcement, authorization, tender and workflow endpoints, scraper trigger/import, and Power Automate request. |
| ORM / database driver | `backend/requirements.txt`, `backend/database/connection.py` | SQLAlchemy sessions and PyMySQL connection to MariaDB. |
| Database | `docker-compose.yml`, `database/jazzworld_b2g.sql`, `backend/database/models/` | User, role, tender, region, participation, employee, document metadata, and session records. |
| Scrapers | `backend/tender_scraper/scrapers/`, `orchestrator_tenderfetch.py` | Collect records from Federal, Punjab, Balochistan, KP, and Sindh procurement sources. |
| Mapping and storage | `storage/db_mapper.py`, `storage/normalizer.py`, `storage/mysql_storage.py` | Normalize/map scraped data, calculate/persist relevance, upsert tender data and document metadata. |
| Runtime state | `backend/config/paths.py`, `storage/checkpoint.py` | Checkpoint JSON and retained data under configured `DATA_DIR` (mounted as `./data` by Compose). |

## Request and processing paths

- Browser requests go to the frontend service; Axios attaches a bearer token from `localStorage`. Nginx proxies `/api/*` to FastAPI.
- FastAPI opens database sessions through `database.connection.SessionLocal` and `get_db()`.
- The admin scraper endpoint schedules the orchestration function as a FastAPI `BackgroundTasks` task in the backend process. It is not a separate Compose worker or durable queue.
- A separate admin-only import endpoint accepts Punjab/Balochistan records and calls local import processors.
- The coordinator assignment-email endpoint posts tender and assignment details to the configured Power Automate URL.
- The internal pending-participation endpoint is protected by `ALERT_SERVICE_KEY`; the caller is not implemented in this repository.

## Persistence

MariaDB uses the named Compose volume `mariadb_data`. Compose mounts `database/jazzworld_b2g.sql` into the MariaDB initialization directory, which is an initialization mechanism and does not automatically migrate an existing data volume. The authentication-session addition has a manual SQL migration at `database/migrations/001_add_auth_sessions.sql`; no migration runner is shown in the dependencies or startup path.

The backend mounts host `./data` at `/app/data`. The application uses it for checkpoint state; existing document files may also remain there. The former local document download and retrieval endpoints are absent. Database records retain document URLs and metadata; deletion code checks that historical file paths resolve under the document directory before deleting.

## Trust boundaries and assumptions

1. **Browser to web tier:** Compose exposes HTTP on port 80. The source does not configure TLS termination. Any external TLS proxy is unverified.
2. **Web tier to API:** Nginx uses HTTP to `backend:8000` on the Compose network. Compose also publishes port 8000 on the host, allowing a path that can bypass Nginx unless host/network controls prevent it.
3. **API to database:** API connects over the Compose network. No database TLS options are visible in SQLAlchemy configuration. MariaDB has no host-published port in the Compose file.
4. **Backend to procurement sources:** portal requests are outbound and rely on remote data. The Sindh scraper has an embedded Basic Authorization value; the Punjab custom TLS adapter disables certificate and hostname verification. One scraper uses an HTTP source.
5. **Backend to Power Automate:** flow URL is read from `POWER_AUTOMATE_FLOW_URL`; network restrictions, TLS policy, and service-side controls are outside this repository.
6. **External alert consumer to API:** access relies on a shared `ALERT_SERVICE_KEY`; caller identity, key storage, rotation, and network restrictions are not verified.

## Current deployment configuration and limitations

`docker-compose.yml` defines `backend`, `frontend`, and `mariadb`. The backend publishes `8000:8000`; frontend publishes `80:80`; MariaDB has no published host port. The services share Compose networking. Docker image tags are not pinned by digest. The backend Dockerfile does not declare a non-root `USER`.

FastAPI is instantiated without disabling its default OpenAPI/docs routes. Nginx config has no TLS listener or security-header policy. CORS in `backend/main.py` allows the Vite development origin `http://localhost:5173`; this is not a production-origin configuration.

Infrastructure isolation, deployed firewall rules, external TLS, database grants, secret-store configuration, storage encryption, backup/recovery, monitoring, and environment segregation require operator evidence. They are not inferred from this local Compose configuration. No Jazz Secure SDLC policy document was found in the repository; policy-specific compliance remains pending authoritative ISG review.

## Related documentation

- [System flows](system-flows.md)
- [Deployment and network security](deployment-and-network-security.md)
- [Authentication and access control](authentication-and-access-control.md)
- [API authorization matrix](api-authorization-matrix.md)
- [Threat model and risk register](threat-model-and-risk-register.md)
