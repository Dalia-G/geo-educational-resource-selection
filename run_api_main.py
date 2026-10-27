import argparse
import csv
import getpass
import hashlib
import io
import json
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICY_VERSION = "main-runner-v1-selection-evidence-separated"


def now():
    return datetime.now(timezone.utc).isoformat()


def read_csv(path):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    return list(csv.DictReader(io.StringIO(text, newline="")))


def save(path, data):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def stop(message):
    raise SystemExit("STOPPED: " + message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def normalize(text):
    return " ".join(text.split())


def assess(response, mapping, documents, grades, qid, target):
    result = {"selection_usable": False, "first_selection_success": 0,
              "abstain": None, "ranked_doc_ids": [], "ranked_grades": [],
              "rr_at_3": 0.0, "recall_at_3": None,
              "target_hit_at_1": 0, "target_hit_at_3": 0,
              "target_rr_at_3": 0.0, "target_rank_within_top3": None,
              "quote_fidelity": "not_evaluable", "issues": []}
    issues = result["issues"]
    relevant = {d for (q, d), g in grades.items() if q == qid and g >= 2}
    if relevant:
        result["recall_at_3"] = 0.0
    choices = response.get("choices") or []
    if not choices:
        issues.append("No response choices")
        return result
    choice = choices[0]
    result["finish_reason"] = choice.get("finish_reason")
    content = (choice.get("message") or {}).get("content")
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        issues.append("Response is not valid JSON")
        return result
    if not isinstance(data, dict):
        issues.append("Response JSON is not an object")
        return result
    required = {"abstain", "ranked_resource_ids", "answer", "cited_resource_ids", "evidence_quotes"}
    if set(data) != required:
        issues.append("Incorrect response fields")
    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip() or len(answer.split()) > 150:
        issues.append("Answer missing, empty, or over 150 words")
    abstain = data.get("abstain")
    ranked = data.get("ranked_resource_ids")
    cited = data.get("cited_resource_ids")
    quotes = data.get("evidence_quotes")
    if type(abstain) is not bool:
        issues.append("Invalid abstain field")
        return result
    result["abstain"] = abstain
    if choice.get("finish_reason") != "stop":
        issues.append("Finish reason is not stop; selection unusable")
        return result
    if abstain:
        if ranked == []:
            result["selection_usable"] = True
        else:
            issues.append("Abstention has nonempty or missing ranking")
        if cited != [] or quotes != []:
            issues.append("Abstention has nonempty or missing evidence lists")
        return result
    if (not isinstance(ranked, list) or len(ranked) != 3
            or not all(isinstance(r, str) and r in mapping for r in ranked)
            or len(set(ranked)) != 3):
        issues.append("Ranking must contain three distinct valid IDs")
        return result
    result["selection_usable"] = True
    ranked_docs = [mapping[r] for r in ranked]
    ranked_grades = [grades[qid, d] for d in ranked_docs]
    result["ranked_doc_ids"] = ranked_docs
    result["ranked_grades"] = ranked_grades
    result["first_selection_success"] = int(ranked_grades[0] >= 2)
    result["rr_at_3"] = next((1 / i for i, g in enumerate(ranked_grades, 1) if g >= 2), 0.0)
    if relevant:
        result["recall_at_3"] = len(set(ranked_docs) & relevant) / len(relevant)
    if target in ranked_docs:
        rank = ranked_docs.index(target) + 1
        result["target_rank_within_top3"] = rank
        result["target_hit_at_1"] = int(rank == 1)
        result["target_hit_at_3"] = 1
        result["target_rr_at_3"] = 1 / rank
    if not isinstance(answer, str) or ranked[0] not in answer:
        issues.append("First-ranked ID not present in answer")
    if (not isinstance(cited, list) or not all(isinstance(r, str) and r in mapping for r in cited)
            or ranked[0] not in cited):
        issues.append("Invalid citations or first-ranked ID not cited")
    quote_issues = []
    if not isinstance(quotes, list) or not 1 <= len(quotes) <= 2:
        quote_issues.append("Expected one or two evidence quotes")
    else:
        for item in quotes:
            if not isinstance(item, dict) or set(item) != {"resource_id", "quote"}:
                quote_issues.append("Incorrect evidence-quote fields")
                continue
            text = item.get("quote")
            if item.get("resource_id") != ranked[0]:
                quote_issues.append("Quote not attributed to first-ranked resource")
            elif not isinstance(text, str) or not text.strip():
                quote_issues.append("Quote missing or empty")
            else:
                if len(text.split()) > 50:
                    quote_issues.append("Quote exceeds 50 words")
                if normalize(text) not in normalize(documents[mapping[ranked[0]]]):
                    quote_issues.append("Quote not found after whitespace normalization")
    issues.extend(quote_issues)
    result["quote_fidelity"] = "fail" if quote_issues else "pass"
    return result


def load_plan(plan):
    config = json.loads((plan / "api_run_config_draft.json").read_text(encoding="utf-8"))
    manifest = json.loads((plan / "api_input_manifest.json").read_text(encoding="utf-8"))
    for item in manifest:
        path = ROOT / item["path"]
        if sha(path.read_bytes()) != item["sha256"]:
            stop("Input hash changed: " + str(path))
    prompt = (plan / "system_prompt.txt").read_text(encoding="utf-8")
    if sha(prompt.encode()) != config["system_prompt_sha256"]:
        stop("System prompt hash changed")
    schedule = read_csv(plan / "api_execution_schedule.csv")
    mappings = json.loads((plan / "api_label_mappings.json").read_text(encoding="utf-8"))
    qrows = read_csv(ROOT / "queries/main_study_query_set.csv")
    queries = {r["query_id"].strip(): r["query_text"].strip() for r in qrows}
    targets = {r["query_id"].strip(): r["primary_doc_id"].strip() for r in qrows}
    grade_rows = read_csv(ROOT / config["evaluation_labels"])
    grades = {(r["query_id"].strip(), r["doc_id"].strip()): int(r["relevance_0_to_3"]) for r in grade_rows}
    docs = {condition: {} for condition in config["conditions"]}
    for item in manifest:
        path = ROOT / item["path"]
        if path.suffix == ".md" and path.parent.name in docs:
            docid = path.name[:7]
            docs[path.parent.name][docid] = path.read_text(encoding="utf-8-sig")
    expected_docs = {f"DOC_{i:03d}" for i in range(1, 19)}
    if len(queries) != 54 or len(grades) != 972 or any(set(d) != expected_docs for d in docs.values()):
        stop("Inventory validation failed")
    if set(grades) != {(q, d) for q in queries for d in expected_docs}:
        stop("Label coverage mismatch")
    if len(schedule) != 648 or len({r["request_id"] for r in schedule}) != 648:
        stop("Expected 648 distinct scheduled requests")
    blocks = {}
    for row in schedule:
        qid, condition = row["query_id"], row["condition"]
        if qid not in queries or condition not in docs or row["repetition"] not in {"1", "2", "3"}:
            stop("Invalid schedule entry")
        block = row["block_id"]
        if block != f"{qid}__rep{row['repetition']}" or row["request_id"] != f"{block}__{condition}":
            stop("Schedule IDs inconsistent")
        mapping = mappings[block]
        if set(mapping) != {f"R{i:02d}" for i in range(1, 19)} or set(mapping.values()) != expected_docs:
            stop("Invalid resource mapping")
        blocks.setdefault(block, []).append(condition)
    if len(blocks) != 162 or any(sorted(c) != sorted(docs) for c in blocks.values()):
        stop("Matched condition-block validation failed")
    for q in queries:
        orders = [tuple(mappings[f"{q}__rep{rep}"][f"R{i:02d}"] for i in range(1, 19)) for rep in range(1, 4)]
        if len(set(orders)) != 3:
            stop("Repeated presentation order for " + q)
    return config, prompt, schedule, mappings, queries, targets, grades, docs


def request_for(row, config, prompt, mappings, queries, docs):
    mapping = mappings[row["block_id"]]
    resources = "\n\n".join(
        f'<resource id="{rid}">\n{docs[row["condition"]][doc]}\n</resource>'
        for rid, doc in mapping.items())
    user = "EDUCATIONAL QUERY\n" + queries[row["query_id"]] + "\n\nRESOURCES\n" + resources
    return {"model": config["model"], "messages": [{"role": "system", "content": prompt},
            {"role": "user", "content": user}], "temperature": config["temperature"],
            "top_p": config["top_p"], "max_tokens": config["max_tokens"], "stream": False,
            "extra_body": {"chat_template_kwargs": {"enable_thinking": config["enable_thinking"]}}}


def retry_seconds(error, retry_index):
    wait = (15, 30, 60)[retry_index]
    response = getattr(error, "response", None)
    value = response.headers.get("retry-after") if response is not None else None
    if value:
        try:
            server_wait = float(value)
        except ValueError:
            try:
                server_wait = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError):
                server_wait = 0
        wait = max(wait, server_wait)
    return max(5, wait)


