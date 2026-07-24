# Backend Analysis

## Evidence classification

Classes, methods, settings, routes, field access, and formulas below are **Verified from repository**. Multi-user impact and the asserted runtime failure of statically inconsistent routes are **Inference — approval required** under I-010 and I-014–I-016 because the Django application was not runtime-tested in this audit.

## Structure and request handling

The backend is a Django 5 application named `certificates`. Root URLs mount `/api/` and the default Django admin. Feature packages use this flow:

```text
URL pattern -> Django View -> Controller -> Query/Model class -> MongoDB
                                  |                 |
                                  `-> Redis cache   `-> result collections or live certificates
```

Responses use Django `JsonResponse`; Django REST Framework is not active. `json_response` helpers recursively serialize `ObjectId`, dates, and related values. Many endpoints are class-based GET views. The root scope switch is a function-based POST endpoint.

## Core infrastructure

### `certificates/db.py`

- Loads the first database entry from root `project-config.json`.
- Creates one PyMongo singleton connection to localhost.
- Constructs 197 UI choices from `Scopes.json`: global plus 196 country/TLD scopes.
- Wraps the main `certificates` collection in `ScopedCollection`, which injects the current scope into `find`, `find_one`, `count_documents`, `estimated_document_count`, and `aggregate`.
- Locates scope-specific precomputed documents in the results database.
- Reassigns collection handles on a scope switch and clears Redis cache.

The current scope is module-global process state. Middleware changes it from each request's `scope` query parameter or `X-Certificate-Scope` header. It is not request-local, thread-local, or validated strictly against configured options. This is a correctness/concurrency limitation for multi-user deployment.

### `cache_service.py`

- Uses Redis when the module and local server are available; otherwise all methods degrade to no-ops.
- Serializes values as JSON.
- Hashes sorted parameters with MD5 to produce compact keys and always adds the current precomputed scope.
- Defines cache namespaces for metrics, certificate lists, CA, signature/hash, SAN, validity, trends, geography, filters, and future risk.
- Every active configured TTL is currently 1,800 seconds even though adjacent comments name differing minute values.
- Supports namespace invalidation and full prefix deletion.

### Settings

- Django SQLite `internal_db` is configured for framework internals.
- MongoDB is accessed directly and is not a Django ORM database.
- CORS permits `http://localhost:3000`.
- The settings are development-only: `DEBUG=True`, a committed insecure secret, empty `ALLOWED_HOSTS`, duplicate `CommonMiddleware`, and no production hardening.
- Django's authentication apps/middleware exist by default, but no dashboard endpoint enforces project-specific authentication or authorization.

## Feature modules

| Module | Controller/query responsibilities | Main data source |
|---|---|---|
| `shared_apis` | global health, validity trends, CA leaderboard, geography, paginated/filterable certificates, detail serialization, status/grade/risk enrichment | main certificates plus precomputed CA/geography/validity/shared-key data |
| `overview` | encryption distribution, unique filters, future risk, ranked vulnerability candidates | live main collection plus shared-key results |
| `ca_analytics` | CA totals, validation matrix, market ranking, multi-factor leaf-certificate score | `ca-analysis`, with live fallback methods |
| `validity_analysis` | average/min/max lifetime, 398-day compliance, buckets, issuance timeline, live near-expiry counts | `validity-analysis` plus live counts |
| `signature_hash` | signature/hash/key distributions, weak-hash counts, score, historical trends, issuer matrix | `signature-and-hash` |
| `san_analytics` | SAN totals/averages, size buckets, wildcard breakdown, TLD breakdown, referenced certificate hydration | `san-analysis` plus main certificate hydration |
| `shared_keys` | metadata, distributions, issuer analysis, heatmap, pagination, group detail | `shared-keys-detailed` |
| `trends` | expiration forecast, algorithm adoption, validation level and key-size timelines | live main collection aggregations |

## Business rules

### Certificate status and grade

`SharedModels` derives validity status from the parsed end date and creates an application grade from ZLint error/warning counts. It serializes issuer, subject, key, fingerprints, SANs, validity, ZLint issues, and optional risk/shared-key context for frontend consumption.

### Vulnerability score

The overview risk model is an application-defined score, not a standardized vulnerability metric:

- expired certificate: +30;
- shared public key: +30;
- RSA key below 2048 bits: +20;
- validity above 398 days: +10;
- ZLint error/warning penalty: up to +10;
- currently valid, strong-key, modern-validity, and clean-ZLint signals each subtract 5 when applicable.

The score is clamped to 0–100. Levels are Critical at 85+, High at 70+, Medium at 40+, otherwise Low. Candidate collection uses indexed signal-specific queries capped by a per-signal limit before scoring, so the ranking is a bounded risk view rather than an exhaustive full-collection sort.

### CA ranking score

The generic precompute job scores leaf certificates and averages by CA. The final score is the mean of five 0–1 components, multiplied by 100:

1. core hygiene: normalized non-critical ZLint penalty and curated critical lint hits;
2. crypto health: key hygiene, key reuse, and weak-key-length helper;
3. operational stability: fixed per-certificate mean of CADS, TSI, and IOPS in the optimized implementation;
4. policy compliance: EKU, policy OID, DV/OV/EV, and name-constraints functions;
5. risk factors: issuer geography, authority-access placeholder, and revocation endpoints.

The implementation's `compute_wklp` returns 1 for a key below 2048 bits and that value is averaged positively. `compute_khs` also applies a 2048-bit threshold to ECDSA length. These facts must be disclosed in any report discussion of score validity.

## Export behavior

- `/certificates/download/` streams CSV rows and is intended for large result sets.
- `/certificates/export/` intends to export up to 10,000 records, but calls `CertificateModel.get_all`, whose only definition in `models.py` is commented out. The active implementation is therefore broken unless restored or redirected to `SharedModels.get_all`.
- Neither endpoint is access controlled by project-specific authorization.

## Backend dead/inconsistent code

- `models.py` is a PyMongo wrapper, not a set of Django ORM models; much older code is commented.
- Root `controllers.py` contains only a few live helpers and is not the main modular API path.
- Its active search/recent-scan helpers also call the missing `CertificateModel.get_all`; they are not mounted by the current modular URL set.
- `hello_mongo_view` reports a hard-coded database label (`latest-pk-domains`) rather than the active configured database.
- The duplicate `/api/shared/databases/switch/` view implements only `get` but rejects non-POST requests inside it; POST dispatch has no `post` method. The frontend uses the working root `/api/databases/switch/` endpoint.
- `SharedKeyModel.get_shared_key_timeline_fast` queries a `certificates` collection in the results database and matches `public_key_hash_sha256`, while canonical certificates are in the main database and store the key fingerprint under `parsed.subject_key_info.fingerprint_sha256`. The timeline endpoint is consequently incomplete with the verified schema.
- The misspelled `/overview/vulnerablities/` route is retained as an alias.
- There is no substantive backend test suite.
