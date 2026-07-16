# Evidence Traceability and Inference Register

## Classification rule

Every report-level technical claim must use one of two internal classifications:

- **Verified from repository** — directly observable in project-authored source, configuration, committed data/resource files, committed papers, or a reproducible static check run against the repository. This classification verifies what is implemented or stored; it does not prove production reliability, scientific validity, or measured performance.
- **Inference** — an interpretation, objective, requirement, consequence, intended benefit, probable runtime outcome, architecture label, generalization, future-work priority, or content/design decision derived from repository evidence but not explicitly established as a fact by it.

During report drafting, a Verified statement must cite its evidence file/function in the working notes. An Inference must be worded as derived, intended, possible, or proposed and requires the user's approval before inclusion. Repository README statements are not accepted alone when they conflict with code.

## Chapter 1 approval record

The user approved the documentation plan and authorized generation through Chapter 1. Accordingly, I-001, I-002, I-003, I-024, and the Chapter-1 organizational use of I-028 may be used in Chapter 1 with their existing qualifications. They remain classified as **Inference**; approval does not convert them into repository facts. Inference-dependent material for later chapters must be reviewed again at the relevant chapter gate.

## Chapter 2 approval record

On 14 July 2026, the user explicitly requested generation of the next chapter
after approving Chapter 1 and the documentation plan. This authorizes Chapter
2's qualified use of I-008, I-021, and I-028. They remain **Inference** and are
worded respectively as design intent, a citation-bounded interpretation, and a
repository-grounded synthesis rather than measured project outcomes.

## Major findings verified from repository

