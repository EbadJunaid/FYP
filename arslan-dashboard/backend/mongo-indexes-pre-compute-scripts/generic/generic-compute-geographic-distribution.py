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
from scope_utils import create_index_if_missing, get_scope_filter, get_scopes_for_entry, merge_scope_query, normalize_db_entries, scoped_doc_id


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
    "ac": "Ascension Island",
    "ad": "Andorra",
    "ae": "United Arab Emirates",
    "af": "Afghanistan",
    "ag": "Antigua and Barbuda",
    "ai": "Anguilla",
    "al": "Albania",
    "am": "Armenia",
    "ao": "Angola",
    "ar": "Argentina",
    "as": "American Samoa",
    "at": "Austria",
    "au": "Australia",
    "aw": "Aruba",
    "ax": "Åland Islands",
    "az": "Azerbaijan",
    "ba": "Bosnia and Herzegovina",
    "bb": "Barbados",
    "bd": "Bangladesh",
    "be": "Belgium",
    "bf": "Burkina Faso",
    "bg": "Bulgaria",
    "bh": "Bahrain",
    "bi": "Burundi",
    "bj": "Benin",
    "bm": "Bermuda",
    "bn": "Brunei",
    "bo": "Bolivia",
    "br": "Brazil",
    "bs": "Bahamas",
    "bt": "Bhutan",
    "bw": "Botswana",
    "by": "Belarus",
    "bz": "Belize",
    "ca": "Canada",
    "cc": "Cocos (Keeling) Islands",
    "cd": "Democratic Republic of Congo",
    "cf": "Central African Republic",
    "cg": "Republic of Congo",
    "ch": "Switzerland",
    "ci": "Cote d'Ivoire",
    "cl": "Chile",
    "cm": "Cameroon",
    "cn": "China",
    "co": "Colombia",
    "co.uk": "United Kingdom",
    "com.au": "Australia",
    "cr": "Costa Rica",
    "cu": "Cuba",
    "cv": "Cape Verde",
    "cw": "Curaçao",
    "cx": "Christmas Island",
    "cy": "Cyprus",
    "cz": "Czech Republic",
    "de": "Germany",
    "dj": "Djibouti",
    "dk": "Denmark",
    "dm": "Dominica",
    "do": "Dominican Republic",
    "dz": "Algeria",
    "ebad": "ebad",
    "ec": "Ecuador",
    "ee": "Estonia",
    "eg": "Egypt",
    "er": "Eritrea",
    "es": "Spain",
    "et": "Ethiopia",
    "eu": "European Union",
    "fi": "Finland",
    "fj": "Fiji",
    "fm": "Micronesia",
    "fo": "Faroe Islands",
    "fr": "France",
    "ga": "Gabon",
    "gb": "United Kingdom",
    "gd": "Grenada",
    "ge": "Georgia",
    "gf": "French Guiana",
    "gg": "Guernsey",
    "gh": "Ghana",
    "gi": "Gibraltar",
    "gl": "Greenland",
    "gm": "Gambia",
    "gn": "Guinea",
    "gp": "Guadeloupe",
    "gq": "Equatorial Guinea",
    "gr": "Greece",
    "gs": "South Georgia and the South Sandwich Islands",
    "gt": "Guatemala",
    "gw": "Guinea-Bissau",
    "gy": "Guyana",
    "hk": "Hong Kong",
    "hm": "Heard Island and McDonald Islands",
    "hn": "Honduras",
    "hr": "Croatia",
    "ht": "Haiti",
    "hu": "Hungary",
    "id": "Indonesia",
    "ie": "Ireland",
    "il": "Israel",
    "im": "Isle of Man",
    "in": "India",
    "io": "British Indian Ocean Territory",
    "iq": "Iraq",
    "ir": "Iran",
    "is": "Iceland",
    "it": "Italy",
    "je": "Jersey",
    "jm": "Jamaica",
    "jo": "Jordan",
    "jp": "Japan",
    "ke": "Kenya",
    "kg": "Kyrgyzstan",
    "kh": "Cambodia",
    "ki": "Kiribati",
    "km": "Comoros",
    "kn": "Saint Kitts and Nevis",
    "kp": "North Korea",
    "kr": "South Korea",
    "kw": "Kuwait",
    "ky": "Cayman Islands",
    "kz": "Kazakhstan",
    "la": "Laos",
    "lb": "Lebanon",
    "lc": "Saint Lucia",
    "li": "Liechtenstein",
    "lk": "Sri Lanka",
    "lr": "Liberia",
    "ls": "Lesotho",
    "lt": "Lithuania",
    "lu": "Luxembourg",
    "lv": "Latvia",
    "ly": "Libya",
    "ma": "Morocco",
    "mc": "Monaco",
    "md": "Moldova",
    "me": "Montenegro",
    "mg": "Madagascar",
    "mh": "Marshall Islands",
    "mk": "North Macedonia",
    "ml": "Mali",
    "mm": "Myanmar",
    "mn": "Mongolia",
    "mo": "Macau",
    "mp": "Northern Mariana Islands",
    "mr": "Mauritania",
    "ms": "Montserrat",
    "mt": "Malta",
    "mu": "Mauritius",
    "mv": "Maldives",
    "mw": "Malawi",
    "mx": "Mexico",
    "my": "Malaysia",
    "mz": "Mozambique",
    "na": "Namibia",
    "nc": "New Caledonia",
    "ne": "Niger",
    "ng": "Nigeria",
    "ni": "Nicaragua",
    "nl": "Netherlands",
    "no": "Norway",
    "np": "Nepal",
    "nr": "Nauru",
    "nu": "Niue",
    "nz": "New Zealand",
    "om": "Oman",
    "pa": "Panama",
    "pe": "Peru",
    "pf": "French Polynesia",
    "pg": "Papua New Guinea",
    "ph": "Philippines",
    "pk": "Pakistan",
    "pl": "Poland",
    "pm": "Saint Pierre and Miquelon",
    "pn": "Pitcairn Islands",
    "pr": "Puerto Rico",
    "ps": "Palestine",
    "pt": "Portugal",
    "pw": "Palau",
    "py": "Paraguay",
    "qa": "Qatar",
    "re": "Réunion",
    "ro": "Romania",
    "rs": "Serbia",
    "ru": "Russia",
    "rw": "Rwanda",
    "sa": "Saudi Arabia",
    "sb": "Solomon Islands",
    "sc": "Seychelles",
    "sd": "Sudan",
    "se": "Sweden",
    "sg": "Singapore",
    "sh": "Saint Helena",
    "si": "Slovenia",
    "sk": "Slovakia",
    "sl": "Sierra Leone",
    "sm": "San Marino",
    "sn": "Senegal",
    "so": "Somalia",
    "soy": "say",
    "sr": "Suriname",
    "ss": "South Sudan",
    "st": "Sao Tome and Principe",
    "sv": "El Salvador",
    "sx": "Sint Maarten",
    "sy": "Syria",
    "sz": "Eswatini",
    "tc": "Turks and Caicos Islands",
    "td": "Chad",
    "tf": "French Southern and Antarctic Lands",
    "tg": "Togo",
    "th": "Thailand",
    "tj": "Tajikistan",
    "tk": "Tokelau",
    "tl": "Timor-Leste",
    "tm": "Turkmenistan",
    "tn": "Tunisia",
    "to": "Tonga",
    "tr": "Turkey",
    "tt": "Trinidad and Tobago",
    "tv": "Tuvalu",
    "tw": "Taiwan",
    "tz": "Tanzania",
    "ua": "Ukraine",
    "ug": "Uganda",
    "uk": "United Kingdom",
    "us": "United States",
    "uy": "Uruguay",
    "uz": "Uzbekistan",
    "vc": "Saint Vincent and the Grenadines",
    "ve": "Venezuela",
    "vg": "British Virgin Islands",
    "vn": "Vietnam",
    "vu": "Vanuatu",
    "wf": "Wallis and Futuna",
    "ws": "Samoa",
    "xk": "Kosovo",
    "ye": "Yemen",
    "yt": "Mayotte",
    "za": "South Africa",
    "zm": "Zambia",
    "zw": "Zimbabwe"
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
    return normalize_db_entries(items)


