# Folder Analysis

## Evidence classification

Folder contents and call/configuration relationships are **Verified from repository**. Importance ratings and proposed report placement are editorial **Inference** governed by the approved outline.

| Folder | Purpose and relationship | Importance | Report use |
|---|---|---:|---|
| `binaries` | Holds `zcertificate` and CertStream Go executables expected by subprocess-based acquisition code. The current local files use `.exe`; several scripts expect extensionless paths. | Critical runtime dependency; provenance/build source absent | Acquisition and deployment constraints |
| `ct-logs-renewal-pipeline` | Maintains the domain corpus using a local CertStream-compatible server, WebSocket ingestion, Mongo staging databases, renewal recrawling, new-domain discovery, idempotent replacement, and precompute triggering. | Core | Dedicated CT pipeline chapter |
| `dashboard/backend` | Exposes Django JSON endpoints, performs live MongoDB queries, serves precomputed analytics, applies logical scope filtering, and optionally caches responses in Redis. | Core | Architecture, API, database, analytics, security |
| `dashboard/backend/certificates` | Main Django application. Feature packages consistently separate views, controllers, and query/model classes, though some older monolithic code remains commented or partially active. | Core | Backend implementation |
| `dashboard/backend/pre-compute-scripts` | Creates indexes and materializes six result families per configured scope. `run-generic.py` discovers and verifies these jobs. | Core | Analytics pipeline and performance design |
| `dashboard/backend/country-domain-extractors` | Older, hard-coded MongoDB/Tranco extraction utilities not called by active orchestration. | Legacy/utility | Mention only in repository/legacy inventory |
| `dashboard/frontend` | Next.js 16, React 19, TypeScript, Tailwind, SWR, and Recharts dashboard. App Router pages consume the Django APIs. | Core | Frontend architecture and dashboard |
| `figures-and-poster` | Contains PNG diagrams, Mermaid/Excalidraw sources, icon, and poster. Some images are accurate, some stale or misleading. | Supporting | Resource selection and figure provenance |
| `recordings` | Includes a current 1920x1080 dashboard demonstration and an older 854x480 interface recording. | Supporting | Current recording supplies four report screenshots; older recording excluded |
| `reports` | Standalone Mongo shell, Python, HTML, and ReportLab investigations for validity, SANs, ZLint, shared keys, expiry, hashes, and signatures. They are not connected to dashboard routes and committed output files are absent. | Exploratory | Algorithms/history; no unverified numerical results |
| `research-papers` | Three related-work PDFs about RSA certificate/key reuse, domain ownership in shared-key sets, and stale TLS certificates. | Supporting | Literature review and motivation |
| `ssl-certificates-crawler/domain-based-crawler` | Threaded TLS acquisition, queue/status collection, zcertificate parsing, scope enrichment, leaf classification, retry/doctor logic, and dataset-preparation scripts. | Core | Certificate acquisition chapter |
| `ssl-certificates-crawler/ip-based-crawler` | APNIC-to-CIDR preparation and static/interactive IPv4 scanning experiments. Results use a separate database/schema and are not integrated into the dashboard. | Experimental | Scoped subsection and repository experiment |
| `useful-scripts` | CSV cleanup, CT endpoint checking, document cleanup/scope enrichment, and small test-database preparation. | Utility | Maintenance appendix/limitations |
| `.vscode` | Editor-level configuration only. | Low | Exclude from main report |
| `.git` | Version-control history and objects. | Operational metadata | Exclude from report content |
| `archive` | Explicitly excluded from every stage by user instruction. | Not analysed | None |

## Dead, legacy, and incomplete elements

- `crawler-legacy.py` predates scope and `is_leaf` enrichment.
- `data/mockData.ts` is not imported by active frontend pages.
- `HelloDisplay.tsx` is unused; `NotDevelopedModal.tsx` remains active for unavailable UI actions.
- The API client's notification method targets a route that is commented out; the notification icon/callback is also commented.
- Root backend controller/model files contain substantial commented implementations superseded by feature packages.
- Django `models.py` does not define active ORM entities; certificate data is accessed directly through PyMongo.
- `tests.py` is a placeholder and there is no substantive automated backend test suite.
- `next.config.ts` declares `nextConfig` but exports a different inline object, producing a lint warning.
- Standalone report scripts are exploratory and are not part of the application request path.