| ID | Major finding | Status | Primary evidence |
|---|---|---|---|
| V-001 | The repository implements domain crawling, experimental IP crawling, CT renewal/discovery, scoped analytics, a Django API, and a Next.js dashboard. | Verified from repository | top-level folders; active source files |
| V-002 | Root configuration selects `hugging-face-792k` and `hugging-face-792k-results` plus `global-dataset.csv`. | Verified from repository | `project-config.json`; `certificates/db.py` |
| V-003 | The UI scope model uses one physical database pair and global plus 196 configured country scopes. | Verified from repository | `certificates/db.py`; `certificates/Scopes.json` |
| V-004 | Domain workers atomically claim queue entries, retrieve port-443 certificates, call zcertificate, enrich documents, and update status. | Verified from repository | `crawler.py`; `crawler-args.py` worker and helper functions |
| V-005 | Domain crawler TLS contexts disable hostname/trust verification and use domain SNI. | Verified from repository | `get_pem_from_domain` in crawler variants |
| V-006 | Queue statuses, stale-task reset, rescue workers, retry flags, and monitoring/ETA logic exist. | Verified from repository | crawler worker/doctor/dashboard functions |
| V-007 | Leaf classification is `not self-subject and not basic_constraints.ca` in crawler and backfill code. | Verified from repository | `_compute_is_leaf`; `backfill-is_leaf.py` |
| V-008 | The IP scanners use APNIC-derived Pakistan CIDRs and write to separate databases/schemas not consumed by dashboard code. | Verified from repository | IP crawler scripts; backend DB references |
| V-009 | CT ingestion consumes `ws://localhost:8080/domains-only`, normalizes SANs, batches 5,000 sets, and writes `found=false` documents plus metadata. | Verified from repository | `config.yml`; `go-server.py` |
| V-010 | `main.py` implements eight ordered orchestration steps from CT shutdown through precompute and restart. | Verified from repository | step functions and `main()` in CT pipeline |
| V-011 | Renewal selection uses known-domain/base-www variants and marks matching CT SAN-set documents as found. | Verified from repository | `data-renew.py` |
| V-012 | Renewal merge uses checkpointed `ReplaceOne` operations keyed by domain. | Verified from repository | `data-renew-merge.py` |
| V-013 | New-domain extraction currently selects at most 1,500 CT documents, crawls them, bulk-inserts results, and updates the CSV. | Verified from repository | `new-data.py` |
| V-014 | Precompute orchestration creates indexes, discovers six analytics jobs, runs them, and verifies result collections/indexes. | Verified from repository | `run-generic.py`; `generic-create-indexes.py`; six jobs |
| V-015 | Materialized result families are CA, geography, SAN, shared keys, signature/hash, and validity; trend modules query the main collection live. | Verified from repository | precompute files; feature query modules |
| V-016 | The main certificate shape includes domain, scope, scan time, leaf flag, parsed X.509, and ZLint data. | Verified from repository | crawler inserts; backend field access; local shape check corroboration |
| V-017 | Result documents are keyed by scope and contain the field groups recorded in `database_analysis.md`. | Verified from repository | precompute document builders and result query code |
| V-018 | Backend feature packages use URL/view/controller/query-model layers with custom `JsonResponse`, not DRF. | Verified from repository | backend URLs, views, controllers, requirements |
| V-019 | Scope middleware mutates module-global scope and scoped collections inject live scope filters. | Verified from repository | `scope_middleware.py`; `db.py` |
| V-020 | Redis is optional, scope-aware, JSON-serialized, and configured with active 1,800-second TTL values. | Verified from repository | `cache_service.py` |
| V-021 | The active endpoint catalog and HTTP methods in `api_analysis.md` exist in URL/view code, including aliases and duplicate routes. | Verified from repository | all backend `urls.py` and view methods |
| V-022 | The frontend route/API map in `frontend_analysis.md` is implemented with App Router pages, API client/controller, contexts, SWR, Tailwind, and Recharts. | Verified from repository | `package.json`; frontend `src` |
| V-023 | Notification client code exists while its backend route and visible trigger are commented out. | Verified from repository | `apiClient.ts`; header/root URLs |
| V-024 | Shared-key list/detail pages hard-code localhost for two calls. | Verified from repository | shared-key page source |
| V-025 | The validity buckets, signature/hash formula, CA formula, shared-key thresholds, and vulnerability points recorded in the analytics artifacts match code. | Verified from repository | generic compute scripts; overview query model |
| V-026 | Geographic analytics map a domain's final TLD through a static country mapping. | Verified from repository | geographic precompute; `SharedModels.get_tld_country` |
| V-027 | Custom project authentication/authorization is not applied to dashboard APIs; settings remain development-oriented. | Verified from repository | settings; URLs/views; absence of decorators/permission checks |
| V-028 | The export view calls `CertificateModel.get_all`, whose implementation is commented; the duplicate shared switch has a GET/POST dispatch mismatch; shared-key timeline uses the wrong verified location/path. | Verified from repository | `views.py`; `models.py`; shared API/scope and shared-key query code |
| V-029 | Config/code drift includes 700k legacy defaults, stale README limits, `.exe`/extensionless binary mismatch, and hard-coded URLs. | Verified from repository | configuration, README, crawler/CT/frontend code, local binary filenames |
| V-030 | No substantive automated backend/frontend/E2E tests, CI configuration, container deployment, production manifest, or benchmark output is committed. | Verified from repository | recursive repository inventory; placeholder `tests.py` |
| V-031 | Committed data counts at audit time are 707,084 global CSV rows, 8,185 Pakistan-domain rows, and 720 Pakistan APNIC/CIDR lines excluding relevant headers as documented. | Verified from repository | committed CSV/text files and line-count check |
| V-032 | `results.txt` contains SNI/no-SNI IP experiment counts but lacks a formal experiment protocol and timestamps. | Verified from repository | IP crawler `results.txt` |
| V-033 | The current recording is 1920x1080 and shows overview, validity, detail, and trends; the older recording is 854x480 and visually obsolete. | Verified from repository | committed videos; ffprobe/contact-sheet review |
| V-034 | Three committed papers support discussion of key reuse, domain ownership, and stale certificates. | Verified from repository | `research-papers/*.pdf` |
| V-036 | All 105 first-party Python files outside `archive` and `node_modules` parsed; TypeScript type-check passed; ESLint reported 22 errors and 45 warnings in 19 files. | Verified from repository | reproducible commands refreshed for Chapter 8 and recorded in `verification_matrix.md` |
| V-037 | Existing source diagrams include stale or code-inconsistent statements identified in `resource_analysis.md`. | Verified from repository | diagram text/flows compared with current source |

## Inferences requiring approval

