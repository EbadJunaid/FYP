# API Analysis

## Evidence classification

Routes, view methods, filters, response construction, and missing permission checks are **Verified from repository** (V-018–V-021, V-027, V-028). Concurrency/security impact and runtime failure conclusions are **Inference — approval required** (I-010, I-014–I-016, I-022).

## API conventions

- Base path: `/api/`.
- Format: JSON except CSV export/download endpoints.
- Pagination commonly uses `page` and `page_size`.
- Logical scope is supplied by `scope` query parameter or `X-Certificate-Scope` header.
- There is no API version prefix and no OpenAPI/Swagger specification.
- There is no project-specific authentication or authorization.

## Active endpoint catalog

| Group | Method and path | Purpose/source |
|---|---|---|
| Health | `GET /api/hello/` | Mongo connectivity/count diagnostic; response database label is stale |
| Export | `GET /api/certificates/download/` | streaming filtered CSV |
| Export | `GET /api/certificates/export/` | intended filtered CSV capped at 10,000; currently calls a commented-out/missing model method |
| Legacy/root | `GET /api/validation-distribution/` | validation distribution |
| Legacy/root | `GET /api/vulnerabilities/` | vulnerability response |
| Scope | `GET /api/databases/current/` | active physical pair/logical scope |
| Scope | `GET /api/databases/available/` | global and country scope choices |
| Scope | `POST /api/databases/switch/` | process-global logical scope switch |
| Shared dashboard | `GET /api/shared/global-health/` | health/active/expiry/vulnerability metrics |
| Shared dashboard | `GET /api/shared/validity-trends/` | validity/issuance trends |
| Shared dashboard | `GET /api/shared/ca-analytics/` | CA distribution/leaderboard |
| Shared dashboard | `GET /api/shared/geographic-distribution/` | geographic counts |
| Certificates | `GET /api/shared/certificates/` | paginated, filtered list |
| Certificates | `GET /api/shared/certificates/<id>/` | certificate detail |
| Shared scope | `GET /api/shared/databases/current/` | duplicate current-scope read |
| Shared scope | `GET /api/shared/databases/available/` | duplicate available-scope read |
| Shared scope | `/api/shared/databases/switch/` | implementation is nonfunctional due to GET/POST dispatch mismatch |
| Overview | `GET /api/overview/unique-filters/` | issuer/country/status/grade/validation options |
| Overview | `GET /api/overview/future-risk/` | application-defined projection |
| Overview | `GET /api/overview/encryption-strength/` | algorithm/key-size distribution |
| Overview | `GET /api/overview/vulnerabilities/` | paginated ranked risk view |
| Overview | `GET /api/overview/vulnerablities/` | misspelled alias |
| CA | `GET /api/ca/ca-stats/` | CA metric cards/distribution |
| CA | `GET /api/ca/issuer-validation-matrix/` | CA by DV/OV/EV matrix |
| CA | `GET /api/ca/ranking/` | CA or issuer grouping/ranking |
| Validity | `GET /api/validity/validity-stats/` | summary plus live expiry windows |
| Validity | `GET /api/validity/validity-distribution/` | lifetime buckets |
| Validity | `GET /api/validity/issuance-timeline/` | monthly issuance |
| Signature/hash | `GET /api/signature-hash/signature-stats/` | signature/hash/key statistics |
| Signature/hash | `GET /api/signature-hash/hash-trends/` | quarterly/yearly hash trends |
| Signature/hash | `GET /api/signature-hash/issuer-algorithm-matrix/` | top issuer/algorithm matrix |
| SAN | `GET /api/san/san-stats/` | SAN summary |
| SAN | `GET /api/san/san-distribution/` | SAN size buckets |
| SAN | `GET /api/san/san-tld-breakdown/` | SAN TLD distribution |
| SAN | `GET /api/san/san-wildcard-breakdown/` | wildcard/non-wildcard comparison |
| SAN | `GET /api/san/san-filtered-certs/` | SAN-specific certificate references/details |
| Trends | `GET /api/trends/stats/` | trend summary |
| Trends | `GET /api/trends/expiration-forecast/` | future expiry months |
| Trends | `GET /api/trends/algorithm-adoption/` | algorithm adoption over time |
| Trends | `GET /api/trends/validation-levels/` | validation levels over time |
| Trends | `GET /api/trends/key-size-timeline/` | key sizes over time |
| Shared keys | `GET /api/shared-keys/stats/` | aggregate shared-key metrics |
| Shared keys | `GET /api/shared-keys/distribution/` | certificate-count distribution |
| Shared keys | `GET /api/shared-keys/by-issuer/` | issuer exposure |
| Shared keys | `GET /api/shared-keys/timeline/` | intended timeline; current query targets the wrong database/field path |
| Shared keys | `GET /api/shared-keys/heatmap/` | issuer/key-type matrix |
| Shared keys | `GET /api/shared-keys/list/` | paginated/sorted groups |
| Shared keys | `GET /api/shared-keys/detail/<public_key_hash>/` | one group and certificates |

## Certificate filters

The shared certificate endpoint supports combinations of pagination, status, country, issuer, text search, encryption/key/signature/hash properties, vulnerability presence, validity/issuance windows, SAN characteristics, shared-key membership, risk signal, and global date/country/issuer/status/validation lists. The typed frontend client exposes these values and serializes arrays as comma-separated query values.

## Frontend/API traceability

Every active dashboard analytics page has a concrete endpoint mapping. The one known client-only mismatch is `getNotifications()`, which targets `/notifications/` while the backend route and UI notification trigger are commented. Shared-key list/detail pages bypass `apiClient` for two calls and hard-code localhost.

## API risks and limitations

- Mutating global scope through a query or switch request is unsafe under concurrent users.
- Errors often expose `str(exception)` directly in JSON.
- Export/list endpoints have no access-control or rate-limiting layer.
- No API contract tests, schema validators, throttling, or versioning are present.
- Several endpoints combine live and precomputed semantics, so freshness differs by metric.
- The export endpoint is structurally routed but not operational with the active `CertificateModel` implementation.
- The shared-key timeline endpoint is routed but its fast query does not match the verified main-certificate location/schema.
- Some live query paths accept search/filter input used in Mongo queries; their behavior must be documented, not represented as a hardened public API.
