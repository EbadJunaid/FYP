#!/usr/bin/env python3
"""
Generic geographic distribution pre-compute script.

Reads databases.json unless --dbs is provided, and writes to <results_db>.geographic-distribution-1.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pymongo import MongoClient


GENERIC_TLDS = {
    "com", "net", "org", "edu", "gov", "mil", "int",
    "info", "biz", "name", "pro", "mobi", "tel", "travel",
    "asia", "cat", "coop", "jobs", "museum", "aero", "post",
    "io", "ai", "co", "me", "tv", "cc", "ws", "tk", "ml", "ga", "cf", "gq",
    "dev", "app", "page", "cloud", "online", "site", "website", "tech", "store",
    "blog", "shop", "web", "space", "digital", "network", "systems", "software",
    "email", "host", "domains", "link", "click", "today", "world", "global",
    "xyz", "top", "club", "vip", "icu", "live", "fun", "press", "news",
}

TLD_TO_COUNTRY = {
    "us": "United States", "ca": "Canada", "mx": "Mexico",
    "gt": "Guatemala", "bz": "Belize", "sv": "El Salvador", "hn": "Honduras",
    "ni": "Nicaragua", "cr": "Costa Rica", "pa": "Panama", "cu": "Cuba",
    "jm": "Jamaica", "ht": "Haiti", "do": "Dominican Republic", "tt": "Trinidad and Tobago",
    "bb": "Barbados", "bs": "Bahamas", "ag": "Antigua and Barbuda", "dm": "Dominica",
    "gd": "Grenada", "kn": "Saint Kitts and Nevis", "lc": "Saint Lucia",
    "vc": "Saint Vincent and the Grenadines",
    "br": "Brazil", "ar": "Argentina", "co": "Colombia", "cl": "Chile",
    "pe": "Peru", "ve": "Venezuela", "ec": "Ecuador", "bo": "Bolivia",
    "py": "Paraguay", "uy": "Uruguay", "gy": "Guyana", "sr": "Suriname",
    "uk": "United Kingdom", "co.uk": "United Kingdom", "gb": "United Kingdom",
    "ie": "Ireland", "fr": "France", "es": "Spain", "pt": "Portugal",
    "de": "Germany", "nl": "Netherlands", "be": "Belgium", "lu": "Luxembourg",
    "ch": "Switzerland", "at": "Austria", "it": "Italy", "gr": "Greece",
    "se": "Sweden", "no": "Norway", "dk": "Denmark", "fi": "Finland",
    "is": "Iceland",
    "pl": "Poland", "cz": "Czech Republic", "sk": "Slovakia", "hu": "Hungary",
    "ro": "Romania", "bg": "Bulgaria", "si": "Slovenia", "hr": "Croatia",
    "rs": "Serbia", "ba": "Bosnia and Herzegovina", "mk": "North Macedonia",
    "al": "Albania", "me": "Montenegro", "xk": "Kosovo",
    "ee": "Estonia", "lv": "Latvia", "lt": "Lithuania",
    "ru": "Russia", "ua": "Ukraine", "by": "Belarus", "md": "Moldova",
    "ge": "Georgia", "am": "Armenia", "az": "Azerbaijan",
    "tr": "Turkey", "il": "Israel", "ps": "Palestine", "jo": "Jordan",
    "lb": "Lebanon", "sy": "Syria", "iq": "Iraq", "ir": "Iran",
    "sa": "Saudi Arabia", "ae": "United Arab Emirates", "kw": "Kuwait",
    "qa": "Qatar", "bh": "Bahrain", "om": "Oman", "ye": "Yemen",
    "kz": "Kazakhstan", "uz": "Uzbekistan", "tm": "Turkmenistan",
    "kg": "Kyrgyzstan", "tj": "Tajikistan", "af": "Afghanistan",
    "in": "India", "pk": "Pakistan", "bd": "Bangladesh", "lk": "Sri Lanka",
    "np": "Nepal", "bt": "Bhutan", "mv": "Maldives",
    "th": "Thailand", "vn": "Vietnam", "sg": "Singapore", "my": "Malaysia",
    "id": "Indonesia", "ph": "Philippines", "mm": "Myanmar", "kh": "Cambodia",
    "la": "Laos", "bn": "Brunei", "tl": "Timor-Leste",
    "cn": "China", "jp": "Japan", "kr": "South Korea", "kp": "North Korea",
    "mn": "Mongolia", "tw": "Taiwan", "hk": "Hong Kong", "mo": "Macau",
    "au": "Australia", "com.au": "Australia", "nz": "New Zealand",
    "pg": "Papua New Guinea", "fj": "Fiji", "sb": "Solomon Islands",
    "vu": "Vanuatu", "ws": "Samoa", "ki": "Kiribati", "to": "Tonga",
    "fm": "Micronesia", "mh": "Marshall Islands", "pw": "Palau",
    "nr": "Nauru", "tv": "Tuvalu",
    "eg": "Egypt", "ly": "Libya", "tn": "Tunisia", "dz": "Algeria",
    "ma": "Morocco", "sd": "Sudan", "ss": "South Sudan",
    "ng": "Nigeria", "gh": "Ghana", "ci": "Cote d'Ivoire", "sn": "Senegal",
    "ml": "Mali", "bf": "Burkina Faso", "ne": "Niger", "gn": "Guinea",
    "sl": "Sierra Leone", "lr": "Liberia", "tg": "Togo", "bj": "Benin",
    "mr": "Mauritania", "gm": "Gambia", "gw": "Guinea-Bissau",
    "cv": "Cape Verde",
    "cd": "Democratic Republic of Congo", "cg": "Republic of Congo",
    "cm": "Cameroon", "cf": "Central African Republic", "td": "Chad",
    "ga": "Gabon", "gq": "Equatorial Guinea", "st": "Sao Tome and Principe",
    "ke": "Kenya", "tz": "Tanzania", "ug": "Uganda", "rw": "Rwanda",
    "bi": "Burundi", "et": "Ethiopia", "so": "Somalia", "dj": "Djibouti",
    "er": "Eritrea", "sc": "Seychelles", "mu": "Mauritius", "km": "Comoros",
    "mg": "Madagascar",
    "za": "South Africa", "zw": "Zimbabwe", "zm": "Zambia", "mw": "Malawi",
    "mz": "Mozambique", "bw": "Botswana", "na": "Namibia", "sz": "Eswatini",
    "ls": "Lesotho", "ao": "Angola",
}


def get_default_config_path():
    script_dir = os.path.dirname(__file__)
    local = os.path.join(script_dir, "databases.json")
    if os.path.exists(local):
        return local
    parent = os.path.abspath(os.path.join(script_dir, "..", "databases.json"))
    return parent


def load_db_entries(config_path):
    with open(config_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        return _normalize_db_entries(data)

    if isinstance(data, dict) and "databases" in data:
        return _normalize_db_entries(data["databases"])

    raise ValueError("Unsupported databases.json format")


def _normalize_db_entries(items):
    entries = []
    for item in items:
        if isinstance(item, str):
            entries.append({"main": item, "results": f"{item}-results"})
        elif isinstance(item, dict):
            main_db = item.get("main") or item.get("db") or item.get("name")
            results_db = item.get("results") or (f"{main_db}-results" if main_db else None)
            if main_db:
                entries.append({"main": main_db, "results": results_db})
        else:
            raise ValueError("Unsupported database entry in list")
    return entries


def resolve_targets(db_names, entries):
    if not db_names:
        return entries

    lookup = {entry["main"]: entry for entry in entries}
    targets = []
    for name in db_names:
        if name in lookup:
            targets.append(lookup[name])
        else:
            targets.append({"main": name, "results": f"{name}-results"})
    return targets


def get_tld_country(domain):
    if not domain:
        return "Others"

    parts = domain.lower().split(".")
    if len(parts) >= 2:
        two_part = ".".join(parts[-2:])
        # print(f"Domain: {domain}, Two-part TLD: {two_part}")
        if two_part in TLD_TO_COUNTRY:
            return TLD_TO_COUNTRY[two_part]

        tld = parts[-1]
        if tld in GENERIC_TLDS:
            return "Others"
        if tld in TLD_TO_COUNTRY:
            return TLD_TO_COUNTRY[tld]
        return "Others"

    return "Others"


def compute_geographic_distribution(client, main_db, results_db, limit=None, verify=False):
    source_collection = client[main_db]["certificates"]
    target_collection_name = "geographic-distribution-1"
    target_collection = client[results_db][target_collection_name]

    query = {"domain": {"$exists": True, "$ne": None, "$ne": ""}}
    projection = {"_id": 1, "domain": 1}

    cursor = source_collection.find(query, projection)
    # print(f"cursor first enrty: {cursor[0] if cursor.count() > 0 else 'No entries'}")

    if limit:
        cursor = cursor.limit(limit)

    country_groups = {}
    processed_count = 0

    for doc in cursor:
        cert_id = doc["_id"]
        domain = doc.get("domain", "")
        country = get_tld_country(domain)

        if country not in country_groups:
            country_groups[country] = {
                "count": 0,
                "certificate_ids": []
            }

        group = country_groups[country]
        group["count"] += 1
        if len(group["certificate_ids"]) < 1000:
            group["certificate_ids"].append(cert_id)

        processed_count += 1

    sorted_countries = sorted(country_groups.items(), key=lambda x: x[1]["count"], reverse=True)
    total_certificates = sum(group["count"] for group in country_groups.values())
    max_count = sorted_countries[0][1]["count"] if sorted_countries else 1

    colors = [
        "#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444",
        "#06b6d4", "#14b8a6", "#6366f1", "#ec4899", "#84cc16",
        "#f97316", "#a855f7", "#22c55e", "#0ea5e9", "#d946ef",
        "#eab308", "#6b7280",
    ]

    country_docs = []
    for i, (country, group) in enumerate(sorted_countries):
        count = group["count"]
        percentage = round((count / total_certificates) * 100, 3) if total_certificates else 0
        certificate_ids = group["certificate_ids"]
        country_docs.append({
            "_id": country,
            "country": country,
            "count": count,
            "percentage": percentage,
            "color": colors[i % len(colors)],
            "rank": i + 1,
            "certificate_ids": certificate_ids,
            "has_more": count > len(certificate_ids),
            "computed_at": datetime.now(timezone.utc),
            "source_database": main_db,
            "source_collection": "certificates",
            "testing_mode": bool(limit),
        })

    target_collection.delete_many({})
    if country_docs:
        batch_size = 100
        for i in range(0, len(country_docs), batch_size):
            target_collection.insert_many(country_docs[i:i + batch_size])

    target_collection.create_index("rank")
    target_collection.create_index("count")
    target_collection.create_index("computed_at")

    metadata = {
        "_id": "metadata",
        "last_computed": datetime.now(timezone.utc),
        "computation_duration_seconds": 0,
        "total_countries": len(country_docs),
        "total_certificates": total_certificates,
        "source_database": main_db,
        "source_collection": "certificates",
        "target_database": results_db,
        "target_collection": target_collection_name,
        "testing_mode": bool(limit),
        "documents_processed": processed_count,
    }
    target_collection.replace_one({"_id": "metadata"}, metadata, upsert=True)

    if verify:
        stored_count = target_collection.count_documents({"_id": {"$ne": "metadata"}})
        if stored_count != len(country_docs):
            raise RuntimeError("Verification failed: record count mismatch")
        if sum(doc["count"] for doc in country_docs) != total_certificates:
            raise RuntimeError("Verification failed: total count mismatch")
        stored_meta = target_collection.find_one({"_id": "metadata"})
        if stored_meta and stored_meta.get("total_certificates") != total_certificates:
            raise RuntimeError("Verification failed: metadata total mismatch")


def main():
    parser = argparse.ArgumentParser(description="Generic geographic distribution pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--limit", type=int, default=None, help="Limit documents processed")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        compute_geographic_distribution(
            client,
            target["main"],
            target["results"],
            limit=args.limit,
            verify=args.verify,
        )
    client.close()


if __name__ == "__main__":
    main()