| ID | Inferred conclusion or proposed treatment | Status | Repository basis | Approval consequence |
|---|---|---|---|---|
| I-001 | The formal problem is maintaining and analysing a large, evolving SSL/TLS certificate corpus across acquisition, freshness, and risk dimensions. | Inference | V-001, V-009–V-015, README | Required for Ch. 1 problem statement |
| I-002 | The project's objectives are to collect, refresh, analyse, and visualize certificate data. | Inference | implemented subsystems, UI, README | Required for Ch. 1 objectives |
| I-003 | The integrated platform and its pipelines/analytics constitute the project's principal contributions. | Inference | V-001 and module integration | Required for Ch. 1 contributions |
| I-004 | Intended stakeholders/use cases include researchers or operators exploring certificate ecosystem/security data. | Inference | analytics/UI behavior; no stakeholder study | Required for Ch. 3.1 |
| I-005 | Functional requirements can be reconstructed from implemented routes, pages, pipelines, and scripts. | Inference | V-001–V-025 | Required for Ch. 3.2; must be labelled “derived requirements” |
| I-006 | Quality attributes such as scalability, recoverability, freshness, and usability were design goals. | Inference | indexes, batching, checkpoints, cache, UI | Required for Ch. 3.3; describe evidence, not elicited requirements |
| I-007 | “Local data-intensive analytics system” is the best architectural-style characterization. | Inference | V-001–V-022 | Approval for architecture narrative label |
| I-008 | The CT pipeline keeps the corpus fresher. Code shows intended refresh behavior, but no freshness measurement proves its effectiveness. | Inference | V-009–V-013 | Use “designed to refresh,” not a measured outcome |
| I-009 | Indexes, batches, cache, materialization, and pagination improve performance/scalability. They are mechanisms; benefit magnitude is unmeasured. | Inference | V-014, V-020, index code | Approval for Ch. 8.5 bounded discussion |
| I-010 | Process-global scope can cause cross-request interference under concurrent users. | Inference | V-019 | Approval for security/architecture risk statement |
| I-011 | Renewal checkpoint reuse after staging database recreation may skip documents. | Inference | checkpoint and cleanup code | Approval for correctness-risk discussion |
| I-012 | Broad process matching may affect unintended processes. | Inference | process-name/cmdline matching code | Approval for operational-risk discussion |
| I-013 | TLS verification is disabled so the crawler can collect invalid/expired/self-signed endpoints. Behavior is verified; rationale is inferred. | Inference | V-005 plus crawler purpose | Approval for rationale wording |
| I-014 | The export endpoint is nonfunctional at runtime. The call/missing method is verified, but Django execution was not performed. | Inference | V-028; no Django runtime check | Report as “statically inconsistent,” unless runtime-tested |
| I-015 | The duplicate shared scope-switch endpoint is nonfunctional at runtime. | Inference | V-028 | Same bounded wording/runtime-test option |
| I-016 | The shared-key timeline endpoint returns no valid timeline with the configured schema. | Inference | V-028 | Same bounded wording/runtime-test option |
| I-017 | The committed IP experiment counts represent comparative SNI behavior. Counts are verified; generalization or causal interpretation is not. | Inference | V-032 | User approval required before results discussion |
| I-018 | The actual lineage of the final Pakistan-domain CSV follows all dataset-preparation scripts/diagram sources. Scripts exist, but raw sources/run manifest are absent. | Inference | V-031; dataset scripts | Dataset provenance diagram/claims need approval or narrower wording |
| I-019 | The “Issuer Countries” UI label is misleading because implementation groups domain TLDs. | Inference | V-026 and frontend label | Approval for critique; implementation fact remains verified |
| I-020 | CA, signature, and vulnerability scores are not scientifically validated and contain methodological weaknesses. Formula facts are verified; evaluation is interpretive. | Inference | V-025; absent validation study | Approval for limitations/threats-to-validity wording |
| I-021 | A shared public key does not by itself prove private-key compromise or unsafe cross-owner reuse. | Inference | V-025 plus local shared-key paper | Include only with verified citation |
| I-022 | Security consequences/mitigations arising from DEBUG, missing API auth, exports, mutable scope, and local services. | Inference | V-019, V-027 | Approval for risk/mitigation table; facts can be stated directly |
| I-023 | Recommended future work and its priority order. | Inference | verified gaps V-027–V-030 | Required for Ch. 9.2 |
| I-024 | The 44-page allocation and placement of figures/tables will meet university expectations. | Inference | template review and content estimate | Planning approval only |
| I-025 | Newly composed architecture/context diagrams accurately synthesize relationships spread across multiple files. | Inference | relevant V IDs for each diagram | Diagrams require code-to-arrow review before inclusion |
| I-026 | The 1080p recording should be treated as the current UI version. | Inference | source-code visual comparison; no version tag | Approval for screenshot use |
| I-027 | The existing `automation-lucid.png` is sufficiently current to reuse unchanged. | Inference | visual/code comparison | Approval required; safer default is redraw from code |
| I-028 | The repository-grounded research gap and final conclusion drawn from implementation and three papers. | Inference | V-001, V-034 | Required for Ch. 2.6 and Ch. 9.1 |

## Out-of-band non-technical evidence

The required binary classification applies to technical/report findings. The following are not technical findings and therefore are recorded separately rather than mislabeled as repository evidence:

- project title, university, department, programme, session, and placeholders are user-supplied administrative metadata in `report_metadata.md`;
- page layout, front-matter order, font, numbering, and IEEE guidance come from the two user-supplied external template files in `template_analysis.md`;
- page allocations are an editorial inference I-024, not a repository fact.

## Default drafting policy pending approval

