# Repository Verification Matrix

| Planned area | Classification | Repository evidence | Decision/constraint |
|---|---|---|---|
| Introduction/problem/objectives/contributions | Inference — approved and bounded for Chapter 1 | I-001–I-003; V-001 | Repository has no formal statements; retain reconstructed, implementation-grounded wording |
| TLS/X.509/CT background | Verified from repository | V-034 local papers; V-005, V-009 implementation | Authoritative facts require exact citations |
| Requirements | Inference — approved and bounded | I-004–I-006; routes/UI/crawlers/pipeline | Included in Chapter 3 only as derived stakeholders, requirements, and quality attributes |
| Architecture components/data flow | Verified from repository | V-001, V-004, V-009–V-022 | Use concrete components and calls |
| Architecture label/topology | Inference — approved and bounded | I-007, I-025 | Included in Chapter 4 as repository-grounded abstractions; no production deployment claim |
| Domain crawler | Verified from repository | V-004–V-007 | Existing inaccurate images excluded |
| Dataset construction provenance | Inference — approved and bounded | I-018; scripts, processed files, V-031 | Chapter 5 states that actual final CSV lineage is unproven and does not include a provenance diagram |
| IP crawler implementation | Verified from repository | V-008 | Separate experimental database/schema emphasized |
| IP experiment interpretation | Inference — approved and bounded for Chapter 8 | I-017; V-032 | Exact committed counts transcribed; no causal, population, or general SNI claim |
| CT ingestion/orchestration | Verified from repository | V-009–V-014 | Implemented control flow only |
| CT freshness/recovery effectiveness | Inference — approved and bounded | I-008, I-011, I-012 | Chapter 6 describes intended refresh behavior and conditional static risks; no measured freshness or recovery-effectiveness claim |
| Precomputed/live analytics | Verified from repository | V-014, V-015, V-025, V-026 | Formulas/buckets/query source exactly as code |
| Analytics scientific interpretation | Inference — excluded from Chapter 7 | I-019–I-021 | Chapter 7 reports exact implementation behavior only; interpretation remains deferred |
| Backend/API | Verified from repository | V-018–V-021, V-027–V-029 | Mark statically inconsistent routes |
| Endpoint runtime failure conclusions | Inference — not asserted through Chapter 8 | I-014–I-016; V-028 | Chapters 7–8 identify static source inconsistencies only; Django runtime could not be exercised |
| Frontend/dashboard | Verified from repository | V-022–V-024 | Route/client/component claims supported |
| Screenshot currentness | Inference — excluded from Chapter 7 | I-026; V-033 | Unversioned recording stills were not included; fresh runtime images remain an option |
| Authentication/authorization absence | Verified from repository | V-027 | Do not claim auth as a feature |
| Security consequences/mitigations | Inference — approved and bounded for Chapter 8 | I-010, I-022 | Direct facts are separated from conditional impact and control boundaries |
| Performance mechanisms | Verified from repository | index/cache/batch/materialization code | Describe mechanisms only |
| Performance/scalability benefit | Inference — approved only as mechanism discussion | I-009 | Chapter 8 excludes benchmarks, source-comment timings, and improvement magnitudes |
| Static verification/testing state | Verified from repository | V-030, V-036 | State scope; no fabricated test campaign |
| User evaluation | Verified from repository | V-030 absence | Exclude |
| Hardware requirements | Verified from repository | V-030 absence | Exclude |
| Future work | Inference — approved and bounded for Chapter 9 | I-023; V-023–V-030; Chapter 8 limitations | Present as proposals only; do not describe any item as implemented |

## Executed verification checks

| Check | Result | Interpretation |
|---|---|---|
| Recursive first-party Python AST parse | 105/105 parsed outside `archive` and `node_modules` | syntax-level validity only |
| TypeScript compiler (`--noEmit`) | passed | current TS type check passed |
| ESLint | 67 findings in 19 files: 22 errors, 45 warnings | quality gate currently fails |
| Django runtime check | not run | active Python interpreter lacked Django/PyMongo |
| Mongo ping through `mongosh` | passed | local Mongo was reachable during analysis |
| Active DB collection presence | expected main and six result families present | environment supports code/config mapping |
| Result document shape | expected scope and analytics field groups observed | confirms precompute/API contracts locally |
| Frontend page/API call trace | active pages mapped; notification mismatch found | route traceability established |
| Export model trace | `CertificateExportView` calls missing active `CertificateModel.get_all` | routed export is not verified operational |

## Removed or constrained claims

- No claim that the system has authentication, authorization, rate limiting, production deployment, containerization, CI/CD, automated backend tests, user studies, benchmarked scalability, or validated scientific scoring.
- No claim that IP-crawled certificates feed the dashboard.
- No numerical output from standalone report scripts without committed output.
- No claim of fingerprint deduplication in the configurable crawler.
- No reuse of stale/inaccurate figures as implementation truth.
