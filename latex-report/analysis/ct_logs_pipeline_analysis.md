# CT Logs Renewal Pipeline Analysis

## Evidence classification

Script order, configured endpoints, batch sizes, database operations, and checkpoints are **Verified from repository** (V-009–V-014). Claims that the pipeline achieves fresher data or that identified checkpoint/process patterns cause runtime failures are **Inference — approval required** (I-008, I-011, I-012).

## Objective

The CT pipeline keeps the domain-based certificate corpus fresher by identifying domains already known to the project whose CT entries may have changed and by discovering previously unseen domains. It combines a continuously checkpointed CT collector with a periodically invoked eight-step batch orchestrator.

## Continuous CT ingestion

### CertStream-compatible Go server

`config.yml` configures a local domain-only WebSocket endpoint, Google/Chrome CT log metadata, buffering, Prometheus metrics, and recovery through `ct_index.json`. The checkpoint file contains per-log indices for the configured log set.

### `go-server.py`

- starts the native server if not already detected;
- connects to `ws://localhost:8080/domains-only`;
- removes leading `*.` wildcard markers and deduplicates each message's domain
  strings; the current implementation does not lowercase the names;
- deduplicates SAN sets in memory by sorted tuple;
- bulk-inserts batches of 5,000 documents into `go-server.certificates`;
- stores `{domains: [...], found: false}` under a unique multikey domain index;
- writes run status/metrics to a metadata collection every five seconds;
- flushes and terminates on signals.

Portability limitations are material: the script expects an extensionless Go binary and passes `preexec_fn=os.setsid`, which is POSIX-specific, while this repository is being analysed on Windows with an `.exe` binary.

## Periodic orchestration (`main.py`)

| Step | Action | Inputs | Outputs/state |
|---:|---|---|---|
| 1 | stop detected Go server | process list | CT server stopped |
| 2 | ensure global domain CSV | main certificates if CSV absent | `global-dataset.csv` |
| 3 | find renewal candidates | global CSV + CT staging | `data-renew.csv`, CT `found=true` |
| 4 | run new-data process and renewal crawler | renewal/new CSVs, crawler CLI | `new-data` and `data-renew` staging databases |
| 5 | merge renewal documents | `data-renew.certificates` | replacements/upserts in main certificates |
| 6 | remove renewal artifacts | renewal CSV/database | clean staging state |
| 7 | run generic precomputation | updated main database | refreshed results collections |
| 8 | restart CT collection | config/checkpoints | background Go/WebSocket ingestion |

No scheduler, lock service, CI job, cron entry, or Task Scheduler definition is committed. The code assumes external invocation and has no complete master-overlap guard.

## Renewal candidate selection (`data-renew.py`)

- Reads known domains in batches of 5,000.
- Builds base/`www` variations.
- Looks up CT documents whose `domains` array intersects the variations.
- Writes one representative domain for each matched CT SAN-set document.
- Marks that CT document `found=true` to avoid repeated selection.

The selection is document/SAN-set oriented, not necessarily one line for every matching domain. The `found` state persists until the CT staging database is dropped by the new-data path.

## Renewal crawl and merge

`crawler-args.py` crawls renewal candidates into `data-renew`. `data-renew-merge.py` then strips the staging `_id` and performs bulk `ReplaceOne({domain: ...}, replacement, upsert=True)` operations. It stores a last processed ObjectId checkpoint only after a successful batch, which makes an interrupted batch retryable.

A correctness concern remains: the orchestrator drops the renewal staging database but the checkpoint remains in the main database. A later staging database receives new ObjectIds; comparing them to an old checkpoint can skip new documents depending on ObjectId ordering/time.

## New-domain path (`new-data.py`)

- selects up to 1,500 `found=false` CT documents in the current code;
- writes the first cleaned domain from each SAN set to `new-data.csv`;
- drops the whole `go-server` database after extraction;
- invokes the configurable crawler into `new-data`;
- bulk-inserts staged certificates into the active main database;
- appends only successfully inserted domains to the global CSV;
- removes the CSV and temporary database.

README material that states a 10,000-domain extraction limit is stale. Comments also assume duplicate certificate fingerprints will be rejected, but the invoked crawler's fingerprint index is non-unique.

## Dataset export (`fetch-domains-names.py`)

The exporter streams domains from the configured main collection. It can analyse duplicate frequencies and optionally write a deduplicated copy. The orchestrator calls it without replacing the original with the deduplicated output, so duplicate rows can remain in the main CSV.

## Process-control risks

- Process detection uses broad name/cmdline matching and can identify unintended processes.
- PID-file protection applies to the new-data background process, not to the full orchestrator.
- Constants/comments use `GO_SERVER_DB_NAME = "new-data"` in one cleanup branch although the ingestion database is named `go-server`, creating naming ambiguity.
- Step 5 attempts a merge even when no renewal data was produced.
- No transactional boundary covers CSV change, database merge, precompute, and CT restart.
- Failure logging exists, but automated fault-injection or recovery tests do not.
