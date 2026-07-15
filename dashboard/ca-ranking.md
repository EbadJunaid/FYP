# CA Ranking

CA Ranking ranks Certificate Authorities for the currently selected dashboard scope. The endpoint is:

```text
GET /api/ca/ranking/?group_by=ca&limit=20&scope=all
```

The fast path reads the scoped document from:

```text
<results_db>.ca-analysis / { "scope": "<current scope>" }
```

Ranking fields are stored inside each object of the `ca-list` array. The API does not keep precomputed ranking data in Python memory and it does not scan the main certificates collection for ranking.

## Storage

`generic-compute-ca-stats.py` computes normal CA analytics and ranking together. For each CA object inside `ca-list`, it stores:

```text
score
scoreRank
scoreSampleCount
coreHygiene
cryptoHealth
operationalStability
policyCompliance
riskFactors
```

`rank` still means market-share rank by certificate count. `scoreRank` means trust-score rank from the notebook formula.

## Notebook Formula

The code follows `ranking_group_wise (2).ipynb` for the scoring functions.

The safest way to say this in a presentation or viva is:

```text
The implementation is a direct code translation of the notebook formula.
The same component functions, constants, critical lint list, and final averaging structure are used.
The only extra engineering changes are database integration, scope filtering, precomputation, batching, and safe handling of bad/missing dates.
Those changes affect how data is read and stored, not the mathematical scoring formula.
```

Avoid saying "mathematically proven 100% correct" unless you have a formal proof. A stronger and safer claim is:

```text
It is implementation-equivalent to the notebook formula, and we can verify that equivalence by comparing the component functions and by running both implementations on the same certificate sample.
```

Per certificate:

```text
core_hygiene = mean(ZCS, ZHFS)
crypto_health = mean(KHS, KUS, WKLP)
operational_stability = mean(CADS, TSI, IOPS)
policy_compliance = mean(EKUVS, PICS, DVAS, NCVS)
risk_factors = mean(GNS, ACCS, REVPS)

final_score = mean(
  core_hygiene,
  crypto_health,
  operational_stability,
  policy_compliance,
  risk_factors
) * 100
```

For a CA, the script scores its leaf certificates and stores the average component scores and average final score.

## Why The Formula Matches The Notebook

The notebook has these main steps, and the backend keeps the same steps:

```text
1. Define CRITICAL_LINTS.
2. Compute zlint non-critical penalty using error=2 and warn=1.
3. Normalize zlint penalty using the 95th percentile value.
4. Compute per-certificate component scores:
   - core_hygiene
   - crypto_health
   - operational_stability
   - policy_compliance
   - risk_factors
5. Compute final certificate score as the mean of those five components.
6. For CA ranking, group certificates by issuer organization and average the certificate scores per CA.
```

The backend uses two implementations of the same formula:

```text
generic-compute-ca-stats.py
```

This precomputes the ranking and stores it in `ca-analysis.ca-list`.

```text
backend/certificates/ca_analytics/db_queries.py
```

This reads the precomputed result in `get_ranking_fast()`. If precomputed data is missing, it uses `get_ranking()` as a slow fallback and computes the same notebook formula from the main certificate collection.

The formula-related names are intentionally similar to the notebook:

```text
compute_zcs_from_lints / _compute_zcs_from_lints
compute_zhfs / _compute_zhfs
compute_khs / _compute_khs
compute_wklp / _compute_wklp
compute_kus / _compute_kus
compute_cads / _compute_cads
compute_tsi / _compute_tsi
compute_iops / _compute_iops
compute_ekuvs / _compute_ekuvs
compute_pics / _compute_pics
score_dvas_one / _score_dvas_one
compute_ncvs / _compute_ncvs
compute_gns / _compute_gns
compute_accs / _compute_accs
compute_revps / _compute_revps
```

## What Changed From The Notebook

These changes were made for production use, not to change the formula:

```text
Scope support:
The notebook reads one collection directly. The dashboard can compute per scope, such as all, pk, in, us.

Precomputation:
The notebook computes and writes CSV output. The dashboard stores CA scores inside MongoDB in ca-analysis.ca-list.

Batching:
The notebook can loop directly in memory. The dashboard streams MongoDB batches so a large dataset does not crash memory.

Bad date handling:
Some certificates can contain dates that Windows cannot convert with timestamp().
The dashboard skips invalid timestamps, which is equivalent to treating that date as unavailable.
When there is not enough valid time data, TSI returns the notebook's neutral 0.5.

CA aggregation:
The notebook scores certificates. The dashboard ranks CAs by averaging the scores of leaf certificates issued by each CA.
```

## How To Verify Correctness

Use these checks when someone asks how you know the implementation is correct:

```text
1. Compare constants:
   CRITICAL_LINTS, W_ERR=2, W_WARN=1, MAX_VALIDITY_DAYS=825, T_MAX=730, INCLUDE_ACCS=False.

2. Compare component functions:
   Each notebook scoring function has a matching backend function.

3. Compare final score:
   Both use the mean of the same five component groups and multiply by 100.

4. Run both on the same sample:
   Take 10k certificates, run the notebook and backend script, and compare component scores and final scores.

5. Compare stored output:
   Check ca-analysis.ca-list for score, scoreRank, scoreSampleCount, coreHygiene, cryptoHealth,
   operationalStability, policyCompliance, and riskFactors.
```

A good answer is:

```text
I verified correctness by keeping the same constants and component formulas from the notebook, then integrating them into the backend with only database and batching changes. The precomputed and fallback paths both use the same formula structure.
```

## Component Meanings

`ZCS`: non-critical zlint error/warn penalty, normalized by the 95th percentile penalty in the current scope.

`ZHFS`: critical zlint hygiene score. It checks the curated critical lint set from the notebook and reduces the score when those lints have `error`.

`KHS`: key health score from key size, key algorithm, and validity length.

`KUS`: key uniqueness score. Unknown keys are neutral, first-seen keys score higher, reused keys score lower.

`WKLP`: weak-key function copied from the notebook.

`CADS`: CA diversity score.

`TSI`: temporal stability score from issue timestamps.

`IOPS`: issuer operational pattern score.

`EKUVS`: extended key usage score.

`PICS`: policy identifier score for DV/OV/EV policy OIDs.

`DVAS`: validation assurance score where EV is highest, then OV, then DV.

`NCVS`: name constraints presence score.

`GNS`: geography risk score. The notebook marks IR, KP, SY, CU, and RU as risky issuer countries.

`ACCS`: AIA CA issuers score. It is neutral because `INCLUDE_ACCS` is false in the notebook.

`REVPS`: revocation presence score from OCSP and CRL endpoints.

## Common Questions And Answers

### What is the formula?

The formula ranks each certificate first, then averages certificate scores per CA.

```text
core_hygiene = mean(ZCS, ZHFS)
crypto_health = mean(KHS, KUS, WKLP)
operational_stability = mean(CADS, TSI, IOPS)
policy_compliance = mean(EKUVS, PICS, DVAS, NCVS)
risk_factors = mean(GNS, ACCS, REVPS)

final_score = mean(
  core_hygiene,
  crypto_health,
  operational_stability,
  policy_compliance,
  risk_factors
) * 100
```

For CA ranking:

```text
CA score = average(final_score of all scored leaf certificates issued by that CA)
```

### Is a higher score better?

Yes. A higher score means the CA's certificates look better according to this notebook formula.

### Is this an attack-risk score?

No. It is not a direct probability of attack and it does not predict that a CA will be attacked.

It is a certificate trust/hygiene score based on observable certificate properties:

```text
lint quality
cryptographic configuration
operational consistency
policy and validation signals
revocation and contextual risk signals
```

