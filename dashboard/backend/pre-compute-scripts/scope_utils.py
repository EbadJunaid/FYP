"""Shared helpers for generic pre-compute scripts."""

from pymongo.errors import OperationFailure


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
COUNTRY_TO_TLD = {name.lower(): tld for tld, name in TLD_TO_COUNTRY.items()}


def normalize_db_entries(items):
    entries = []
    for item in items:
        if isinstance(item, str):
            entries.append({"main": item, "results": f"{item}-results", "countries": []})
        elif isinstance(item, dict):
            main_db = item.get("main") or item.get("db") or item.get("name")
            results_db = item.get("results") or (f"{main_db}-results" if main_db else None)
            if main_db:
                countries = item.get("countries") or []
                if isinstance(countries, str):
                    countries = [countries]
                entry = {"main": main_db, "results": results_db, "countries": countries}
                if item.get("id"):
                    entry["id"] = str(item["id"])
                entries.append(entry)
        else:
            raise ValueError("Unsupported database entry in list")
    return entries


def country_name_to_tld(country):
    if not country:
        return None
    value = str(country).strip().lower().lstrip(".")
    if not value:
        return None
    if value in TLD_TO_COUNTRY:
        return value
    return COUNTRY_TO_TLD.get(value)


def get_scope_filter(scope):
    scope = (scope or "all").strip().lower()
    if scope in ("", "all", "global"):
        return {}
    return {"scope": scope}


def scoped_doc_id(base_id, scope):
    scope = (scope or "all").strip().lower() or "all"
    return f"{base_id}:{scope}"


def get_scopes_for_entry(entry):
    scopes = [("all", None)]
    seen = {"all"}
    for country in entry.get("countries", []):
        tld = country_name_to_tld(country)
        if not tld or tld in seen:
            continue
        scopes.append((tld, country))
        seen.add(tld)
    return scopes


def add_scope_match(pipeline, scope):
    scope_filter = get_scope_filter(scope)
    if not scope_filter:
        return list(pipeline)
    return [{"$match": scope_filter}] + list(pipeline)


def merge_scope_query(query, scope):
    query = query or {}
    scope_filter = get_scope_filter(scope)
    if not scope_filter:
        return query
    if not query:
        return scope_filter
    return {"$and": [query, scope_filter]}


def normalize_index_keys(keys):
    if isinstance(keys, str):
        return [(keys, 1)]
    return [(field, direction) for field, direction in keys]


def create_index_if_missing(collection, keys, name, **options):
    normalized_keys = normalize_index_keys(keys)
    requested_partial = options.get("partialFilterExpression")
    for existing in collection.list_indexes():
        existing_keys = list(existing.get("key", {}).items())
        existing_partial = existing.get("partialFilterExpression")
        if existing.get("name") == name:
            if existing_keys != normalized_keys:
                print(
                    f"  Reusing existing index {name} on {collection.full_name}; "
                    f"existing keys {existing_keys}, requested keys {normalized_keys}"
                )
            elif existing_partial != requested_partial:
                print(
                    f"  Reusing existing index {name} on {collection.full_name}; "
                    "partial filter differs from requested options"
                )
            return existing.get("name")
        if existing_keys == normalized_keys:
            if existing_partial != requested_partial:
                continue
            if existing.get("name") != name:
                print(
                    f"  Reusing existing index {existing.get('name')} for {name} "
                    f"on {collection.full_name}"
                )
            return existing.get("name")

    try:
        return collection.create_index(normalized_keys, name=name, **options)
    except OperationFailure as exc:
        if getattr(exc, "code", None) in (85, 86):
            print(f"  Index conflict for {name} on {collection.full_name}; equivalent index already exists")
            return None
        raise
