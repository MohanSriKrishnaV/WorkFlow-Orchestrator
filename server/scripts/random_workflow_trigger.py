#!/usr/bin/env python3
"""
Trigger a random number of CSV-cleaning workflows using random file IDs,
with optional pre-validation of file existence/type.

Usage:
  python scripts/random_workflow_trigger.py
  python scripts/random_workflow_trigger.py --min 5 --max 20 --file-id-min 1 --file-id-max 200
  python scripts/random_workflow_trigger.py --validate-files --max-probe-attempts 500
  python scripts/random_workflow_trigger.py --api-base http://127.0.0.1:8000 --delay-ms 150 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class TriggerResult:
    index: int
    file_id: int
    status_code: int
    ok: bool
    workflow_id: int | None = None
    first_job_id: int | None = None
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trigger random CSV-cleaning workflows with random file IDs."
    )
    parser.add_argument(
        "--api-base",
        default="http://127.0.0.1:8000",
        help="Base URL for API (default: http://127.0.0.1:8000)",
    )
    parser.add_argument("--min", dest="min_count", type=int, default=1)
    parser.add_argument("--max", dest="max_count", type=int, default=10)
    parser.add_argument("--file-id-min", type=int, default=1)
    parser.add_argument("--file-id-max", type=int, default=100)
    parser.add_argument("--delay-ms", type=int, default=100)
    parser.add_argument("--seed", type=int, default=None)

    # v2 options
    parser.add_argument(
        "--validate-files",
        action="store_true",
        help="Validate file IDs by calling GET /files/{id} and only use CSV files.",
    )
    parser.add_argument(
        "--max-probe-attempts",
        type=int,
        default=500,
        help="Max attempts to find valid CSV IDs when --validate-files is enabled (default: 500).",
    )
    return parser.parse_args()


def random_clean_options() -> dict[str, bool]:
    options = {
        "drop_missing_rows": random.choice([True, False]),
        "trim_whitespace": random.choice([True, False]),
        "lowercase_headers": random.choice([True, False]),
        "remove_empty_rows": random.choice([True, False]),
        "remove_duplicate_rows": random.choice([True, False]),
        "normalize_column_names": random.choice([True, False]),
        "remove_empty_columns": random.choice([True, False]),
    }
    if not any(options.values()):
        options[random.choice(list(options.keys()))] = True
    return options


def _request_json(method: str, url: str, payload: dict | None = None) -> tuple[int, dict | str]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status_code = resp.getcode()
            body = resp.read().decode("utf-8")
            try:
                return status_code, json.loads(body)
            except json.JSONDecodeError:
                return status_code, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else str(e)
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body
        return e.code, parsed
    except Exception as e:
        return 0, str(e)


def post_json(url: str, payload: dict) -> tuple[int, dict | str]:
    return _request_json("POST", url, payload)


def get_json(url: str) -> tuple[int, dict | str]:
    return _request_json("GET", url, None)


def looks_like_csv_file(file_obj: dict) -> bool:
    # Try common fields first
    name = str(file_obj.get("original_filename") or "").lower()
    ctype = str(file_obj.get("content_type") or "").lower()
    storage_path = str(file_obj.get("storage_path") or "").lower()

    return (
        name.endswith(".csv")
        or storage_path.endswith(".csv")
        or "text/csv" in ctype
        or "csv" in ctype
    )


def pick_valid_csv_file_id(
    api_base: str,
    file_id_min: int,
    file_id_max: int,
    max_probe_attempts: int,
) -> int | None:
    """
    Probe random file IDs and return one that exists and looks like CSV.
    """
    for _ in range(max_probe_attempts):
        candidate = random.randint(file_id_min, file_id_max)
        status, body = get_json(f"{api_base.rstrip('/')}/files/{candidate}")

        if status != 200 or not isinstance(body, dict):
            continue

        if looks_like_csv_file(body):
            return candidate

    return None


def main() -> int:
    args = parse_args()

    if args.min_count < 1 or args.max_count < 1:
        print("ERROR: --min and --max must be >= 1")
        return 2
    if args.min_count > args.max_count:
        print("ERROR: --min cannot be greater than --max")
        return 2
    if args.file_id_min < 1 or args.file_id_max < 1:
        print("ERROR: --file-id-min and --file-id-max must be >= 1")
        return 2
    if args.file_id_min > args.file_id_max:
        print("ERROR: --file-id-min cannot be greater than --file-id-max")
        return 2
    if args.delay_ms < 0:
        print("ERROR: --delay-ms cannot be negative")
        return 2
    if args.max_probe_attempts < 1:
        print("ERROR: --max-probe-attempts must be >= 1")
        return 2

    if args.seed is not None:
        random.seed(args.seed)

    total = random.randint(args.min_count, args.max_count)
    endpoint = args.api_base.rstrip("/") + "/workflows/csv-cleaning"

    print("=== Random Workflow Trigger (v2) ===")
    print(f"API Base         : {args.api_base}")
    print(f"Endpoint         : {endpoint}")
    print(f"Trigger count    : {total} (random in [{args.min_count}, {args.max_count}])")
    print(f"File ID range    : [{args.file_id_min}, {args.file_id_max}]")
    print(f"Delay            : {args.delay_ms} ms")
    print(f"Validate files   : {args.validate_files}")
    if args.validate_files:
        print(f"Max probe tries  : {args.max_probe_attempts}")
    if args.seed is not None:
        print(f"Seed             : {args.seed}")
    print("====================================\n")

    results: list[TriggerResult] = []
    delay_s = args.delay_ms / 1000.0

    for i in range(1, total + 1):
        if args.validate_files:
            file_id = pick_valid_csv_file_id(
                api_base=args.api_base,
                file_id_min=args.file_id_min,
                file_id_max=args.file_id_max,
                max_probe_attempts=args.max_probe_attempts,
            )
            if file_id is None:
                r = TriggerResult(
                    index=i,
                    file_id=-1,
                    status_code=0,
                    ok=False,
                    error=(
                        "Could not find a valid CSV file_id in range "
                        f"[{args.file_id_min}, {args.file_id_max}] "
                        f"within {args.max_probe_attempts} probe attempts."
                    ),
                )
                results.append(r)
                print(f"[{i}/{total}] FAIL no valid CSV file found for this trigger")
                if i < total and delay_s > 0:
                    time.sleep(delay_s)
                continue
        else:
            file_id = random.randint(args.file_id_min, args.file_id_max)

        payload = {
            "input_file_id": file_id,
            "clean_options": random_clean_options(),
        }

        status, body = post_json(endpoint, payload)

        if 200 <= status < 300 and isinstance(body, dict):
            r = TriggerResult(
                index=i,
                file_id=file_id,
                status_code=status,
                ok=True,
                workflow_id=body.get("workflow_id"),
                first_job_id=body.get("first_job_id"),
            )
            print(
                f"[{i}/{total}] OK  file_id={file_id} "
                f"workflow_id={r.workflow_id} first_job_id={r.first_job_id}"
            )
        else:
            err_text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
            r = TriggerResult(
                index=i,
                file_id=file_id,
                status_code=status,
                ok=False,
                error=err_text,
            )
            print(
                f"[{i}/{total}] FAIL file_id={file_id} "
                f"status={status} error={err_text}"
            )

        results.append(r)
        if i < total and delay_s > 0:
            time.sleep(delay_s)

    success_count = sum(1 for r in results if r.ok)
    fail_count = len(results) - success_count

    print("\n=== Summary ===")
    print(f"Total   : {len(results)}")
    print(f"Success : {success_count}")
    print(f"Failed  : {fail_count}")

    if fail_count:
        print("\nFailed requests:")
        for r in results:
            if not r.ok:
                print(
                    f"- idx={r.index} file_id={r.file_id} "
                    f"status={r.status_code} error={r.error}"
                )

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())