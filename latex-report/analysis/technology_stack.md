# Technology Stack

## Evidence classification

Dependencies, versions, imports, scripts, configured services, and check results are **Verified from repository**. Any claim that a technology improves performance, scalability, security, or usability is **Inference — approval required** unless a committed benchmark establishes it.

## Verified stack

| Layer | Technology | Repository evidence | Role |
|---|---|---|---|
| Frontend | Next.js 16.1.1, React 19.2.3, TypeScript 5 | `dashboard/frontend/package.json`, `src/app` | App Router UI and server-independent client pages |
| Styling | Tailwind CSS 4 | package/config/CSS files | Responsive themed interface |
| Data fetching | SWR 2.3.8, Fetch API | page files, `apiClient.ts` | Client caching/revalidation and HTTP calls |
| Visualization | Recharts 3.6.0 | package and chart components | Bar, line, pie, and matrix-style analytics |
| Backend | Django 5.x, django-cors-headers | `requirements.txt`, settings, URL/view files | JSON API, routing, middleware, admin scaffold |
| API serialization | Django `JsonResponse` and custom serializers | view/query files | No Django REST Framework dependency is active |
| Primary data store | MongoDB with PyMongo 4.6+ | `db.py`, crawlers, pipeline, precompute scripts | Certificates, queues, CT staging, analytics documents |
| Django internal store | SQLite | `ssl_dashboard/settings.py` | Django framework tables only; not certificate analytics |
| Optional cache | Redis | `cache_service.py` | JSON response caching with scope-aware keys and nominal 1,800-second TTLs |
| TLS acquisition | Python `ssl`/`socket`, threads | domain/IP crawler source | Connect to port 443 and retrieve peer certificates |
| Certificate parser | `zcertificate` external binary | crawler subprocess calls | Parse X.509 and produce parsed/ZLint JSON |
| CT ingestion | CertStream server Go binary, Python WebSocket client | CT config and `go-server.py` | Stream domains-only CT events to MongoDB |
| Orchestration | Python subprocesses, PID/process inspection | `ct-logs-renewal-pipeline/main.py` | Eight-stage renewal/discovery workflow |
| Data processing | Python CSV/JSON, pandas, NumPy, cryptography | utility, dataset, analytics scripts | Dataset preparation and selected analysis tasks |
| Reports | Mongo shell JavaScript, HTML/JavaScript, ReportLab | `reports` | Standalone exploratory outputs |
| Process/network utilities | psutil, httpx, websocket-client | CT utilities and pipeline | Process discovery, CT endpoint tests, WebSocket ingestion |

## Build and run model

- Frontend scripts are `next dev`, `next build`, `next start`, and `eslint`.
- Backend uses Django's `manage.py`; no container, Compose, CI, or deployment manifest is committed.
- MongoDB, Redis, the CertStream server, and crawler binaries are expected on localhost or the local filesystem.
- The pipeline assumes an external scheduler invokes `main.py`; no scheduler definition is present.
- Precomputation is started by `run-generic.py`, which first creates indexes, runs discovered generic jobs, and verifies expected collections/indexes.

## Dependency completeness

`dashboard/backend/requirements.txt` covers Django, CORS, PyMongo, dateutil, and Redis. Repository-wide scripts additionally import NumPy, pandas, cryptography, websocket-client, psutil, httpx, and ReportLab. These are not consolidated into one reproducible project-level dependency file. The executable binaries also lack version/build provenance in the repository.

## Verification on the analysis machine

- All 105 first-party Python files outside `archive` and `node_modules` parsed successfully with the available Python 3 AST parser during the Chapter 8 refresh.
- `npx tsc --noEmit --incremental false` completed successfully.
- `npm run lint` completed with 67 findings in 19 files: 22 errors and 45 warnings, chiefly React 19 effect-state rules, explicit `any`, hook dependency issues, and unused values.
- The available Anaconda Python environment did not have Django or PyMongo installed, so a Django runtime check was not possible from that interpreter.
- MongoDB itself was reachable through `mongosh`; the configured main/results databases and expected result collections were present. This is environment verification, not a committed repository dataset.
