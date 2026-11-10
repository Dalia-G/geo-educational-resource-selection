# Study 2 Protocol: Competitive, Target-Only GEO with Same-Department Competitors

Status: frozen before the first Study 2 request (see `freeze/frozen_manifest.json` for the UTC freeze time and SHA-256 checksums).

## 1. Purpose

Study 1 found that the target resource was ranked first in 87.0–93.8% of requests in every condition, so a ceiling effect could have masked condition effects. Study 2 is a harder, competitive replication designed to remove that limitation. It changes three design features and adds a second model family. The query set, GEO templates, prompt, and decoding settings remain the same as in Study 1.

## 2. Design changes relative to Study 1

1. Harder candidate set. The 18 Study 1 descriptions (DOC_001–DOC_018, byte-identical) are joined by 30 same-department competitor descriptions (DOC_019–DOC_048; five per department) drawn from the MIT Learn public course API (`platform=ocw`). Each request presents all 48 resources, giving 7 same-department alternatives per target.
2. Competitive (target-only) optimization. In each request, only the query's target resource is presented in the assigned condition; the other 47 resources are presented in baseline form. This simulates one publisher optimizing a page in an unoptimized competitive field. Study 1 instead optimized all resources at once.
3. Schema-enforced output. JSON output is constrained through `response_format` (`json_schema`, `strict: true`): resource identifiers are restricted to R01–R48, and the ranking must contain exactly three items.
4. Second model family. M1 = `nvidia/nemotron-3-ultra-550b-a55b` (thinking disabled). M2 was chosen by a rule fixed in advance: the first non-NVIDIA candidate, in a fixed order, that returned schema-valid JSON in 5/5 technical test calls on a non-study prompt (`source/model2_selection_log.json`). The result was `minimaxai/minimax-m3.1-flash`. Earlier candidates either returned HTTP 502 or had no deployed function (HTTP 404) at test time.

## 3. Materials

- Queries: the 54 frozen Study 1 queries (`source/main_study_query_set.csv`, SHA-256 285cd470…f285e9). Each query has one target (`primary_doc_id`), and there are three queries per target (topic, learner intent, task-oriented).
- GEO conditions: baseline, entity_structure_geo, faq_geo, full_geo. These are produced by the same deterministic templates as Study 1 (`scripts/geo_transform.py`). The template reproduces 68 of the 72 Study 1 files byte-for-byte; the 4 remaining files differ only in topic-list segmentation. For DOC_001–DOC_018, the exact Study 1 files are used.
- Prompt: the Study 1 system prompt. The only change is the identifier range ("R01 through R48").
- Decoding: temperature 1.0, top_p 0.95, max_tokens 2048, non-streaming.

## 4. Schedule and randomization

- Each block is one (query, repetition) pair: 54 × 3 = 162 blocks. Each block has one random R01–R48 label mapping, shared across the four conditions and both models. Condition order is randomized independently for each (model, block), and block order is shuffled for each model. The schedule seed is 20261029.
- In total, 2 models × 162 blocks × 4 conditions = 1,296 requests.

## 5. Execution rules

- Before execution, the runner verifies every input against the frozen manifest.
- Requests to each model start at least 5 s apart, and the two models run concurrently.
- A transport error (connection error, timeout, HTTP 408/429/5xx, an expired credential session, or a process ending while awaiting a reply) allows up to 3 retries of the identical request. Content is never repaired or resampled.
- The run stops if the returned model identifier changes.
- Every request, attempt, and raw response is archived.

## 6. Outcomes

Primary outcome: the target resource is ranked first. The target-centered definition follows the query-design protocol. Malformed JSON, schema-invalid output, abstention, a finish reason other than `stop`, and exhausted transport retries all count as failures.

Secondary outcomes (descriptive):

- target in top 3;
- reciprocal rank of the target within the top 3;
- JSON validity;
- first rank taken by a same-department competitor (displacement);
- quote fidelity: the quote is attributed to the first-ranked resource, is ≤50 words, and appears verbatim in the text shown after whitespace normalization;
- results by query type;
- results pooled across models.

## 7. Hypotheses and analysis

- H1 (competitive advantage): within each model, at least one GEO condition changes the target's first-rank rate relative to baseline. Tested in 6 two-sided contrasts (3 GEO conditions × 2 models).
- H2 (practical equivalence): for any contrast without a detectable difference, the 90% CI falls inside ±10 percentage points (TOST at α = 0.05).
- Inference unit: the target resource (18 clusters, each with 9 paired observations: 3 queries × 3 repetitions). The cluster statistic is the mean paired difference (condition − baseline).
- Test: exact paired sign-flip permutation over the 18 resource-level differences (2^18 assignments), with Holm adjustment across the 6 primary contrasts.
- Intervals: resource-cluster percentile bootstrap (10,000 resamples, seed 20261030), reporting 95% CIs for estimation and 90% CIs for equivalence.
- Secondary contrasts are reported without multiplicity adjustment and are interpreted descriptively.

## 8. Deviations

Any deviation from this protocol will be recorded in `DEVIATIONS.md`, including when it occurred relative to execution and to outcome inspection.
