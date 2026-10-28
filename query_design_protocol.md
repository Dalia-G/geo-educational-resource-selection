# Query Design and Relevance-Judgment Protocol

## Purpose

This document prespecifies the query set and relevance-judgment rules for the 18-resource controlled retrieval experiment. Queries will be designed using the frozen source extracts and source metadata, before any retrieval is run on the 18-resource corpus.

## Query set

The study will use 54 queries:

- 18 topic queries: one per target resource.
- 18 learner-intent queries: one per target resource.
- 18 task-oriented queries: one per target resource.

Each query has one primary intended target document. A query may also have one or more secondary relevant documents when that relevance is substantively justified by the source extracts.

## Query constraints

1. Every query must be grounded in the target document's locked source extract.
2. A query must not copy a complete course title, course number, exact source-page URL, or the phrase "MIT OpenCourseWare."
3. Topic queries emphasize subject concepts, methods, or phenomena.
4. Learner-intent queries use a plausible first-person educational-search form, such as "I want to learn..." or "I need a course that explains..."
5. Task-oriented queries frame an objective, comparison, or applied learning need.
6. Queries must not include claims absent from the source extract.
7. Queries must be written without viewing main-study retrieval rankings.
8. The same query text will be evaluated against each of the four representation conditions.

## Primary relevance

The primary target document receives relevance grade 2. It is the resource from whose source extract the query was designed.

## Secondary relevance

A different document may receive relevance grade 1 only when its source extract explicitly supports the query's core information need. Secondary relevance must be documented before retrieval and must cite the shared source-supported concept in the `relevance_rationale` field.

Examples:
- A query about fundamental probability may reasonably have a mathematics primary target and another mathematics secondary target if both extracts explicitly cover probability.
- A query about basic thermodynamics may have a chemistry primary target and a heat-transfer secondary target only if both source extracts explicitly address the requested concept.

## Nonrelevance

All unlisted document-query pairs are treated as unjudged/nonrelevant for the main evaluation. The study will report that relevance judgments were source-grounded, prespecified, and primarily target-centered, rather than exhaustively assessed by independent human judges.

## Required query fields

- query_id
- query_text
- query_type
- primary_doc_id
- primary_relevance
- source_grounding
- ambiguity_note
- authoring_status

## Required qrels fields

- query_id
- doc_id
- relevance_grade
- relevance_type
- relevance_rationale
- judgment_status

## Quality control

1. Check every query against its primary source extract.
2. Check for accidental use of course titles, numbers, provider names, or URL fragments.
3. Check that a topic query, learner-intent query, and task-oriented query exist for every document.
4. Freeze