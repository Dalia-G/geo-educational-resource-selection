# Study 2: Competitive, Target-Only GEO with Same-Department Competitors

This folder holds every material needed to inspect, reproduce, or re-analyze Study 2 of the manuscript submitted to *Information* (MDPI). The Study 1 materials sit in the repository root and are unchanged.

## What changed relative to Study 1

| Feature | Study 1 | Study 2 |
|---|---|---|
| Resources per request | 18 | 48 (18 targets + 30 same-department competitors) |
| Optimization scenario | all resources in the assigned condition | target only; 47 competitors always baseline |
| Output constraint | JSON requested in the prompt | strict JSON schema enforced at decoding (`response_format`) |
| Models | Nemotron 3 Ultra | Nemotron 3 Ultra (M1) + MiniMax M3.1 Flash (M2) |
| Queries | 54 frozen queries | the same 54 frozen queries (SHA-256 `285cd470…f285e9`) |
| Requests | 648 | 1296 |

## Folder layout

| Path | Content |
|---|---|
| `protocol_study2.md` | Prespecified protocol: hypotheses, endpoints, analysis, ±10 pp equivalence margin |
| `freeze/frozen_manifest.json` | SHA-256 of all execution inputs and analysis code, plus the UTC freeze time (recorded before the first request) |
| `DEVIATIONS.md` | Deviations from the protocol, with their timing |
| `study2_config.json` | Models, decoding settings, seeds, retry and spacing rules |
| `system_prompt_study2.txt` | System prompt (identical to Study 1 apart from the identifier range R01–R48) |
| `source/main_study_query_set.csv` | The 54 frozen queries |
| `source/ocw_catalog_raw.json` | MIT Learn API catalogue snapshot (2587 OCW courses) used to select competitors |
| `source/model2_selection_log.json` | Prespecified second-model selection rule, with every test call |
| `source/nvidia_model_catalog_20261029.json` | Models listed by the endpoint on the selection date |
| `source/study1_corpus/` | Study 1 corpus files, copied byte-for-byte |
| `corpus/{baseline,entity_structure_geo,faq_geo,full_geo}/` | 48 × 4 = 192 resource files |
| `corpus/corpus_manifest.json` | SHA-256 for every corpus file |
| `corpus/competitor_metadata.csv` | The 30 competitors: course number, title, department, term, source URL, closest Study 1 target |
| `corpus/document_departments.csv` | Department group for all 48 resources |
| `schedule/study2_schedule.csv` | 1296 scheduled requests (model, block, condition, order) |
| `schedule/study2_label_mappings.json` | R01–R48 mapping for each of the 162 blocks (shared across conditions and models) |
| `scripts/` | Corpus construction, GEO templates, schedule, freeze, runner, driver, analysis, feasibility pilot, model selection |
| `runs_raw.zip` | Every request, attempt, raw API response, and scored result (`runs/M1`, `runs/M2`) |
| `pilot/` | Technical feasibility calls with one non-study query (not analyzed) |
| `analysis/study2_request_level.csv` | One row per request with all derived outcomes |
| `analysis/study2_results.json` | Full output of the prespecified analysis |
| `analysis/replay_check.json` | Re-scoring of all archived raw responses (must match the stored metrics) |
| `logs/run.log` | Execution log |

## Reproduce

```bash
pip install requests numpy
python scripts/build_corpus.py         # rebuilds corpus/ and corpus_manifest.json
python scripts/make_schedule.py        # rebuilds schedule/ from seed 20261029
python scripts/freeze.py               # writes a NEW manifest (the archived one is authoritative)
# execution needs an NVIDIA API key; the scripts route requests through an HTTPS proxy that injects it
python scripts/run_study2.py           # resumes from runs/ checkpoints; verifies the frozen manifest first
python scripts/analyze_study2.py       # writes analysis/
```

To re-analyze without calling any API, unzip `runs_raw.zip` into this folder and run `python scripts/analyze_study2.py`.

## Licenses

The code is released under the MIT License (see the repository root). The MIT OpenCourseWare course descriptions are reproduced under the Creative Commons Attribution–NonCommercial–ShareAlike 4.0 license (https://ocw.mit.edu/terms/); see `OCW_LICENSE_NOTICE.md`.

## Verify the freeze

```bash
python - <<'PY'
import json, hashlib
m = json.load(open('freeze/frozen_manifest.json'))
bad = [f['path'] for s in ('files', 'analysis_files') for f in m[s]
       if hashlib.sha256(open(f['path'], 'rb').read()).hexdigest() != f['sha256']]
print('freeze_utc', m['freeze_utc'], '| mismatches:', bad or 'none')
PY
```
All frozen files in this folder match the manifest. The first study request was sent after the manifest timestamp (see `logs/run.log`).