def export_metrics(run_dir, schedule):
    rows = []
    for item in schedule:
        path = run_dir / (item["request_id"] + "__result.json")
        if path.exists():
            result = json.loads(path.read_text(encoding="utf-8"))
            row = dict(item, status=result["status"])
            for key, value in result.get("metrics", {}).items():
                row[key] = json.dumps(value) if isinstance(value, (list, dict)) else value
            rows.append(row)
    if rows:
        fields = list(dict.fromkeys(k for row in rows for k in row))
        path = run_dir / "per_response_metrics.csv"
        temp = path.with_suffix(".csv.tmp")
        with temp.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        temp.replace(path)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Main API runner. Default: offline validation only.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    plan = Path(args.plan).resolve()
    config, prompt, schedule, mappings, queries, targets, grades, docs = load_plan(plan)
    run_dir = plan / "main_results"
    policy = {"version": POLICY_VERSION, "min_request_start_interval_seconds": 5,
              "transport_retries_after_initial": 3, "content_repair_retries": 0,
              "relevance_threshold": 2,
              "selection_usability": "Valid JSON object; boolean abstain; finish=stop; non-abstaining ranking has exactly three distinct supplied IDs. Explanation/citation/quote defects flagged separately.",
              "valid_abstention": "Boolean true and empty ranking; selection success zero. Other evidence-field defects separately flagged.",
              "quote_fidelity": "One/two quotes from first-ranked document, <=50 words each, exact substring after whitespace normalization only; absent evidence fails.",
              "missing_transport": "No usable response; exclude incomplete four-condition blocks from primary paired comparison and report zero-outcome sensitivity.",
              "recall_no_relevant_documents": "Undefined (blank), not zero",
              "aggregation": "Average repetitions within query, then average query values; do not treat requests as independent queries.",
              "paid_fallback": False}
    plan_files = ["api_run_config_draft.json", "api_input_manifest.json", "api_execution_schedule.csv", "api_label_mappings.json", "system_prompt.txt"]
    plan_hashes = {name: sha((plan / name).read_bytes()) for name in plan_files}
    policy["runner_sha256"] = sha(Path(__file__).read_bytes())
    policy["plan_file_hashes"] = plan_hashes
    print("PASS: Frozen inputs, 648 requests, and matched order blocks validated.")
    print("Model:", config["model"])
    print("Offline mode:", not args.execute)
    print("Results folder:", run_dir)
    if not args.execute:
        print("NO API REQUESTS MADE. NO API KEY READ. NO FILES WRITTEN.")
        print("Live execution requires --execute and typing RUN 648 at the confirmation prompt.")
        return
    from openai import OpenAI, APIConnectionError, APITimeoutError, APIStatusError
    if input("This sends main-study requests to NVIDIA. Type RUN 648 to proceed: ").strip() != "RUN 648":
        stop("Execution cancelled")
    key = os.environ.get("NVIDIA_API_KEY") or getpass.getpass("NVIDIA API key (hidden input): ").strip()
    if not key:
        stop("No API key supplied")
    run_dir.mkdir(exist_ok=True)
    policy_path = run_dir / "execution_policy.json"
    if policy_path.exists():
        if json.loads(policy_path.read_text(encoding="utf-8")) != policy:
            stop("Runner, policy, or plan changed since execution began")
    else:
        save(policy_path, policy)
    save(run_dir / ("session_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"),
         {"started_utc": now(), "model": config["model"], "execute_confirmation": True})
    client = OpenAI(base_url=config["base_url"], api_key=key, timeout=180, max_retries=0)
    identity_path = run_dir / "observed_model.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8")) if identity_path.exists() else None
    last_start = time.monotonic()
    try:
        for item in schedule:
            rid = item["request_id"]
            result_path = run_dir / (rid + "__result.json")
            if result_path.exists():
                continue
            request = request_for(item, config, prompt, mappings, queries, docs)
            request_hash = sha(json.dumps(request, sort_keys=True).encode())
            request_path = run_dir / (rid + "__request.json")
            if request_path.exists():
                if json.loads(request_path.read_text(encoding="utf-8"))["request_sha256"] != request_hash:
                    stop("Saved request differs: " + rid)
            else:
                save(request_path, {"schedule": item, "request_sha256": request_hash, "request": request})
            print(f"[{item['sequence']}/648] {rid}", flush=True)
            finished = False
            for attempt_number in range(1, 5):
                attempt_path = run_dir / f"{rid}__attempt_{attempt_number}.json"
                record = None
                if attempt_path.exists():
                    record = json.loads(attempt_path.read_text(encoding="utf-8"))
                    if record["status"] == "started":
                        stop("Interrupted attempt has uncertain outcome; inspect before resending: " + str(attempt_path))
                    if record["status"] == "fatal_error":
                        stop("Previous fatal API error requires review: " + str(attempt_path))
                else:
                    time.sleep(max(0, 5 - (time.monotonic() - last_start)))
                    record = {"request_id": rid, "attempt": attempt_number, "status": "started", "started_utc": now()}
                    save(attempt_path, record)
                    last_start = time.monotonic()
                    start = time.monotonic()
                    try:
                        response = client.chat.completions.create(**request)
                        record.update(status="response", response=response.model_dump(mode="json"),
                                      response_request_id=getattr(response, "_request_id", None))
                    except (APIConnectionError, APITimeoutError, APIStatusError) as error:
                        status = getattr(error, "status_code", None)
                        transient = isinstance(error, APIConnectionError) or status in (408, 429) or (status is not None and 500 <= status <= 599)
                        record.update(status="transient_error" if transient else "fatal_error",
                                      error_type=type(error).__name__, http_status=status,
                                      retry_wait_seconds=retry_seconds(error, min(attempt_number - 1, 2)))
                    record.update(finished_utc=now(), elapsed_seconds=time.monotonic() - start)
                    save(attempt_path, record)
                if record["status"] == "fatal_error":
                    stop("Fatal API error recorded; no further requests sent")
                if record["status"] == "response":
                    raw = record["response"]
                    returned_model = raw.get("model")
                    if not returned_model:
                        stop("No returned model identifier; raw response preserved")
                    if identity is None:
                        identity = {"returned_model": returned_model}
                        save(identity_path, identity)
                    elif returned_model != identity["returned_model"]:
                        stop("Returned model identifier changed; raw response preserved")
                    metrics = assess(raw, mappings[item["block_id"]], docs[item["condition"]], grades,
                                     item["query_id"], targets[item["query_id"]])
                    save(result_path, {"schedule": item, "status": "response", "attempt": attempt_number,
                                       "metrics": metrics, "usage": raw.get("usage"),
                                       "returned_model": returned_model, "system_fingerprint": raw.get("system_fingerprint")})
                    print("  selection_success=", metrics["first_selection_success"],
                          "quote_fidelity=", metrics["quote_fidelity"], "issues=", metrics["issues"], flush=True)
                    finished = True
                    break
                if attempt_number < 4:
                    wait = record.get("retry_wait_seconds", 60)
                    print(f"  transient error; backoff {wait:.0f}s before next identical attempt", flush=True)
                    time.sleep(wait)
            if not finished:
                save(result_path, {"schedule": item, "status": "transport_exhausted", "attempts": 4})
                print("  transport retries exhausted; coverage gap recorded", flush=True)
            export_metrics(run_dir, schedule)
    finally:
        rows = export_metrics(run_dir, schedule)
        print("Accounted-for scheduled requests:", len(rows), "/648")
        print("Results saved:", run_dir)
        client.close()
    print("Scheduled run completed. Human explanation/evidence audit and query-level paired analysis are still required.")


if __name__ == "__main__":
    main()