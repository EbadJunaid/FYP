#!/usr/bin/env python3
"""
Run all generic maintenance scripts for databases listed in databases.json.

Reads databases.json once at startup, then invokes every generic-*.py script in
the generic/ folder (except this file), passing --dbs and --config to each.

Prerequisites:
  pyenv activate SSL-crawler
  MongoDB running on localhost:27017

Usage:
  python run-generic.py
  python3 run-generic.py --dbs test-api-tranco test-api-pakistani
  python3 run-generic.py --dry-run
  python3 run-generic.py --verify-collections
  python3 run-generic.py --skip-verify
  python3 run-generic.py --only generic-compute-ca-stats.py generic-create-indexes.py
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Any

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from scope_utils import normalize_db_entries

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = os.path.join(SCRIPT_DIR, "databases.json")
INDEXES_SCRIPT = "generic-create-indexes.py"
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")

# Collections each compute script is expected to populate in <results_db>.
SCRIPT_RESULT_COLLECTIONS: dict[str, list[str]] = {
    "generic-compute-ca-stats.py": ["ca-analysis"],
    "generic-compute-geographic-distribution.py": ["geographic-distribution-1"],
    "generic-compute-san-analytics.py": ["san-analysis"],
    "generic-compute-shared-keys.py": ["shared-keys-detailed"],
    "generic-compute-signature-stats.py": ["signature-and-hash"],
    "generic-compute-validity-analytics.py": ["validity-analysis"],
}

# Union of all results collections (used for final verification).
ALL_RESULTS_COLLECTIONS = sorted(
    {name for names in SCRIPT_RESULT_COLLECTIONS.values() for name in names}
)


def format_duration(seconds: float) -> str:
    total_seconds = int(round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"

# Indexes referenced by generic compute scripts on main DB certificates collection.
REQUIRED_CERTIFICATE_INDEXES = [
    "idx_validity_end",
    "idx_validity_start",
    "idx_validity_length",
    "idx_key_algorithm_name",
    "idx_rsa_public_key_length",
    "idx_ecdsa_public_key_length",
    "idx_signature_algo",
    "idx_zlint_errors",
    "idx_self_signed",
    "idx_scope",
    "idx_validation_level",
    "idx_cert_fingerprint_sha256",
    "idx_public_key_fingerprint",
    "idx_domain",
    "idx_issuer_country",
    "idx_issuer_org",
    "idx_san_dns_names",
    "idx_algo_rsa_length",
    "idx_algo_ecdsa_length",
    "idx_issuer_org_validation_level",
    "idx_cert_and_public_key_fingerprint",
    "idx_scope_validity_end",
    "idx_scope_zlint_errors",
    "idx_scope_id",
    "idx_scope_validity_start",
    "idx_scope_validity_length",
    "idx_scope_algo_rsa_length",
    "idx_scope_algo_ecdsa_length",
    "idx_scope_issuer_org",
    "idx_scope_issuer_validation",
    "idx_scope_signature_algo",
    "idx_scope_self_signed",
    "idx_scope_public_key_fingerprint",
    "idx_scope_domain",
    "idx_scope_issuer_country",
    "idx_issuer_org_algo_rsa_length",
    "idx_issuer_org_algo_ecdsa_length",
    "idx_scope_issuer_algo_rsa_length",
    "idx_scope_issuer_algo_ecdsa_length",
]


def load_db_entries(config_path: str) -> list[dict[str, str]]:
    with open(config_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        return _normalize_db_entries(data)

    if isinstance(data, dict) and "databases" in data:
        return _normalize_db_entries(data["databases"])

    raise ValueError(f"Unsupported databases.json format: {config_path}")


def _normalize_db_entries(items: list[Any]) -> list[dict[str, str]]:
    return normalize_db_entries(items)


def discover_generic_scripts() -> list[str]:
    """Return generic-*.py scripts in a stable run order (indexes first)."""
    scripts = [
        name
        for name in os.listdir(SCRIPT_DIR)
        if name.startswith("generic-") and name.endswith(".py") and name not in {
            "run-generic.py",
            "generic-compute-ca-analytics.py",
            "generic-compute-issuer-validation-matrix.py",
            "generic-compute-hash-trends.py",
            "generic-compute-issuer-algorithm-matrix.py",
            "generic-compute-issuance-timeline.py",
            "generic-compute-validity-analytics-old.py",
        }
    ]
    if INDEXES_SCRIPT in scripts:
        scripts.remove(INDEXES_SCRIPT)
        scripts.sort()
        return [INDEXES_SCRIPT] + scripts
    return sorted(scripts)


def run_script(
    script_name: str,
    db_names: list[str],
    config_path: str,
    *,
    dry_run: bool,
    verify: bool,
    extra_args: list[str],
) -> None:
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.isfile(script_path):
        raise FileNotFoundError(f"Script not found: {script_path}")

    cmd = [
        sys.executable,
        script_path,
        "--dbs",
        *db_names,
        "--config",
        config_path,
    ]
    if dry_run and script_name == INDEXES_SCRIPT:
        cmd.append("--dry-run")
    if verify and script_name != INDEXES_SCRIPT:
        cmd.append("--verify")

    cmd.extend(extra_args)

    print(f"\n{'=' * 72}", flush=True)
    print(f"Running {script_name}", flush=True)
    print(f"  databases: {', '.join(db_names)}", flush=True)
    print(f"  command:   {' '.join(cmd)}", flush=True)
    print("=" * 72, flush=True)

    if dry_run and script_name != INDEXES_SCRIPT:
        print("  [DRY-RUN] skipped (only index creation supports --dry-run)", flush=True)
        return

    sys.stdout.flush()
    subprocess.run(cmd, check=True, cwd=SCRIPT_DIR)


def _collection_has_data(db, collection_name: str) -> tuple[bool, str]:
    if collection_name not in db.list_collection_names():
        return False, "missing"

    count = db[collection_name].count_documents({})
    if count == 0:
        return False, "empty"
    return True, f"{count:,} docs"


def verify_main_indexes(client: MongoClient, entries: list[dict[str, str]]) -> list[str]:
    failures: list[str] = []
    for entry in entries:
        main_db = entry["main"]
        collection = client[main_db]["certificates"]
        existing = {idx["name"] for idx in collection.list_indexes()}
        for index_name in REQUIRED_CERTIFICATE_INDEXES:
            if index_name not in existing:
                failures.append(f"{main_db}.certificates missing index {index_name}")
    return failures


def verify_results_collections(
    client: MongoClient,
    entries: list[dict[str, str]],
    *,
    collections: list[str] | None = None,
) -> list[str]:
    expected = collections or ALL_RESULTS_COLLECTIONS
    failures: list[str] = []

    for entry in entries:
        results_db_name = entry["results"]
        db = client[results_db_name]
        present = set(db.list_collection_names())

        for collection_name in expected:
            if collection_name not in present:
                failures.append(f"{results_db_name}.{collection_name}: missing")
                continue

            ok, detail = _collection_has_data(db, collection_name)
            if not ok:
                failures.append(f"{results_db_name}.{collection_name}: {detail}")

    return failures


def verify_per_script(
    client: MongoClient,
    entries: list[dict[str, str]],
    scripts_ran: list[str],
) -> list[str]:
    failures: list[str] = []
    for script_name in scripts_ran:
        collections = SCRIPT_RESULT_COLLECTIONS.get(script_name)
        if not collections:
            continue
        failures.extend(
            verify_results_collections(client, entries, collections=collections)
        )
    return failures


def ping_mongo(client: MongoClient) -> None:
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError as exc:
        raise SystemExit(
            f"Cannot connect to MongoDB at {MONGO_URI}. Is the server running?"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all generic maintenance scripts")
    parser.add_argument("--dbs", nargs="*", help="Main database names (overrides config)")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Path to databases.json")
    parser.add_argument(
        "--only",
        nargs="*",
        metavar="SCRIPT",
        help="Run only these script filenames (e.g. generic-compute-ca-stats.py)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions only")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Pass --verify to each sub-script where supported",
    )
    parser.add_argument(
        "--verify-collections",
        action="store_true",
        help="After all scripts finish, verify MongoDB collections and indexes",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip post-run collection verification (on by default unless --dry-run)",
    )
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Extra args forwarded to each sub-script (prefix with --)",
    )
    args = parser.parse_args()

    run_started_at = datetime.now()
    run_started_perf = time.perf_counter()
    print(f"Run started at: {run_started_at.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

    def print_run_timing() -> None:
        run_finished_at = datetime.now()
        elapsed = time.perf_counter() - run_started_perf
        print(f"\nRun finished at: {run_finished_at.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
        print(f"Total run time:  {format_duration(elapsed)}", flush=True)

    atexit.register(print_run_timing)

    if not os.path.isfile(args.config):
        raise SystemExit(f"Config not found: {args.config}")

    entries = load_db_entries(args.config)
    if not entries:
        raise SystemExit("No databases in config")

    if args.dbs:
        lookup = {entry["main"]: entry for entry in entries}
        entries = [
            lookup[name] if name in lookup else {"main": name, "results": f"{name}-results", "countries": []}
            for name in args.dbs
        ]

    db_names = [entry["main"] for entry in entries]
    all_scripts = discover_generic_scripts()

    if args.only:
        unknown = [name for name in args.only if name not in all_scripts]
        if unknown:
            raise SystemExit(f"Unknown script(s): {', '.join(unknown)}")
        scripts = [name for name in all_scripts if name in args.only]
    else:
        scripts = all_scripts

    extra_args = [arg for arg in args.extra_args if arg != "--"]

    print(f"Config:     {args.config}", flush=True)
    print(f"Databases:  {len(entries)}", flush=True)
    for entry in entries:
        scopes = ["all"] + list(entry.get("countries", []))
        print(f"  - {entry['main']} -> {entry['results']} scopes={', '.join(scopes)}", flush=True)
    print(f"Scripts:    {len(scripts)}", flush=True)

    if args.dry_run:
        print("\n[DRY-RUN] No scripts will modify data (indexes script prints only).", flush=True)
        for script_name in scripts:
            run_script(
                script_name,
                db_names,
                args.config,
                dry_run=True,
                verify=False,
                extra_args=extra_args,
            )
        return

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    ping_mongo(client)

    failed_scripts: list[str] = []
    for script_name in scripts:
        try:
            run_script(
                script_name,
                db_names,
                args.config,
                dry_run=False,
                verify=args.verify,
                extra_args=extra_args,
            )
        except subprocess.CalledProcessError as exc:
            failed_scripts.append(script_name)
            print(f"ERROR: {script_name} exited with code {exc.returncode}", file=sys.stderr)

    run_verify = args.verify_collections or not args.skip_verify
    if run_verify:
        print(f"\n{'=' * 72}")
        print("Verifying MongoDB indexes and pre-computed collections")
        print("=" * 72)

        index_failures = verify_main_indexes(client, entries)
        collection_failures = verify_results_collections(client, entries)
        per_script_failures = verify_per_script(client, entries, scripts)

        if index_failures:
            print("\nIndex failures:")
            for msg in index_failures:
                print(f"  - {msg}")

        if collection_failures:
            print("\nResults collection failures:")
            for msg in collection_failures:
                print(f"  - {msg}")

        if per_script_failures and per_script_failures != collection_failures:
            print("\nPer-script collection failures:")
            for msg in per_script_failures:
                if msg not in collection_failures:
                    print(f"  - {msg}")

        all_failures = sorted(set(index_failures + collection_failures))
        if all_failures:
            print(f"\nVerification FAILED ({len(all_failures)} issue(s))")
            client.close()
            if failed_scripts:
                raise SystemExit(
                    f"Scripts failed: {', '.join(failed_scripts)}; "
                    f"verification found {len(all_failures)} issue(s)"
                )
            raise SystemExit(f"Verification found {len(all_failures)} issue(s)")

        print("\nVerification PASSED")
        print(f"  - {len(REQUIRED_CERTIFICATE_INDEXES)} indexes on each main DB certificates collection")
        print(f"  - {len(ALL_RESULTS_COLLECTIONS)} results collections across {len(entries)} database(s)")

    client.close()

    if failed_scripts:
        raise SystemExit(f"One or more scripts failed: {', '.join(failed_scripts)}")


if __name__ == "__main__":
    main()