- Verified findings may be drafted after plan approval, with exact file/function traceability.
- Inferences I-001 through I-028 are not treated as facts. They will either be approved, narrowed, converted into explicitly labelled discussion, or removed.
- Local MongoDB document counts observed during analysis are excluded from the report by default because they are environment state, not committed repository evidence.
- No diagram with an Inference classification will be generated for the report until its scope is approved.

## Chapter 3 approval record

On 14 July 2026, after approving the documentation plan, the user explicitly
requested generation of Chapter 3. This authorizes the bounded use of I-004,
I-005, I-006, and I-025 in that chapter. Stakeholders, requirements, and quality
attributes remain labelled as derived; the context figure contains only arrows
verified against V-004--V-005, V-009, V-016--V-020, and V-022. It does not claim
a production deployment, measured quality achievement, or implemented user
authorization roles.

## Chapter 4 approval record

On 14 July 2026, the user explicitly requested generation of Chapter 4 after
approving the documentation plan. This authorizes the bounded architectural
interpretation I-007 and diagram synthesis I-025, together with qualified use
of I-009, I-010, and I-022. The chapter distinguishes configured localhost
topology from production deployment, mechanisms from measured performance,
and verified global-scope state from its inferred concurrency consequence.
Every architecture, topology, schema, and request-sequence arrow is mapped to
V-002--V-005, V-009--V-022, or an exact configuration endpoint.

## Chapter 5 approval record

On 15 July 2026, the user explicitly requested generation of the next chapter.
This authorizes Chapter 5's bounded use of I-013 and I-018. Disabled TLS
verification is presented as an observation setting and not as secure-client
validation. Dataset preparation is limited to committed scripts, file
contracts, and verified row counts; the chapter explicitly states that the
final Pakistan-domain CSV lacks a complete committed run manifest. The
unverified provenance diagram and interpretation of the SNI/no-SNI result
counts were excluded. Figures contain only control/data edges verified by
V-004--V-008.

## Chapter 6 approval record

On 15 July 2026, the user explicitly requested continued chapter generation.
This authorizes Chapter 6's bounded use of I-008, I-011, and I-012. The chapter
describes the pipeline as designed to refresh the corpus, makes no measured
freshness or recovery-effectiveness claim, and presents checkpoint/process
boundaries only as conditional static-analysis risks. The existing
`automation-lucid.png` was excluded under I-027; both Chapter 6 diagrams were
redrawn from the active paths documented by V-009--V-014. A fresh source review
also corrected an earlier analysis note: `go-server.py` removes leading `*.`
markers but does not lowercase SAN values.

## Chapter 7 approval record

On 15 July 2026, the user explicitly requested generation of the next chapter.
Chapter 7 limits its algorithm, route, data-contract, and interface statements to
V-014--V-015, V-018--V-026, and V-028. The CA, signature, and vulnerability
formulae are described as application-defined implementation behavior; the
chapter does not assert the scientific-validity conclusions in I-019--I-020.
Shared-key analysis is described only as grouping distinct certificate
fingerprints by repeated public-key fingerprint, without treating repetition as
proof of private-key compromise or cross-owner misuse under I-021. The
shared-key timeline, root export, and duplicated shared-scope route are reported
as static source inconsistencies, not as runtime-tested failures under
I-014--I-016. Recording-derived screenshots were excluded because I-026 remains
unapproved. Four new diagrams were instead redrawn from the verified analytics,
shared-key, vulnerability, and frontend paths.

## Chapter 8 approval record

On 15 July 2026, the user explicitly requested generation of Chapter 8. This
authorizes bounded use of I-009--I-012, I-014--I-022, and I-028 for analytical
discussion. Repository facts and inferred consequences remain separated in the
security and limitation tables. The committed IP counts are transcribed under
I-017 only as an unreproduced repository record; the chapter makes no causal,
population, or general SNI claim. Performance mechanisms are described without
accepting source-code timing comments as benchmark evidence. Static route and
schema inconsistencies remain explicitly distinct from observed runtime
failures because Django could not be imported in the available Python 3
environment. The refreshed checks produced V-036: 105/105 first-party Python
files parsed, TypeScript passed, and ESLint reported 22 errors plus 45 warnings
in 19 files. No new figure or unversioned screenshot was used.

## Chapter 9 approval record

On 15 July 2026, the user explicitly requested generation of the final Chapter
9. This authorizes bounded use of I-023 and I-028. The conclusion synthesizes
previously verified or approved findings and introduces no new implementation,
runtime, performance, or scientific claim. Future-work items are explicitly
proposed rather than implemented and are prioritized from V-023--V-030 and the
limitations established in Chapter 8. Chapter 9 adds no figure or screenshot.
Appendices remain ungenerated.