### What does Risk Context mean?

`riskFactors` is a score, not a penalty. Higher is better.

It is computed as:

```text
risk_factors = mean(GNS, ACCS, REVPS)
```

Meaning:

```text
GNS: issuer country signal from the notebook
ACCS: AIA issuer URL signal, neutral because INCLUDE_ACCS=False
REVPS: OCSP/CRL revocation endpoint availability
```

So Risk Context means:

```text
How good the contextual safety and revocation-support signals are.
```

It does not mean:

```text
This CA is under attack.
This CA is malicious.
This CA has a measured probability of compromise.
```

### Why are there more total CAs than ranked CAs?

`total_cas` counts issuer organizations found in the CA analytics data.

Ranking only includes CAs that have at least one scored leaf certificate. Some issuer organizations are not ranked because their records are:

```text
self-signed/root-like certificates
intermediate/CA certificates
missing issuer organization
missing enough usable scoring fields
not leaf certificates after filtering
```

So:

```text
total_cas = all issuer organizations seen
ranked CAs = issuer organizations with at least one usable scored leaf certificate
```

### Why do we filter leaf certificates?

The notebook's scoring logic is intended for end-entity/leaf certificates. Root and intermediate CA certificates behave differently and would distort the ranking.

The backend excludes certificates when:

```text
parsed.subject_dn == parsed.issuer_dn
parsed.basic_constraints.ca == true
```

### Why do we average per certificate instead of just counting certificates?

Counting only shows CA market share. Ranking should show quality/trust signals.

So the dashboard keeps both:

```text
rank: market-share rank by certificate count
scoreRank: trust-score rank by notebook score
```

### Why is Let's Encrypt sometimes rank 1 by count but not rank 1 by score?

Because market share and trust score are different. A CA can issue many certificates but still have a lower average score than a smaller CA if its component scores are lower.

### Does zlint affect the score?

Yes. ZLint affects `core_hygiene`.

```text
ZCS checks non-critical lint warnings/errors.
ZHFS checks critical lint errors.
core_hygiene = mean(ZCS, ZHFS)
```

### What happens if a certificate has missing data?

The formula uses the notebook's neutral/default behavior where possible.

Examples:

```text
missing public key fingerprint -> KUS = 0.5
not enough valid timestamps -> TSI = 0.5
ACCS disabled -> ACCS = 0.5
missing EKU -> EKUVS = 0.0
missing policy OID -> PICS = 0.0
```

### Why is bad date handling acceptable?

Some certificates can contain very old or invalid dates that Windows cannot convert to a timestamp. Without handling this, one bad certificate can crash the whole computation.

The implementation skips invalid timestamps. This does not change normal dates. It only treats unusable dates like unavailable time data, causing TSI to use the notebook's neutral fallback when needed.

### How is the dashboard fast if the formula is expensive?

The heavy computation runs in the generic precompute script:

```text
generic-compute-ca-stats.py
```

The API normally uses:

```text
get_ranking_fast()
```

which reads:

```text
<results_db>.ca-analysis
```

Only if precomputed ranking data is missing does it call:

```text
get_ranking()
```

which is the slow live fallback.

### How should I explain the final result?

A good explanation is:

```text
This page ranks Certificate Authorities by averaging notebook-based certificate trust scores for the leaf certificates issued by each CA. The score combines lint hygiene, cryptographic health, operational stability, policy compliance, and contextual revocation/risk signals. Higher scores mean better certificate hygiene according to the selected formula.
```

### What should I avoid saying?

Avoid saying:

```text
This proves the CA is secure.
This predicts attack probability.
This score is a universal trust standard.
```

Say this instead:

```text
This is a comparative ranking based on the selected notebook formula and the certificate fields available in our dataset.
```

## Backend Functions

`compute_ca_notebook_scores(source_collection, scope, limit=None)`

