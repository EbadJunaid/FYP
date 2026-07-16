# Database Analysis

## Evidence classification

Database names, code-defined collections/fields, grouping thresholds, and indexes are **Verified from repository** (V-002, V-016, V-017, V-025). Merge-resume consequences are **Inference — approval required** (I-011). Local runtime document counts are excluded.

## Active database topology

| Store/database | Collections | Purpose |
|---|---|---|
| `hugging-face-792k` | `certificates`; queue/checkpoint collections when applicable | canonical certificate corpus and live query source |
| `hugging-face-792k-results` | six result families | materialized analytics keyed by logical scope |
| `go-server` | `certificates`, `metadata` | CT SAN sets, processed flag, and ingestion health |
| `data-renew` | `certificates`, `domain_status` | renewal crawler staging |
| `new-data` | `certificates`, `domain_status` | newly discovered domain staging |
| `ip-based-crawler-static` / `ip-based-crawler-interactive` | `pk-certificates` | separate experimental IP scan output |
| SQLite `internal_db` | Django internal tables | Django framework state only |
| Redis DB 0 | prefixed JSON keys | optional response cache |

Database names above are code/configuration contracts. The temporary databases exist only during relevant workflows.

## Main certificate document

The canonical document is generated from `zcertificate` JSON and enriched by the crawler.

| Field | Type/shape | Producer and use |
|---|---|---|
| `_id` | ObjectId | MongoDB identity and detail route |
| `domain` | string | input domain; list/search/filter/display |
| `scope` | string | extracted final TLD; live country scope filtering |
| `scanned_at` | UTC datetime | acquisition timestamp and dashboard display |
| `is_leaf` | boolean | crawler/backfill leaf rule; CA ranking input |
| `parsed` | object | X.509 structure from `zcertificate` |
| `parsed.validity` | object | start/end/length for status and validity analytics |
| `parsed.issuer`, `parsed.subject` | objects | CA, organization, country, and identity analytics |
| `parsed.subject_key_info` | object | algorithm, size, key fingerprint, shared-key analysis |
| `parsed.signature_algorithm`, `parsed.signature` | objects | hash/signature and self-signed analytics |
| `parsed.extensions` | object | SAN, policies, EKU, AIA, constraints, CRL data |
| `parsed.fingerprint_sha256` | string | certificate identity/deduplication intent |
| `zlint` | object | lint version, flags, and per-lint results |

The leaf rule is `not self-subject and not basic_constraints.ca`. A one-time backfill applies the same rule to existing documents.

## Results collections

| Collection | Document granularity | Important fields |
|---|---|---|
| `ca-analysis` | one document per configured scope | totals, self-signed count, unique countries, CA list, validation levels, score components/ranks, formula metadata |
| `geographic-distribution` | one per scope | countries array, counts, percentages, source metadata |
| `san-analysis` | one per scope | total/average SAN count, standard/multi/wildcard counts, bucket groups, TLDs, bounded certificate-ID references |
| `signature-and-hash` | one per scope | algorithm/hash/key-size distributions, weak hash count, compliance, strength score, self-signed count, trends, issuer matrix |
| `validity-analysis` | one per scope | mean/min/max days, <=398-day compliance, lifetime buckets and IDs, issuance timeline |
| `shared-keys-detailed` | group documents plus one metadata document per scope | key fingerprint, certificate/domain/SAN counts, key properties, issuers, risk, certificate details; aggregate totals in metadata |

At analysis time, a reachable local MongoDB instance was used only to corroborate collection and field shapes. Its document counts are deliberately excluded from the report because they are environment state, not committed repository evidence. Collection/field claims in the report must instead trace to crawler, precompute, and query code.

## Shared-key grouping

The precompute pipeline groups by public-key SHA-256 fingerprint and requires more than one distinct certificate fingerprint. Group risk is:

- HIGH if at least 5 certificates or 20 SANs;
- MEDIUM if at least 3 certificates or 10 SANs;
- LOW otherwise.

The risk label describes exposure size, not proof that the private key is compromised. Group documents include detailed certificate references, domains, SANs, issuers, key algorithm/size/type, and generated explanatory factors.

## CT and queue schemas

- CT document: `{domains: [normalized names], found: boolean}` with a unique multikey index on `domains`.
- CT metadata: a `run_status` document periodically updated with counters/timestamps.
- Domain queue: domain plus `pending`, `processing`, `completed`, or `failed` status, worker/heartbeat timestamps, and error context.
- Renewal merge checkpoint: last processed staging ObjectId per source/target pair.

## Indexing

The generic index script verifies indexes on validity timestamps/length, key algorithm and size, signature/hash, ZLint flags, self-signed flag, scope, validation level, certificate and key fingerprints, domain, issuer country/organization, SAN names, and `is_leaf`. Compound scope indexes support scoped queries. Result indexes support scope lookup and feature-specific sorting/filtering, including shared-key risk and certificate count.

## Schema limitations

- MongoDB is schemaless and no JSON Schema validator or migration system is committed.
- Domain, renewal, and IP crawlers do not emit one fully uniform schema; interactive IP output nests the certificate.
- Raw scope values include more TLDs than the curated UI options.
- The root project configuration and the older `databases.json` disagree.
- `crawler.py` creates a unique domain index, whereas `crawler-args.py` creates a non-unique certificate-fingerprint index and does not implement the deduplication guarantee described by comments.
- Dropping/recreating staging databases while retaining ObjectId checkpoints creates a possible merge-resume correctness issue.
