#!/usr/bin/env python3
"""
Compare old and new generic pre-compute result databases.

This script is read-only. It does not run compute scripts and does not write to
MongoDB. Use it after running old and new scripts into separate result DBs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from bson import ObjectId
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError


DEFAULT_COLLECTIONS = [
    "ca-analysis",
    "geographic-distribution-1",
    "san-analysis",
    "shared-keys-detailed",
    "signature-and-hash",
    "validity-analysis",
]

DEFAULT_IGNORED_FIELDS = {
    "ca_id",
    "certificate_ids",
    "color",
    "computed_at",
    "computedAt",
    "computation_duration_seconds",
    "days_until_expiry",
    "is_expired",
    "is_expiring_soon",
    "expiring_certificate_ids",
    "issued_certificate_ids",
    "last_computed",
    "last_updated",
    "generated_at",
    "rank",
    "sample_domains",
    "sample_sans",
    "target_database",
    "updated_at",
}

PRESENTATION_FIELDS = {"ca_id", "color", "rank"}
SAMPLE_FIELDS = {
    "certificate_ids",
    "expiring_certificate_ids",
    "issued_certificate_ids",
    "sample_domains",
    "sample_sans",
}
VOLATILE_FIELDS = {
    "computed_at",
    "computedAt",
    "computation_duration_seconds",
    "days_until_expiry",
    "generated_at",
    "is_expired",
    "is_expiring_soon",
    "last_computed",
    "last_updated",
    "target_database",
    "updated_at",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare old/new pre-computed MongoDB result collections"
    )
    parser.add_argument("--old-results", required=True, help="Old results database name")
    parser.add_argument("--new-results", required=True, help="New results database name")
    parser.add_argument(
        "--mongo-uri",
        default=os.environ.get("MONGO_URI", "mongodb://localhost:27017/"),
        help="MongoDB URI",
    )
    parser.add_argument(
        "--collections",
        nargs="*",
        default=DEFAULT_COLLECTIONS,
        help="Collections to compare",
    )
    parser.add_argument(
        "--scopes",
        nargs="*",
        help="Optional scopes to compare, e.g. all pk in. If omitted, compares all docs.",
    )
    parser.add_argument(
        "--ignore-field",
        action="append",
        default=[],
        help="Extra field name to ignore anywhere in the document. Can be repeated.",
    )
    parser.add_argument(
        "--include-presentation-fields",
        action="store_true",
        help="Compare display-only fields like color, rank, and ca_id.",
    )
    parser.add_argument(
        "--include-sample-fields",
        action="store_true",
        help="Compare sample/preview certificate and SAN arrays.",
    )
    parser.add_argument(
        "--include-volatile-fields",
        action="store_true",
        help="Compare run-time-dependent fields like timestamps and expiry booleans.",
    )
    parser.add_argument(
        "--include-boundary-trend-buckets",
        action="store_true",
        help="Compare the first hash-trends bucket even though it is a moving date-window boundary.",
    )
    parser.add_argument(
        "--max-docs",
        type=int,
        default=0,
        help="Optional max documents per collection for quick checks. 0 means no limit.",
    )
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="Print concise changed paths for mismatches.",
    )
    parser.add_argument(
        "--show-full-diff",
        action="store_true",
        help="Print full normalized old/new documents for mismatches.",
    )
    parser.add_argument(
        "--max-diff-paths",
        type=int,
        default=20,
        help="Max changed paths to show per mismatched document.",
    )
    parser.add_argument(
        "--preserve-array-order",
        action="store_true",
        help="Treat array order as significant. By default arrays are sorted after normalization.",
    )
    return parser.parse_args()


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def list_sort_key(value: Any) -> str:
    if not isinstance(value, dict):
        return stable_json(value)

    preferred_keys = [
        "_id",
        "scope",
        "public_key_hash",
        "certificate_id",
        "certificate_fingerprint",
        "name",
        "issuer",
        "organization",
        "domain",
        "period",
        "month",
        "range",
        "bucket",
        "tld",
        "validationlevel_type",
        "algorithm",
        "algorithmType",
        "key_type",
        "keyType",
        "country",
        "year",
        "monthNum",
        "rank",
    ]
    for key in preferred_keys:
        if key in value and value[key] is not None:
            return f"{key}:{stable_json(value[key])}"
    return stable_json(value)


def normalize_value(value: Any, ignored_fields: set[str], *, preserve_array_order: bool) -> Any:
    if isinstance(value, dict):
        return {
            key: normalize_value(item, ignored_fields, preserve_array_order=preserve_array_order)
            for key, item in sorted(value.items())
            if key not in ignored_fields
        }
    if isinstance(value, list):
        normalized_items = [
            normalize_value(item, ignored_fields, preserve_array_order=preserve_array_order)
            for item in value
        ]
        if preserve_array_order:
            return normalized_items
        return sorted(normalized_items, key=list_sort_key)
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def normalize_document_boundaries(document: Any, *, include_boundary_trend_buckets: bool) -> Any:
    if include_boundary_trend_buckets or not isinstance(document, dict):
        return document

    hash_trends = document.get("hash-trends")
    if isinstance(hash_trends, list) and hash_trends:
        document = dict(document)
        earliest_index = min(
            range(len(hash_trends)),
            key=lambda index: (
                hash_trends[index].get("year", 0) if isinstance(hash_trends[index], dict) else 0,
                hash_trends[index].get("quarter", 0) if isinstance(hash_trends[index], dict) else 0,
                hash_trends[index].get("period", "") if isinstance(hash_trends[index], dict) else "",
            ),
        )
        document["hash-trends"] = [
            item for index, item in enumerate(hash_trends) if index != earliest_index
        ]
    return document


def hash_doc(
    document: dict[str, Any],
    ignored_fields: set[str],
    *,
    preserve_array_order: bool,
    include_boundary_trend_buckets: bool,
) -> tuple[str, Any]:
    normalized = normalize_value(
        document,
        ignored_fields,
        preserve_array_order=preserve_array_order,
    )
    normalized = normalize_document_boundaries(
        normalized,
        include_boundary_trend_buckets=include_boundary_trend_buckets,
    )
    digest = hashlib.sha256(stable_json(normalized).encode("utf-8")).hexdigest()
    return digest, normalized


def diff_values(old_value: Any, new_value: Any, path: str = "") -> list[str]:
    if old_value == new_value:
        return []

    current_path = path or "$"
    if isinstance(old_value, dict) and isinstance(new_value, dict):
        diffs: list[str] = []
        old_keys = set(old_value)
        new_keys = set(new_value)
        for key in sorted(old_keys - new_keys):
            diffs.append(f"{current_path}.{key}: missing in new")
        for key in sorted(new_keys - old_keys):
            diffs.append(f"{current_path}.{key}: extra in new")
        for key in sorted(old_keys & new_keys):
            child_path = f"{current_path}.{key}" if path else key
            diffs.extend(diff_values(old_value[key], new_value[key], child_path))
        return diffs

    if isinstance(old_value, list) and isinstance(new_value, list):
        diffs = []
        old_len = len(old_value)
        new_len = len(new_value)
        if old_len != new_len:
            diffs.append(f"{current_path}: length changed {old_len} -> {new_len}")
        for index, (old_item, new_item) in enumerate(zip(old_value, new_value)):
            diffs.extend(diff_values(old_item, new_item, f"{current_path}[{index}]"))
        return diffs

    return [f"{current_path}: {old_value!r} -> {new_value!r}"]


def build_query(scopes: list[str] | None) -> dict[str, Any]:
    if not scopes:
        return {}
    return {"scope": {"$in": scopes}}


def load_hashes(
    collection,
    query: dict[str, Any],
    ignored_fields: set[str],
    max_docs: int,
    preserve_array_order: bool,
    include_boundary_trend_buckets: bool,
) -> dict[str, tuple[str, Any]]:
    cursor = collection.find(query).sort("_id", 1)
    if max_docs:
        cursor = cursor.limit(max_docs)

    hashes: dict[str, tuple[str, Any]] = {}
    for document in cursor:
        doc_key = str(document.get("_id"))
        hashes[doc_key] = hash_doc(
            document,
            ignored_fields,
            preserve_array_order=preserve_array_order,
            include_boundary_trend_buckets=include_boundary_trend_buckets,
        )
    return hashes


def compare_collection(
    old_collection,
    new_collection,
    query: dict[str, Any],
    ignored_fields: set[str],
    max_docs: int,
    show_diff: bool,
    show_full_diff: bool,
    max_diff_paths: int,
    preserve_array_order: bool,
    include_boundary_trend_buckets: bool,
) -> tuple[list[str], int]:
    old_hashes = load_hashes(
        old_collection,
        query,
        ignored_fields,
        max_docs,
        preserve_array_order,
        include_boundary_trend_buckets,
    )
    new_hashes = load_hashes(
        new_collection,
        query,
        ignored_fields,
        max_docs,
        preserve_array_order,
        include_boundary_trend_buckets,
    )

    issues: list[str] = []
    mismatch_count = 0
    old_keys = set(old_hashes)
    new_keys = set(new_hashes)

    for key in sorted(old_keys - new_keys):
        mismatch_count += 1
        issues.append(f"missing in new: {key}")
    for key in sorted(new_keys - old_keys):
        mismatch_count += 1
        issues.append(f"extra in new: {key}")

    for key in sorted(old_keys & new_keys):
        old_digest, old_normalized = old_hashes[key]
        new_digest, new_normalized = new_hashes[key]
        if old_digest == new_digest:
            continue
        mismatch_count += 1
        issues.append(f"content changed: {key}")
        if show_diff:
            diff_paths = diff_values(old_normalized, new_normalized)
            for diff_path in diff_paths[:max_diff_paths]:
                issues.append(f"  {diff_path}")
            if len(diff_paths) > max_diff_paths:
                issues.append(f"  ... {len(diff_paths) - max_diff_paths} more changed path(s)")
        if show_full_diff:
            issues.append(f"  old: {json.dumps(old_normalized, indent=2, default=str)}")
            issues.append(f"  new: {json.dumps(new_normalized, indent=2, default=str)}")

    return issues, mismatch_count


def main() -> None:
    args = parse_args()
    ignored_fields = set(DEFAULT_IGNORED_FIELDS)
    if args.include_presentation_fields:
        ignored_fields -= PRESENTATION_FIELDS
    if args.include_sample_fields:
        ignored_fields -= SAMPLE_FIELDS
    if args.include_volatile_fields:
        ignored_fields -= VOLATILE_FIELDS
    ignored_fields.update(args.ignore_field)

    client = MongoClient(args.mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        client.admin.command("ping")
    except ServerSelectionTimeoutError as exc:
        raise SystemExit(f"Cannot connect to MongoDB at {args.mongo_uri}") from exc

    old_db = client[args.old_results]
    new_db = client[args.new_results]
    query = build_query(args.scopes)

    total_issues = 0
    print(f"Old results DB: {args.old_results}")
    print(f"New results DB: {args.new_results}")
    print(f"Collections:    {', '.join(args.collections)}")
    print(f"Scopes:         {', '.join(args.scopes) if args.scopes else 'all documents'}")
    print(f"Ignored fields: {', '.join(sorted(ignored_fields))}")
    print(f"Array order:    {'preserved' if args.preserve_array_order else 'ignored'}")
    print(
        "Trend boundary: "
        f"{'included' if args.include_boundary_trend_buckets else 'ignored for first hash-trends bucket'}"
    )
    if args.max_docs:
        print(f"Max docs:       {args.max_docs} per collection")

    for collection_name in args.collections:
        print(f"\nComparing {collection_name}...")
        old_collection = old_db[collection_name]
        new_collection = new_db[collection_name]

        issues, mismatch_count = compare_collection(
            old_collection,
            new_collection,
            query,
            ignored_fields,
            args.max_docs,
            args.show_diff,
            args.show_full_diff,
            args.max_diff_paths,
            args.preserve_array_order,
            args.include_boundary_trend_buckets,
        )

        if issues:
            total_issues += mismatch_count
            print(f"  FAILED ({mismatch_count} issue(s))")
            for issue in issues[:50]:
                print(f"  - {issue}")
            if len(issues) > 50:
                print(f"  ... {len(issues) - 50} more issue(s)")
        else:
            print("  OK")

    client.close()

    if total_issues:
        raise SystemExit(f"\nComparison FAILED with {total_issues} issue(s)")
    print("\nComparison PASSED: old and new normalized results match")


if __name__ == "__main__":
    main()