Reads certificates for the selected scope, filters to leaf certificates, computes the zlint normalization value, scores certificates with the notebook formula, then averages scores per CA.

`score_certificate_with_notebook_formula(doc, norm_m, seen_keys)`

Applies the notebook component functions to one certificate and returns the 0-100 final score plus component scores.

`notebook_formula_description()`

Stores a short formula description in the `ca-analysis` document so the API can return the formula with the ranking response.

`CAModel.get_ranking_fast(limit, group_by)`

Reads the scoped `ca-analysis` document, extracts scored CA objects from `ca-list`, sorts by `scoreRank`, slices by `limit`, and returns the API response. It does not use an in-memory cache and it does not run a live ranking aggregation.

`CAModel.get_ranking(limit, group_by)`

Slow fallback. If precomputed ranking fields are missing, this computes the same notebook formula from the main certificate collection for the current scope.

## Frontend Behavior

CA Analytics shows a compact CA Ranking card under the CA Market Share and Validation Level by Issuer cards.

The full page is:

```text
/dashboard/ca-ranking
```

The CA Trust Score chart shows the top 20 CAs. The Ranking Details table shows 10 CAs per page with Previous 10 and Next 10 controls until all ranked CAs are shown.

Click behavior:

```text
Click a CA ranking bar: filters the certificate table by that CA.
Click a CA row in Ranking Details: filters the certificate table by that CA.
Click a certificate row: opens /certificate/<id>.
Use global search: searches certificates directly and ignores the selected CA filter.
```

The active scope is appended by the frontend API client, so changing the country dropdown changes which `ca-analysis` document is read.

## Testing Rule

Do not test this on the full large collection during development. Use `--sample-limit 10000` or a temporary 10k database slice first.

## Certificate Score To CA Score

When we say:

```text
The system ranks certificates first and then groups by CA.
```

it means the formula is applied at certificate level first, not directly at CA level.

The process is:

```text
1. Read certificates from the selected scope.
2. Keep only leaf certificates.
3. For each leaf certificate, compute the notebook score.
4. Identify the issuing CA from parsed.issuer.organization.
5. Put each scored certificate into that CA's group.
6. Average all certificate scores inside each CA group.
7. Sort CAs by that average score.
```

So yes, conceptually we do this:

```text
Find all certificates issued by one CA.
Score every usable leaf certificate from that CA.
Average those certificate scores.
That average becomes the CA score.
```

Example:

```text
CA = Example Trust

Certificate 1 score = 80
Certificate 2 score = 70
Certificate 3 score = 90

CA score = (80 + 70 + 90) / 3
CA score = 80
```

In code, we do not need to fetch one CA separately, then another CA separately. That would be slow. Instead, the script streams certificates once and builds groups while it reads:

```text
ca_scores["Example Trust"].append(certificate_score)
ca_scores["Google Trust Services"].append(certificate_score)
ca_scores["Let's Encrypt"].append(certificate_score)
```

At the end, it averages each group.

This is why `scoreSampleCount` is stored. It tells how many certificates were actually scored for that CA.

## Why Not Score A CA Directly?

A CA is an issuer organization. It is not one certificate. The formula uses certificate fields such as:

```text
zlint results
key algorithm
key size
validity period
EKU
certificate policies
OCSP/CRL endpoints
issuer country
public key fingerprint
```

These fields exist on certificates. Therefore, we score certificates first. After that, we summarize those certificate scores into one CA score.

This gives a fairer CA ranking because it is based on the actual certificates issued by that CA.

## What Is A Leaf Certificate?

A leaf certificate is the final/end-entity certificate used by a real domain or service.

For example:

```text
Root CA certificate
  -> Intermediate CA certificate
      -> Leaf certificate for example.com
```

The leaf certificate is the one normally installed on a website/server. It represents the certificate that users and browsers actually see for a domain.

## Why We Use Only Leaf Certificates

We use only leaf certificates because the notebook formula is designed for normal issued certificates, not root/intermediate CA certificates.

