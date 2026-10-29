# JazzRadar / B2G TMS — Threat Model and Risk Register

**Assessment basis:** source inspection of the current `main` working tree, OWASP ASVS 5.0.0 selected Level 2 application-control subset, and OWASP Top 10:2025 risk categories. This is a lightweight engineering assessment, not a penetration test or formal ASVS verification. See [ASVS 5.0.0](https://asvs.owasp.org/downloads/) and [OWASP Top 10:2025](https://top10.owasp.org/2025/).

## Scope, assets, and trust boundaries

**Assets:** user credentials and session rows; tender and raw source data; business participation decisions and employee assignments; document URLs/metadata and retained files; checkpoints; integration credentials and configuration; service availability and scraper integrity.

**Actors:** unauthenticated internet/local-network client; authenticated viewer; coordinator scoped to a region; administrator with broad write/configuration powers; external procurement portal; scraper import submitter using admin authorization; service-key holder; Power Automate flow; deployment/database operator.

**Boundaries:** browser ↔ Nginx; Nginx ↔ FastAPI; FastAPI ↔ MariaDB; backend ↔ public procurement sites; backend ↔ Power Automate; external alert caller ↔ service-key endpoint; backend container ↔ mounted host data directory. Trust in the proxy, network policies, production secrets, and external services is not established by source.

## Threat scenarios

1. An attacker steals a browser bearer token through script execution or insecure transport and calls APIs directly.
2. A lower-privileged user attempts to read or mutate another region’s tenders, employees, or workflow decisions by changing IDs in API requests.
3. Poisoned or malformed portal/import data corrupts tender records, checkpoint progress, or user-visible links.
4. Source-embedded Sindh scraper authentication is recovered from source/history and reused against the portal.
5. A network attacker impersonates the Punjab procurement site because its scraper adapter disables certificate and hostname validation.
6. A public client reaches the backend’s published host port or public FastAPI docs if infrastructure does not restrict them.
7. A service-key leak enables access to cross-region pending-participation reports.
8. Failures, concurrent scraper jobs, or per-record commits produce partial data or stale checkpoints.
9. Local historical files/checkpoints are exposed or lost through host permissions, inadequate backup, or uncontrolled volume access.

## Risk register

| ID | Severity | Finding / evidence | OWASP mapping | Mitigation | Residual risk / status |
|---|---|---|---|---|---|
| R1 | High | Sindh scraper includes a hard-coded Basic Authorization credential in `backend/tender_scraper/scrapers/sindh.py`; it is used by the active tender-list scraper and passed through its request session. | ASVS configuration/secret management; Top 10 A02, A04, A07 | Treat as disclosed; rotate/replace at the source service; load from a secret store/runtime configuration; validate presence and redact logs. | **Open.** Rotation, ownership, access history and whether the credential remains valid require owner evidence. |
| R2 | High | Punjab `LegacyTLSAdapter` sets `check_hostname=False` and `verify_mode=CERT_NONE` in `backend/tender_scraper/scrapers/punjab.py`; its GET/POST scraper calls use this adapter. | ASVS communications security; Top 10 A04, A07 | Restore hostname/certificate verification. Prefer default `requests` trust behavior; if custom legacy TLS is required, load a trusted CA bundle and preserve only validated compatibility settings. | **Open.** No live portal handshake or CA-chain validation was performed. |
| R3 | High | Compose publishes backend `8000:8000`; Nginx and Compose configure HTTP only; FastAPI default docs/OpenAPI routes are enabled. | ASVS deployment/configuration; Top 10 A02 | Restrict backend to trusted proxy/private network, terminate TLS, configure security headers, and disable/protect docs for deployed environments. | **Not verified beyond repository config.** Actual firewall, proxy, TLS, and host exposure are unknown. |
| R4 | High | `ScraperImportRequest` accepts a string portal and list of arbitrary dictionaries without visible size/count limits; no global rate-limiting middleware was found. | ASVS validation/API; Top 10 A06, A10 | Add request-body and record-count limits at app and edge; validate fields; rate-limit login and expensive API functions. | **Open in source.** Effective upstream limits unknown. |
| R5 | Low (residual compatibility) | Previously identified server-side document-download/retrieval routes and downloader module were removed from current source; no in-repository frontend caller existed. | ASVS file/API handling; prior risk related to Top 10 A06, A10 | Keep retired routes absent; preserve URLs/metadata and safe historical file cleanup. Inventory external callers before considering retirement complete operationally. | **Removed in current code.** Existing files/metadata remain; unknown external integrations are not verified. |
| R6 | Medium | Browser bearer token is stored in `localStorage` in `frontend/src/auth/AuthContext.jsx`; frontend lock hides UI but only the backend session check enforces idle expiry. | ASVS authentication/session; Top 10 A07 | Maintain XSS defenses, secure transport, token/session monitoring; evaluate storage strategy and CSP. | **Partial.** Backend 5-minute idle sessions/revocation are tested; XSS/production TLS are not. |
| R7 | Medium | Internal alerts endpoint protects cross-region alert data with a shared `ALERT_SERVICE_KEY` and direct string comparison; caller/network restrictions are not in repository. | ASVS authentication/configuration; Top 10 A01, A04, A07 | Rotate/store key securely; restrict endpoint network path; consider constant-time comparison and service identity/token; audit requests. | **Not verified.** Secret management and caller controls require operator evidence. |
| R8 | Medium | Scraper locks/status are process-local; persistence commits inside `persist_tender()` per record, with checkpoint update later. | ASVS secure design/integrity; Top 10 A06, A08, A10 | Use single worker/leader coordination or durable job lock if horizontally scaled; record partial runs and define idempotent recovery. | **Known design boundary.** Single-instance local Compose does not show the production scale. |
| R9 | Medium | No repository evidence of dependency/image scanning, SBOM, third-party annual penetration test, or formal code-review controls. Image tags are not pinned by digest. | ASVS verification/deployment; Top 10 A03 | Add pipeline scanning and image provenance; obtain and track independent testing and remediation. | **Not verified.** Requires CI, vendor, and organizational records. |
| R10 | Medium | No production TLS/database TLS/storage encryption, backup schedule, restore test, or log-retention configuration is visible. | ASVS communications/data protection/logging; Top 10 A02, A04, A09 | Supply and verify platform controls; back up MariaDB and mounted `data`; redact secrets/URLs and monitor auth/admin activity. | **Not verified.** Infrastructure/operations evidence required. |
| R11 | Low–Medium | Existing deletion code contains a resolved-path guard before deleting historical document files; test confirms an outside path is retained. Local download write path no longer exists in current production source. | ASVS file handling; Top 10 A01, A10 | Retain the guard and regression test; assess historical files/metadata lifecycle separately. | **Partial.** Existing database path integrity and symlink/host ACL conditions are not proven. |

## OWASP mapping boundary

The chosen baseline is a targeted **ASVS 5.0.0 Level 2 subset** appropriate for authenticated tender and employee workflows. Relevant areas include architecture/configuration, authentication/session, access control, validation/encoding, injection prevention, cryptography, error handling/logging, file handling, API protection, and verification. OWASP Top 10:2025 is used as an awareness/risk taxonomy. Neither mapping establishes ASVS certification or OWASP compliance.

| OWASP Top 10:2025 category | JazzRadar source-based mapping |
|---|---|
| A01 Broken Access Control | R6–R7; route matrix and cross-region test gaps. |
| A02 Security Misconfiguration | R1, R3, R7, R9; embedded credential, docs/ports/HTTP, service-key and image controls. |
| A03 Software Supply Chain Failures | R9; no scan/SBOM evidence and mutable image tags. |
| A04 Cryptographic Failures | R1–R3, R7, R10; embedded credential, disabled verification, absent configured transport/storage encryption. |
| A05 Injection | No specific SQL injection finding was confirmed in this read-only assessment; ORM use is common in reviewed paths. Dynamic query coverage and security scanning remain unverified. |
| A06 Insecure Design | R4, R8; unbounded import behavior in source and process-local/per-record scraper behavior. The former downloader finding is retired in current code (R5). |
| A07 Authentication Failures | R1, R2, R6–R7; portal credential exposure, TLS peer authentication, browser token storage, service-key controls. |
| A08 Software or Data Integrity Failures | R8; partial batch persistence and file-based checkpoints are separate from DB transactions. |
| A09 Security Logging and Alerting Failures | R10; operational logging, redaction, retention, and alerting evidence is unavailable. |
| A10 Mishandling of Exceptional Conditions | R4, R8, R10; bounded request handling, partial import recovery, and operational failure monitoring require further verification. |

## Highest-priority actions

1. Rotate and externalize the Sindh scraper credential.
2. Restore verified TLS for Punjab portal requests and verify CA trust without live testing in this documentation task.
3. Define the production network edge: TLS, backend-port restriction, docs policy, database network/access controls.
4. Bound imports and expensive requests; add rate limits and direct API tests.
5. Obtain security assurance evidence: CI scans, SBOM, annual independent penetration test, review approvals, backup/restore and monitoring controls.
