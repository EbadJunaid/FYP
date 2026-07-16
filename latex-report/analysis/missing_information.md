# Missing Information and Approval Inputs

## Required for front matter

The students and roll numbers, supervisor, co-supervisor, committee members,
Head of Department, programme/session, declaration-date format, and university
logo have been supplied and are recorded in `report_metadata.md`. The remaining
unprovided items are:

- actual submission date;
- faculty/campus wording if an additional form of it is required by the university;
- final abstract text.

These remaining values will not be inferred.

## Not found in the repository

- formal software requirements specification, stakeholder interviews, or use-case approval;
- production deployment topology, hosting provider, domain, TLS configuration, containers, or CI/CD;
- hardware requirements or measured resource consumption;
- documented scheduler for the CT orchestrator;
- automated backend/frontend/end-to-end test suites beyond a placeholder;
- reproducible performance benchmarks for crawler, Mongo queries, precompute jobs, APIs, or UI;
- user evaluation/usability study;
- research ethics, scan authorization, rate-limit, opt-out, and data-retention policy;
- binary source/version/checksum/license for `zcertificate` and CertStream server executables;
- project licence;
- complete Python dependency lock/environment definition;
- committed MongoDB dump or frozen analytics export;
- current screenshots for every dashboard page;
- formal team-member contribution/challenge records.

## Verified implementation defects requiring report treatment

- The routed certificate export endpoint calls a model method that is commented out; it must be described as incomplete unless fixed before the implementation chapter is finalized.
- The duplicate shared scope-switch route cannot dispatch its documented POST request.
- The shared-key timeline query targets the wrong database/field path for the verified schema.
- The configurable crawler does not enforce the fingerprint deduplication assumed by renewal comments.
- The CA score has weak-key polarity/threshold caveats documented in the analysis artifacts.

## Information requiring later verification

- complete BibTeX metadata for all cited papers and authoritative TLS/CT standards;
- whether the dated local MongoDB snapshot may be used as report results;
- whether the committed IP experiment counts are acceptable as evaluation evidence (Chapter 8 uses them only as an approved, bounded transcription and not as a causal or general result);
- whether CA/vulnerability application scores should be presented prominently given their implementation caveats;
- whether the university counts appendices/front matter inside the 40–45 page target.

## Inference approval status

The complete approval register is `evidence_traceability.md`. Chapter-specific
approvals for all generated Chapters 1–9 are recorded there. Appendices remain
ungenerated. Any later inference-dependent diagram or new analytical claim must
still receive explicit approval before inclusion.

## Screenshot gap

The current 1080p recording supports four screenshots. If CA, SAN, signature/hash, shared-key, or vulnerability page screenshots are required, the application must be run and captured later. That requires a reproducible Django/PyMongo environment and should occur only during the approved report-generation stage.
