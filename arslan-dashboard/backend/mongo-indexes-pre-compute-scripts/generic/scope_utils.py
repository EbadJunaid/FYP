"""Shared helpers for generic pre-compute scripts."""


TLD_TO_COUNTRY = {
    "us": "United States", "ca": "Canada", "mx": "Mexico",
    "uk": "United Kingdom", "co.uk": "United Kingdom", "gb": "United Kingdom",
    "fr": "France", "de": "Germany", "nl": "Netherlands", "it": "Italy",
    "es": "Spain", "pt": "Portugal", "ch": "Switzerland", "at": "Austria",
    "se": "Sweden", "no": "Norway", "dk": "Denmark", "fi": "Finland",
    "ru": "Russia", "ua": "Ukraine", "tr": "Turkey", "sa": "Saudi Arabia",
    "ae": "United Arab Emirates", "in": "India", "pk": "Pakistan",
    "bd": "Bangladesh", "lk": "Sri Lanka", "np": "Nepal", "cn": "China",
    "jp": "Japan", "kr": "South Korea", "sg": "Singapore", "my": "Malaysia",
    "id": "Indonesia", "ph": "Philippines", "au": "Australia", "nz": "New Zealand",
    "br": "Brazil", "ar": "Argentina", "co": "Colombia", "cl": "Chile",
    "za": "South Africa", "ng": "Nigeria", "eg": "Egypt", "ke": "Kenya",
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
