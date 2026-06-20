"""Shared helpers for generic pre-compute scripts."""

from pymongo.errors import OperationFailure


TLD_TO_COUNTRY = {
    "ac": "Ascension Island", "ad": "Andorra", "ae": "United Arab Emirates",
    "af": "Afghanistan", "ag": "Antigua and Barbuda", "ai": "Anguilla",
    "al": "Albania", "am": "Armenia", "ao": "Angola", "ar": "Argentina",
    "as": "American Samoa", "at": "Austria", "aw": "Aruba", "ax": "Aland Islands",
    "az": "Azerbaijan", "ba": "Bosnia and Herzegovina", "bb": "Barbados",
    "be": "Belgium", "bf": "Burkina Faso", "bg": "Bulgaria", "bh": "Bahrain",
    "bi": "Burundi", "bj": "Benin", "bm": "Bermuda", "bo": "Bolivia",
    "br": "Brazil", "bs": "Bahamas", "bt": "Bhutan", "bw": "Botswana",
    "by": "Belarus", "bz": "Belize", "ca": "Canada", "cc": "Cocos Islands",
    "cd": "Democratic Republic of the Congo", "cf": "Central African Republic",
    "cg": "Republic of the Congo", "ch": "Switzerland", "ci": "Cote d'Ivoire",
    "cl": "Chile", "cm": "Cameroon", "cn": "China", "co": "Colombia",
    "cr": "Costa Rica", "cu": "Cuba", "cv": "Cape Verde", "cw": "Curacao",
    "cx": "Christmas Island", "cy": "Cyprus", "cz": "Czech Republic",
    "de": "Germany", "dj": "Djibouti", "dk": "Denmark", "do": "Dominican Republic",
    "dz": "Algeria", "ec": "Ecuador", "ee": "Estonia", "eg": "Egypt",
    "es": "Spain", "et": "Ethiopia", "eu": "European Union", "fi": "Finland",
    "fm": "Micronesia", "fo": "Faroe Islands", "fr": "France", "ga": "Gabon",
    "gd": "Grenada", "ge": "Georgia", "gf": "French Guiana", "gg": "Guernsey",
    "gi": "Gibraltar", "gl": "Greenland", "gm": "Gambia", "gp": "Guadeloupe",
    "gq": "Equatorial Guinea", "gr": "Greece",
    "gs": "South Georgia and the South Sandwich Islands", "gt": "Guatemala",
    "gy": "Guyana", "hk": "Hong Kong", "hm": "Heard Island and McDonald Islands",
    "hn": "Honduras", "hr": "Croatia", "ht": "Haiti", "hu": "Hungary",
    "id": "Indonesia", "ie": "Ireland", "im": "Isle of Man", "in": "India",
    "io": "British Indian Ocean Territory", "iq": "Iraq", "ir": "Iran",
    "is": "Iceland", "it": "Italy", "je": "Jersey", "jo": "Jordan",
    "jp": "Japan", "ke": "Kenya", "kg": "Kyrgyzstan", "kr": "South Korea",
    "ky": "Cayman Islands", "kz": "Kazakhstan", "la": "Laos", "lc": "Saint Lucia",
    "li": "Liechtenstein", "lk": "Sri Lanka", "lt": "Lithuania",
    "lu": "Luxembourg", "lv": "Latvia", "ly": "Libya", "ma": "Morocco",
    "mc": "Monaco", "md": "Moldova", "me": "Montenegro", "mg": "Madagascar",
    "mk": "North Macedonia", "ml": "Mali", "mn": "Mongolia", "mo": "Macau",
    "mp": "Northern Mariana Islands", "mr": "Mauritania", "ms": "Montserrat",
    "mt": "Malta", "mu": "Mauritius", "mv": "Maldives", "mw": "Malawi",
    "mx": "Mexico", "my": "Malaysia", "mz": "Mozambique", "nc": "New Caledonia",
    "ne": "Niger", "ng": "Nigeria", "nl": "Netherlands", "no": "Norway",
    "nu": "Niue", "nz": "New Zealand", "om": "Oman", "pa": "Panama",
    "pe": "Peru", "pf": "French Polynesia", "ph": "Philippines", "pk": "Pakistan",
    "pl": "Poland", "pm": "Saint Pierre and Miquelon", "pn": "Pitcairn Islands",
    "pr": "Puerto Rico", "ps": "Palestine", "pt": "Portugal", "pw": "Palau",
    "qa": "Qatar", "re": "Reunion", "ro": "Romania", "rs": "Serbia",
    "rw": "Rwanda", "sa": "Saudi Arabia", "sb": "Solomon Islands",
    "sc": "Seychelles", "sd": "Sudan", "se": "Sweden", "sg": "Singapore",
    "sh": "Saint Helena", "si": "Slovenia", "sk": "Slovakia", "sl": "Sierra Leone",
    "sm": "San Marino", "sn": "Senegal", "so": "Somalia", "sr": "Suriname",
    "st": "Sao Tome and Principe", "sx": "Sint Maarten", "sy": "Syria",
    "tc": "Turks and Caicos Islands", "td": "Chad", "tf": "French Southern Territories",
    "tg": "Togo", "tj": "Tajikistan", "tk": "Tokelau", "tl": "Timor-Leste",
    "tm": "Turkmenistan", "tn": "Tunisia", "to": "Tonga",
    "tt": "Trinidad and Tobago", "tv": "Tuvalu", "tw": "Taiwan", "ua": "Ukraine",
    "ug": "Uganda", "uk": "United Kingdom", "us": "United States", "uy": "Uruguay",
    "uz": "Uzbekistan", "vc": "Saint Vincent and the Grenadines",
    "vg": "British Virgin Islands", "vn": "Vietnam", "vu": "Vanuatu",
    "wf": "Wallis and Futuna", "ws": "Samoa", "yt": "Mayotte",
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