def resolve_targets(db_names, entries):
    if not db_names:
        return entries

    lookup = {entry["main"]: entry for entry in entries}
    targets = []
    for name in db_names:
        if name in lookup:
            targets.append(lookup[name])
        else:
            targets.append({"main": name, "results": f"{name}-results", "countries": []})
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


def compute_geographic_distribution(client, main_db, results_db, limit=None, verify=False, scope="all"):
    source_collection = client[main_db]["certificates"]
    target_collection_name = "geographic-distribution-1"
    target_collection = client[results_db][target_collection_name]

    country_groups = {}
    scope_filter = get_scope_filter(scope)

    if scope_filter:
        try:
            scoped_count = source_collection.count_documents(scope_filter, hint="idx_scope")
        except Exception:
            scoped_count = source_collection.count_documents(scope_filter)
        if limit:
            scoped_count = min(scoped_count, limit)
        country = TLD_TO_COUNTRY.get(scope, scope.upper())
        country_groups[country] = {"count": scoped_count}
        processed_count = scoped_count
    else:
        query = {"domain": {"$exists": True, "$nin": [None, ""]}}
        projection = {"_id": 1, "domain": 1}

        try:
            cursor = source_collection.find(merge_scope_query(query, scope), projection, hint="idx_domain")
        except Exception:
            cursor = source_collection.find(merge_scope_query(query, scope), projection)

        if limit:
            cursor = cursor.limit(limit)

        processed_count = 0

        for doc in cursor:
            # Legacy shape stored sample certificate IDs in each country document.
            # New shape intentionally omits them:
            # cert_id = doc["_id"]
            domain = doc.get("domain", "")
            country = get_tld_country(domain)

            if country not in country_groups:
                country_groups[country] = {
                    "count": 0,
                    # "certificate_ids": []
                }

            group = country_groups[country]
            group["count"] += 1
            # if len(group["certificate_ids"]) < 1000:
            #     group["certificate_ids"].append(cert_id)

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

    countries = []
    now = datetime.now(timezone.utc)
    for i, (country, group) in enumerate(sorted_countries):
        count = group["count"]
        percentage = round((count / total_certificates) * 100, 3) if total_certificates else 0
        # certificate_ids = group["certificate_ids"]
        countries.append({
            "count": count,
            "name": country,
            "percentage": percentage,
            "color": colors[i % len(colors)],
            "rank": i + 1,
            # "certificate_ids": certificate_ids,
            # "has_more": count > len(certificate_ids),
            "computed_at": now,
            "source_database": main_db,
            "source_collection": "certificates",
        })

    geo_doc = {
        "_id": scoped_doc_id("geographic_distribution", scope),
        "scope": scope,
        "countries": countries,
        "computed_at": now,
        "last_computed": now,
        "computation_duration_seconds": 0,
        "total_countries": len(countries),
        "total_certificates": total_certificates,
        "source_database": main_db,
        "source_collection": "certificates",
        "target_database": results_db,
        "target_collection": target_collection_name,
        "testing_mode": bool(limit),
        "documents_processed": processed_count,
    }

    target_collection.replace_one({"scope": scope}, geo_doc, upsert=True)

    create_index_if_missing(target_collection, "scope", name="idx_geo_distribution_scope", background=True)
    create_index_if_missing(target_collection, "computed_at", name="idx_geo_distribution_computed_at", background=True)
    create_index_if_missing(target_collection, "countries.rank", name="idx_geo_distribution_country_rank", background=True)
    create_index_if_missing(target_collection, "countries.count", name="idx_geo_distribution_country_count", background=True)
    create_index_if_missing(target_collection, "countries.name", name="idx_geo_distribution_country_name", background=True)

    if verify:
        stored_doc = target_collection.find_one({"scope": scope})
        if not stored_doc:
            raise RuntimeError("Verification failed: geographic distribution missing")
        if len(stored_doc.get("countries", [])) != len(countries):
            raise RuntimeError("Verification failed: countries count mismatch")
        if sum(doc["count"] for doc in countries) != total_certificates:
            raise RuntimeError("Verification failed: total count mismatch")
        if stored_doc.get("total_certificates") != total_certificates:
            raise RuntimeError("Verification failed: stored total mismatch")


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
        for scope, _country in get_scopes_for_entry(target):
            compute_geographic_distribution(
                client,
                target["main"],
                target["results"],
                limit=args.limit,
                verify=args.verify,
                scope=scope,
            )
    client.close()


if __name__ == "__main__":
    main()
