# Crawler Analysis

## Evidence classification

Crawler control flow, settings, schemas, indexes, and defaults are **Verified from repository** (V-004–V-008). The rationale for disabled TLS validation, recovery effectiveness, and ethical/security consequences are **Inference — approval required** (I-013, I-022).

## Domain crawler variants

| File | Status | Distinguishing behavior |
|---|---|---|
| `src/crawler.py` | primary fixed-configuration crawler | 30 workers by default; unique domain index; scope and leaf enrichment; monitoring/doctor threads |
| `src/crawler-args.py` | pipeline-oriented configurable crawler | CLI overrides for URI, databases, collections, CSV, binary, logs, threads, timeouts, retry; non-unique fingerprint index |
| `src/crawler-legacy.py` | legacy | no scope or `is_leaf`; retained but not current |

## Domain acquisition flow

1. Validate input CSV and parser executable.
2. Connect to MongoDB and establish indexes.
3. Load CSV domains into `domain_status` only when that queue is empty.
4. Worker threads atomically claim a `pending` item with `find_one_and_update` and set it to `processing`.
5. Open TCP/TLS to port 443 using the domain as SNI.
6. Disable hostname and trust validation intentionally and retrieve the DER peer certificate.
7. Convert DER to PEM and invoke `zcertificate -format pem`.
8. Remove the top-level raw field, add `domain`, extracted final-label `scope`, UTC `scanned_at`, and computed `is_leaf`.
9. Insert the certificate and mark the queue item completed; errors mark it failed and write logs.
10. A doctor thread resets stale processing work and can start rescue workers; a dashboard loop reports counts, throughput, and ETA.

The intentional `CERT_NONE` behavior is necessary for a measurement crawler that must collect expired, self-signed, hostname-mismatched, or otherwise invalid certificates. It must not be described as secure client validation.

## Leaf classification

A certificate is considered a leaf when it is neither self-subject (`subject_dn == issuer_dn` with a nonempty subject) nor explicitly a CA (`basic_constraints.ca == true`). The crawler and `backfill-is_leaf.py` use the same rule. This is a pragmatic classification, not full path validation.

## Queue and recovery

- Atomic status claims prevent two normal workers from taking the same pending domain.
- Statuses are `pending`, `processing`, `completed`, and `failed`.
- Worker heartbeat timestamps are updated at phase boundaries.
- Stale tasks older than 60 seconds can be reset.
- Retry behavior exists but defaults to disabled.
- `threading.active_count() - 2` is used as a worker estimate and can count unrelated threads.
- The named `HEARTBEAT_INTERVAL` is not used for periodic heartbeats during a blocking network/subprocess operation.

## Deduplication inconsistency

`crawler.py` creates a unique domain index and handles duplicate-domain insertion. `crawler-args.py`, which the CT pipeline invokes, creates a non-unique index on `parsed.fingerprint_sha256` and performs ordinary inserts without an explicit duplicate check. Comments in the renewal/new-data code imply certificate-fingerprint deduplication that the actual invoked crawler does not guarantee.

## Domain dataset preparation

The repository includes Pakistan-domain merge/filter utilities for supplied lists, Tranco, and Rapid7 certificate exports. Three Rapid7 extraction implementations trade zcertificate accuracy, `cryptography` speed, and a hybrid fallback. Raw upstream datasets are ignored and absent; only scripts and processed evidence such as `pk-domains.csv` are available. Source-size claims in README text cannot be independently reconstructed from committed raw files.

## IP crawler experiment

`apnic-global-to-pk-cidrs.py` filters APNIC delegated statistics for Pakistan IPv4 records and summarizes address ranges into CIDRs. The committed filtered files contain 720 lines; a 13-line mini CIDR file supports smaller runs.

### Static scanner

- Uses a fixed CSV and 20 workers by default.
- Connects by IP and passes the IP as `server_hostname`.
- Stores one parsed document per IP in a separate static database.
- Uses a schema different from the main domain corpus.

### Interactive scanner

- Prompts for CIDR or individual-IP mode and fake SNI (`example.com`) or no SNI.
- Uses 40 workers by default.
- Separates TCP refusal/timeout, TLS timeout, SSL error, and other error statistics.
- Recursively removes raw fields.
- Upserts by unique IP, nesting parsed certificate output under `certificate`.

The experiment is not integrated with the main dashboard database. The committed `results.txt` records counts for SNI/no-SNI experiments; it is evidence for an evaluation subsection but lacks a formal experimental protocol, timestamps, denominators stated in prose, and reproducibility metadata.

## Runtime portability issues

- Scripts commonly expect `../../../binaries/zcertificate` without `.exe`, while the local binary is `zcertificate.exe`.
- Fixed crawler defaults retain an older 700k database name and do not read root project configuration.
- There is no version/checksum or build source for native binaries.
- Network ethics, scan authorization, rate limits, and opt-out policy are not documented in the repository.
