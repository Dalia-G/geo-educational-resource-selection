import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CONDITIONS = ("baseline", "entity_structure_geo", "faq_geo", "full_geo")
BOOTSTRAPS = 20000
SEED = 20261020


def percentile(values, probability):
    pos = (len(values) - 1) * probability
    lower = int(pos)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (pos - lower)


def analyze(input_path, output):
    original = input_path.read_bytes()
    reader = csv.DictReader(original.decode("utf-8-sig").splitlines())
    rows = list(reader)
    required = {"query_id", "repetition", "condition", "request_id", "block_id", "status", "first_selection_success"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Required API metrics columns are missing.")
    if len(rows) != 648 or len({r["request_id"] for r in rows}) != 648:
        raise ValueError("Expected 648 distinct requests.")
    cells = {}
    for r in rows:
        if not re.fullmatch(r"Q0(?:0[1-9]|1[0-8])_[TLA]", r["query_id"]):
            raise ValueError("Unexpected query identifier: " + r["query_id"])
        if r["condition"] not in CONDITIONS or r["repetition"] not in {"1", "2", "3"}:
            raise ValueError("Unexpected condition or repetition.")
        if r["status"] != "response":
            raise ValueError("This complete-coverage script requires response status for every request.")
        if r["first_selection_success"] not in {"0", "1"}:
            raise ValueError("Primary outcome must be 0 or 1.")
        block = r["query_id"] + "__rep" + r["repetition"]
        if r["block_id"] != block or r["request_id"] != block + "__" + r["condition"]:
            raise ValueError("Schedule identifiers are inconsistent.")
        key = (r["query_id"], r["condition"], r["repetition"])
        if key in cells:
            raise ValueError("Duplicate design cell.")
        cells[key] = int(r["first_selection_success"])
    queries = [f"Q{i:03d}_{suffix}" for i in range(1, 19) for suffix in "TLA"]
    expected = {(q, c, str(rep)) for q in queries for c in CONDITIONS for rep in (1, 2, 3)}
    if set(cells) != expected:
        raise ValueError("The 54-query by 4-condition by 3-repetition design is incomplete.")
    totals = {(q, c): sum(cells[q, c, str(rep)] for rep in (1, 2, 3)) for q in queries for c in CONDITIONS}
    query_rows = [{"query_id": q, "resource_block": q.split("_")[0], "condition": c,
                   "repetitions": 3, "success_count": totals[q, c],
                   "mean_first_selection_success": totals[q, c] / 3} for q in queries for c in CONDITIONS]
    condition_rows = [{"condition": c, "responses": 162, "queries": 54,
                       "success_count": sum(totals[q, c] for q in queries),
                       "mean_first_selection_success": sum(totals[q, c] / 3 for q in queries) / 54} for c in CONDITIONS]
    comparisons, differences = [], []
    for condition in CONDITIONS[1:]:
        delta_counts = {q: totals[q, condition] - totals[q, "baseline"] for q in queries}
        for q in queries:
            differences.append({"query_id": q, "resource_block": q.split("_")[0],
                                "condition": condition, "baseline_query_mean": totals[q, "baseline"] / 3,
                                "condition_query_mean": totals[q, condition] / 3,
                                "paired_difference": delta_counts[q] / 3})
        block_counts = [sum(delta_counts[f"Q{i:03d}_{s}"] for s in "TLA") for i in range(1, 19)]
        nonzero = [x for x in block_counts if x != 0]
        observed = abs(sum(block_counts))
        extreme = sum(abs(sum(s * x for s, x in zip(signs, nonzero))) >= observed
                      for signs in itertools.product((-1, 1), repeat=len(nonzero)))
        p = extreme / (2 ** len(nonzero))
        rng = random.Random(SEED)
        boot = sorted(sum(block_counts[rng.randrange(18)] for _ in range(18)) / 162
                      for _ in range(BOOTSTRAPS))
        comparisons.append({"condition": condition, "endpoint": "first_selection_success",
                            "queries": 54, "resource_blocks": 18,
                            "mean_difference": sum(block_counts) / 162,
                            "difference_percentage_points": 100 * sum(block_counts) / 162,
                            "ci95_low": percentile(boot, .025), "ci95_high": percentile(boot, .975),
                            "ci_method": "paired resource-block percentile bootstrap; marginal, not simultaneous",
                            "bootstrap_replicates": BOOTSTRAPS, "bootstrap_seed": SEED,
                            "improved_queries": sum(v > 0 for v in delta_counts.values()),
                            "worsened_queries": sum(v < 0 for v in delta_counts.values()),
                            "unchanged_queries": sum(v == 0 for v in delta_counts.values()),
                            "nonzero_block_totals": len(nonzero), "exact_sign_patterns": 2 ** len(nonzero),
                            "two_sided_exact_block_signflip_p": p})
    maximum = 0.0
    for rank, index in enumerate(sorted(range(3), key=lambda i: comparisons[i]["two_sided_exact_block_signflip_p"])):
        maximum = max(maximum, min(1.0, (3 - rank) * comparisons[index]["two_sided_exact_block_signflip_p"]))
        comparisons[index]["holm_adjusted_p"] = maximum
        comparisons[index]["reject_at_0_05_holm"] = maximum <= .05
    if hashlib.sha256(input_path.read_bytes()).digest() != hashlib.sha256(original).digest():
        raise RuntimeError("Input changed during analysis. No output written.")
    output.mkdir(parents=True, exist_ok=False)
    def write(name, records):
        with (output / name).open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    write("api_query_averages.csv", query_rows)
    write("api_primary_condition_summary.csv", condition_rows)
    write("api_primary_paired_differences.csv", differences)
    write("api_primary_paired_comparisons.csv", comparisons)
    provenance = {"created_utc": datetime.now(timezone.utc).isoformat(),
                  "input_sha256": hashlib.sha256(original).hexdigest(),
                  "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "input_rows": 648, "endpoint": "Original first_selection_success; no output repair or rescoring",
                  "aggregation": "Average 3 repetitions per query, then 54 query averages; 18 resource blocks each include T/L/A queries",
                  "test": "Two-sided exact resource-block sign-flip; requires joint sign symmetry/exchangeability under null",
                  "multiplicity": "Holm correction across three primary GEO-versus-baseline comparisons",
                  "bootstrap": {"type": "paired resource-block percentile", "replicates": BOOTSTRAPS, "seed": SEED,
                                "implementation_timing": "Bootstrap seed and percentile implementation set after outcomes were available; not claimed preregistered"},
                  "limitations": "Protocol supplied as draft; verify final approved analysis plan. Human evidence audit remains outstanding.",
                  "original_files_modified": False, "api_calls": 0}
    (output / "analysis_provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    for r in comparisons:
        print(f"{r['condition']}: delta={r['difference_percentage_points']:+.3f} pp, "
              f"p={r['two_sided_exact_block_signflip_p']:.6f}, Holm p={r['holm_adjusted_p']:.6f}")
    print("Saved:", output)
    print("No API calls. Original responses and primary metrics unchanged.")
    return comparisons


def main():
    parser = argparse.ArgumentParser(description="Offline API primary-endpoint analysis; original strict scores only.")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = Path(__file__).resolve().parent / "api_plans" / "main_plan_20261019T121514701660Z"
    input_path = args.input or plan / "main_results" / "per_response_metrics.csv"
    output = args.output or plan / "analysis" / ("api_primary_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    analyze(input_path, output)


if __name__ == "__main__":
    main()