Root and intermediate certificates behave differently:

```text
They can have CA=true.
They can have much longer validity periods.
They can have different key usage rules.
They are not issued for normal domains.
They are part of the trust chain, not the final website certificate.
```

If we mixed root/intermediate certificates with website certificates, the CA score could become misleading.

So the ranking filters out certificates that look like root/intermediate CA certificates.

The backend treats a certificate as not usable for ranking when:

```text
parsed.subject_dn == parsed.issuer_dn
```

This usually means self-signed/root-like certificate.

And when:

```text
parsed.basic_constraints.ca == true
```

This means the certificate is allowed to act as a CA certificate.

The ranking keeps certificates that are normal leaf/end-entity certificates.

## Simple Explanation For Presentation

You can explain it like this:

```text
We do not assign a score to a CA directly. First, we score every usable leaf certificate issued by that CA using the notebook formula. Then we take the average of those certificate scores. That average becomes the CA's trust score. We use only leaf certificates because they represent real domain/server certificates, while root and intermediate certificates have different behavior and would distort the ranking.
```

## Does Certificate Count Affect The Score?

The current CA score is an average of certificate scores.

That means certificate count does not directly increase the score.

Example:

```text
CA ABC has 2 certificates:
Certificate 1 score = 95
Certificate 2 score = 91

CA ABC score = (95 + 91) / 2 = 93
```

Another CA:

```text
CA 123 has 100,000 certificates.
Most are good, but some are weak or problematic.

Average score = 70
```

In this situation, CA ABC can rank above CA 123 even though CA ABC has only 2 certificates.

This is not a code bug. It is the meaning of an average quality score.

The score answers this question:

```text
On average, how good are the certificates issued by this CA according to the notebook formula?
```

It does not answer this question:

```text
How large or globally important is this CA?
```

Size is shown separately by:

```text
count
percentage
rank
scoreSampleCount
```

## Can This Be Misleading?

Yes, it can be misleading if someone looks only at the score and ignores certificate count.

A CA with only 2 certificates can get a very high score because both certificates are good. But that score has less statistical confidence than a CA with 100,000 scored certificates.

So the score should be interpreted together with sample size:

```text
High score + high scoreSampleCount = strong signal
High score + low scoreSampleCount = good result, but low confidence
Lower score + high scoreSampleCount = broad CA behavior, stronger evidence
Lower score + low scoreSampleCount = weak signal, needs caution
```

This is why the dashboard shows both:

```text
Trust score
Number of certificates
Scored certificates / scoreSampleCount
Market-share rank
```

## Why We Do Not Count Only Good Certificates

If CA 123 has 100,000 certificates and only the good certificates are counted, then the ranking becomes biased.

That would hide weak certificates.

The correct average should include all usable scored leaf certificates:

```text
good certificates
average certificates
weak certificates
problematic certificates
```

Because the goal is to describe the CA's overall certificate quality, not only its best certificates.

So if CA 123 has many good certificates but also many bad certificates, the bad certificates should reduce the average. That is expected.

## Better Interpretation

A clean explanation is:

```text
The score is an average quality score, not a popularity score. A small CA can rank high if its few certificates are excellent, but we must check scoreSampleCount before trusting that ranking strongly. A large CA's score is more representative because it is based on many certificates. Therefore, score and certificate count should be read together.
```

## Possible Future Improvement

If we want to avoid small CAs with only 1 or 2 certificates ranking too high, we can add a confidence adjustment.

For example:

```text
adjusted_score = raw_score * confidence_factor
```

Where:

```text
confidence_factor grows as scoreSampleCount increases
```

Another option is to show separate views:

```text
Best average score
Best score among CAs with at least 100 certificates
Best score among CAs with at least 1,000 certificates
```

For now, the dashboard keeps the notebook-based raw average score and shows certificate counts beside it so the user can interpret the ranking correctly.
