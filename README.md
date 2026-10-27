
# GEO for Educational Resource Selection

Research materials for a controlled experiment evaluating Generative Engine Optimization (GEO) for educational resource selection using a large language model.

## Study Overview

The experiment compares four representations of educational resources:

- Baseline
- Entity-structure GEO
- FAQ GEO
- Full GEO

The research examines resource-selection performance and distinguishes selection outcomes from response-format and supporting-evidence quality.

## Repository Status

This repository is being assembled for research sharing.

The presence of a file does not imply that it has been independently validated. The release inventory and accompanying documentation should identify which materials are included, their provenance, and any outstanding limitations.

## Research Materials

The research package includes or is intended to include:

- Educational-resource descriptions
- Experimental prompts and execution plans
- Experiment runner and scoring scripts
- Original model-response attempts
- Per-response metrics
- Primary statistical-analysis scripts and outputs
- Response-quality audit and refusal-review materials
- Reporting tables and provenance documentation

Consult the actual repository contents to determine which materials are currently available.

## Authoritative Records

Original raw attempts are the authoritative records of model responses.

Processed metrics, review classifications, copied response text, and reporting tables are derived artifacts. They do not replace the original records.

Technical diagnostics, pilot runs, and older experimental designs must remain distinguishable from the main experiment.

## Reproduction

Analysis of saved experimental outputs is separate from executing new API requests.

The primary analysis script is `analyze_api_primary.py`. Consult the script and accompanying reproduction instructions for input requirements and output locations.

New model requests are not required merely to reproduce analyses of saved outputs.

## Review Procedure and AI Assistance

Review documentation must state:

- Who reviewed the responses
- What blinding actually occurred
- Whether AI suggested or edited classifications or rationales
- How final classifications were determined

Independent review, blinded review, and unaided human classification must not be inferred unless explicitly documented.

AI assistance used to assemble a reporting package is distinct from AI assistance used to classify responses.

## Text Fidelity and Encoding


Copied response text must not be described as exactly preserved unless comparison against canonical sources is documented.

Preserve original files. Label any converted, corrected, or redacted copies as derived artifacts and document the changes.

## Reporting Package

A reporting package may contain transcribed summaries rather than freshly rerun analyses.

Its own README and provenance records should be retained alongside its files. Reporting summaries do not replace the complete raw-data archive or analysis outputs.

## Security

Do not include API keys, authentication tokens, passwords, or private environment files.

Check scripts, configuration files, logs, and repository history before public release.

## Licensing

Consult `LICENSE` and any file-specific notices before reuse.

Third-party educational content remains subject to its original permissions and restrictions. Do not assume that the repository's software license applies to every dataset or source document.

## Citation

Citation metadata and any archived-release DOI will be added when available.
