# JazzRadar / B2G TMS — Deployment and Network Security

## Current repository configuration

This is the configuration in `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, and `frontend/nginx.conf`. It is not evidence of the topology or exposure of any deployed system.

| Service | Build/image | Published ports | Communication and storage |
|---|---|---|---|
| `frontend` | Multi-stage Vite build; Nginx Alpine runtime | `80:80` | Nginx serves React assets and proxies `/api/` to `http://backend:8000`. |
| `backend` | Python 3.12 slim; Uvicorn | `8000:8000` | Receives root `.env` through Compose `env_file`; mounts `./data:/app/data`; connects to MariaDB. |
| `mariadb` | MariaDB 10.11 | No host port mapping | Receives database initialization variables; stores data in `mariadb_data`; mounts schema SQL read-only for image initialization. |

Compose creates a default network for these services. The backend port is separately published on the host, so it may be reachable without passing through Nginx unless host firewall/network policy restricts it. MariaDB has no explicit host-published port. Effective reachability is not verified here.

## HTTP, TLS, and API documentation

- Nginx listens on port 80. The checked-in files do not configure HTTPS or TLS termination.
- Nginx proxies to the backend over HTTP inside the Compose network.
- FastAPI is created without custom `docs_url`, `redoc_url`, or `openapi_url` settings, so default `/docs`, `/redoc`, and `/openapi.json` routes are enabled and have no application authentication dependency.
- CORS in `backend/main.py` currently allows the Vite development origin `http://localhost:5173`. It is not a production origin setting.
- No CSP, HSTS, frame, referrer, or MIME-sniffing headers are configured in the provided Nginx file.
- The Punjab scraper disables TLS certificate and hostname verification in `backend/tender_scraper/scrapers/punjab.py`; the Sindh scraper sends a hard-coded Basic Authorization credential in source. These are application-to-portal controls, separate from browser-to-app TLS.

## Configuration categories

Variable names visible in source/example configuration include database connection and MariaDB initialization settings (`DB_*`, `MYSQL_*`), `JWT_SECRET_KEY`, `ALERT_SERVICE_KEY`, `DATA_DIR`, and `POWER_AUTOMATE_FLOW_URL`. No values are documented here. The backend validates `JWT_SECRET_KEY` at import/startup; database configuration checks for required database name and user. The alert key is checked when its route runs. The Power Automate flow URL is checked when its endpoint is called. Sindh scraper credentials are currently source-embedded rather than loaded from a configuration variable.

## Development versus proposed production architecture

**Current repository deployment:** HTTP-only frontend port 80, separately published backend port 8000, MariaDB on the Compose network, one mounted runtime data directory, and environment variables supplied locally. The repository does not establish that this is a production design.

**Production controls requiring deployment design and evidence:**

- Place a managed TLS reverse proxy/load balancer in front of the UI and API; redirect HTTP to HTTPS and use current certificates/protocol settings.
- Restrict backend access to the trusted proxy or private service network; remove public host publication of port 8000 unless explicitly required.
- Keep MariaDB on a private network with no public listener; restrict source/destination rules and use a least-privilege application account.
- Disable or authenticate API docs/OpenAPI where not required by operational users.
- Use a secret manager or protected runtime injection, rotate credentials, and never bake secrets into images or source.
- Set production CORS origins and browser security headers deliberately.
- Run containers with non-root users, minimal capabilities, controlled writable mounts, and pinned/scanned images.
- Define backups, recovery tests, log controls, monitoring, and environment separation.

No firewall rules, production TLS edge, secret manager, network isolation, database grants, or environment separation can be confirmed from these files. Do not treat the Compose port mappings as proof of actual production exposure.

## Migration and initialization note

`database/jazzworld_b2g.sql` is mounted as an initialization script; an existing MariaDB volume is not updated merely because the dump changes. The auth-session table has a separate manual SQL migration. Apply it to a target database using the approved migration/backup process before deploying code that requires the table; do not recreate the volume to apply it. This document task did not apply migrations or connect to a database.
