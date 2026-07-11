
from datetime import datetime, timezone, timedelta
import re
from typing import List, Dict, Any, Optional
from bson import ObjectId

from ..db import db, MongoDBClient
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

class SharedModels:
    collection = db['certificates']

    @classmethod
    def get_ca_distribution(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        """
        Get Certificate Authority distribution.
        
        OPTIMIZATION STRATEGY:
        The current implementation suffers from 'Fetch Penalty' because the query projects
        '$arrayElemAt': ['$parsed.issuer.organization', 0], forcing MongoDB to fetch the 
        full document to get the array element, even though 'idx_issuer_org' exists.
        
        FIX:
        1. NO FILTER (Fast Path):
           - Use 'idx_issuer_org' which indexes the ARRAY 'parsed.issuer.organization'.
           - In MongoDB, indexing an array indexes its ELEMENTS.
           - We can group by 'parsed.issuer.organization' directly. This will count 
             every occurrence. Since the schema implies one org per issuer usually, 
             or we want to count distinct issuers found, this works directly on index.
           - This becomes a Covered Query (PROJECTION-FREE).
           
        2. WITH FILTER (Optimized Path):
           - Remove $project stage at the start to allow index usage for filtering.
           - Group directly.
        """
        
        # Color palette
        colors = [
            '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', 
            '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16', 
            '#f97316', '#a855f7', '#22c55e', '#0ea5e9', '#d946ef', 
            '#eab308', '#6b7280'
        ]

        # ---------------------------------------------------------
        # PATH 1: NO FILTER (Zero Fetch / Index Only)
        # ---------------------------------------------------------
        if not base_filter:
            total = cls.collection.estimated_document_count()
            if total == 0:
                return []

            # We group directly on the indexed field 'parsed.issuer.organization'.
            # Note: If 'organization' is an array ["Google Trust Services"], grouping by it
            # might group by the ARRAY itself or unwind depending on usage. 
            # Ideally, for a covered query on an array field, we want to unwind or exact match.
            # However, for 'get_ca_distribution', we usually want the string name.
            # 
            # FASTEST APPROACH: Group by the field directly.
            # Since 'idx_issuer_org' is on 'parsed.issuer.organization', we MUST NOT 
            # use $arrayElemAt if we want a covered query. We group by the field itself.
            # MongoDB's index covers the array values.
            
            pipeline = [
                # 1. Unwind preserves index use if it's the first stage
                {'$unwind': '$parsed.issuer.organization'},
                # 2. Group by the unwound string (indexed)
                {'$group': {
                    '_id': '$parsed.issuer.organization',
                    'count': {'$sum': 1}
                }},
                {'$sort': {'count': -1}},
                {'$limit': limit}
            ]
            
            # This runs purely on the B-Tree index (IndexScan -> Group)
            results = list(cls.collection.aggregate(pipeline, hint='idx_issuer_org'))

        # ---------------------------------------------------------
        # PATH 2: WITH FILTER
        # ---------------------------------------------------------
        else:
            total = cls.collection.count_documents(base_filter)
            if total == 0:
                return []
                
            pipeline = [
                {'$match': base_filter},
                # We still prefer unwind -> group over $project -> $arrayElemAt
                # because it's friendlier to indexes if base_filter uses the same index
                {'$unwind': '$parsed.issuer.organization'},
                {'$group': {
                    '_id': '$parsed.issuer.organization',
                    'count': {'$sum': 1}
                }},
                {'$sort': {'count': -1}},
                {'$limit': limit}
            ]
            
            results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))

        # ---------------------------------------------------------
        # Formatting (Shared)
        # ---------------------------------------------------------
        if not results:
            return []
            
        max_count = results[0]['count']
        
        ca_list = [
            {
                'id': f'ca-{i}',
                'name': r['_id'],
                'count': r['count'],
                'maxCount': max_count,
                'percentage': round((r['count'] / total) * 100, 1),
                'color': colors[i % len(colors)]
            }
            for i, r in enumerate(results)
        ]
        
        # Calculate "Others"
        top_ca_count = sum(r['count'] for r in results)
        others_count = max(0, total - top_ca_count)
        
        if others_count > 0:
            ca_list.append({
                'id': 'ca-others',
                'name': 'Others',
                'count': others_count,
                'maxCount': max_count,
                'percentage': round((others_count / total) * 100, 1),
                'color': '#6b7280',
                'isOthers': True
            })
            
        return ca_list
    
    # @classmethod
    # def get_ca_distribution_fast(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
    #     """
    #     ⚡ FAST VERSION: Get Certificate Authority distribution from pre-computed collection
        
    #     This method reads from a materialized view that's updated periodically (every 6-12 hours)
    #     by the compute_ca_analytics.py script.
        
    #     Performance: ~0.01s (reads from pre-computed results)
        
    #     Limitation: 
    #     - Does NOT support base_filter (global filters) - returns full pre-computed data
    #     - If you need filtered results, falls back to get_ca_distribution() (slow)
        
    #     Args:
    #         limit: Number of top CAs to return (default: 10)
    #         base_filter: If provided, falls back to slow method (not supported)
            
    #     Returns:
    #         List of CA distribution data in API-ready format
    #     """
        
    #     # If filter is provided, fall back to slow method
    #     if base_filter:
    #         print("[WARNING] CA Analytics: base_filter provided, falling back to slow aggregation")
    #         return cls.get_ca_distribution(limit=limit, base_filter=base_filter)
        
    #     try:
    #         # Read from pre-computed collection
    #         ca_analytics_collection = MongoDBClient.get_results_db()['ca-analytics']
            
    #         # Get metadata to check freshness
    #         metadata = ca_analytics_collection.find_one({'_id': 'metadata'})
    #         if not metadata:
    #             print("[WARNING] CA Analytics: No pre-computed data found, falling back to slow method")
    #             return cls.get_ca_distribution(limit=limit, base_filter=None)
            
    #         # Check if data is stale (older than 24 hours)
    #         last_computed = metadata.get('last_computed')
    #         if last_computed:
    #             # Ensure both datetimes are timezone-aware
    #             now_utc = datetime.now(timezone.utc)
    #             if isinstance(last_computed, datetime):
    #                 # If last_computed is naive, make it aware (assume UTC)
    #                 if last_computed.tzinfo is None:
    #                     last_computed = last_computed.replace(tzinfo=timezone.utc)
                    
    #                 age_hours = (now_utc - last_computed).total_seconds() / 3600
    #                 if age_hours > 24:
    #                     print(f"[WARNING] CA Analytics: Pre-computed data is {age_hours:.1f} hours old")
            
    #         # Fetch top N CAs
    #         ca_records = list(
    #             ca_analytics_collection
    #             .find({'_id': {'$ne': 'metadata'}})  # Exclude metadata document
    #             .sort('rank', 1)  # Sort by rank ascending
    #             .limit(limit)
    #         )
            
    #         if not ca_records:
    #             print("[WARNING] CA Analytics: No CA records found, falling back to slow method")
    #             return cls.get_ca_distribution(limit=limit, base_filter=None)
            
    #         # Get total for "Others" calculation
    #         total_certificates = metadata.get('total_certificates', 0)
    #         top_ca_count = sum(record['count'] for record in ca_records)
    #         others_count = max(0, total_certificates - top_ca_count)
            
    #         # Transform to API format
    #         ca_list = [
    #             {
    #                 'id': record['ca_id'],
    #                 'name': record['name'],
    #                 'count': record['count'],
    #                 'maxCount': record['max_count'],
    #                 'percentage': record['percentage'],
    #                 'color': record['color']
    #             }
    #             for record in ca_records
    #         ]
            
    #         # Add "Others" if needed
    #         if others_count > 0 and ca_records:
    #             max_count = ca_records[0]['max_count']
    #             ca_list.append({
    #                 'id': 'ca-others',
    #                 'name': 'Others',
    #                 'count': others_count,
    #                 'maxCount': max_count,
    #                 'percentage': round((others_count / total_certificates) * 100, 1),
    #                 'color': '#6b7280',
    #                 'isOthers': True
    #             })
            
    #         return ca_list
            
    #     except Exception as e:
    #         print(f"[ERROR] CA Analytics Fast: {str(e)}, falling back to slow method")
    #         return cls.get_ca_distribution(limit=limit, base_filter=None)
 
    @classmethod
    def get_validity_trends(cls, months_before: int = 4, months_after: int = 4, granularity: str = 'monthly') -> List[Dict]:
        """Get certificate expiration trends by calendar period
        
        Args:
            months_before: Number of months to look back
            months_after: Number of months to look ahead
            granularity: 'monthly' or 'weekly' - determines the grouping period
        
        Returns:
            List of dicts with period, expirations count, and period metadata
        """
        from calendar import monthrange
        from dateutil.relativedelta import relativedelta
        
        trends = []
        now = datetime.now(timezone.utc)
        scoped_trends = MongoDBClient.get_current_scope() not in ('', 'all', 'global')
        validity_hint = 'idx_scope_validity_end' if scoped_trends else 'idx_validity_end'
        
        if granularity == 'weekly':
            # Weekly granularity: show last N weeks and next M weeks
            weeks_before = months_before * 4  # ~4 weeks per month
            weeks_after = months_after * 4
            
            for i in range(-weeks_before, weeks_after + 1):
                # Calculate week start (Monday) and end (Sunday)
                week_start = now + timedelta(weeks=i)
                # Adjust to Monday of that week
                week_start = week_start - timedelta(days=week_start.weekday())
                week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
                
                start_str = week_start.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_str = week_end.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                # Count certificates expiring in this week
                count = cls.collection.count_documents({
                    'parsed.validity.end': {
                        '$gte': start_str,
                        '$lte': end_str
                    }
                }, hint=validity_hint)
                
                # Week label: "Jan 6-12"
                week_label = f"{week_start.strftime('%b %d')}-{week_end.strftime('%d')}"
                is_current = (week_start <= now <= week_end)
                
                trends.append({
                    'month': week_label,  # Keep key as 'month' for frontend compatibility
                    'expirations': count,
                    'year': week_start.year,
                    'monthNum': week_start.month,
                    'weekNum': week_start.isocalendar()[1],
                    'weekStart': start_str,
                    'weekEnd': end_str,
                    'isCurrent': is_current,
                    'granularity': 'weekly'
                })
        else:
            # Monthly granularity (default)
            start_offset = -(months_before)
            end_offset = months_after
            
            for i in range(start_offset, end_offset + 1):
                # Calculate the target month using relativedelta
                target_date = now + relativedelta(months=i)
                year = target_date.year
                month = target_date.month
                
                # Get first day and last day of the month
                _, days_in_month = monthrange(year, month)
                month_start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
                month_end = datetime(year, month, days_in_month, 23, 59, 59, tzinfo=timezone.utc)
                
                start_str = month_start.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_str = month_end.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                # Count certificates expiring in this month
                count = cls.collection.count_documents({
                    'parsed.validity.end': {
                        '$gte': start_str,
                        '$lte': end_str
                    }
                }, hint=validity_hint)
                
                # Include year with month name for clarity (e.g., "Jan 2026")
                month_label = month_start.strftime('%b %Y')
                is_current = (year == now.year and month == now.month)
                
                trends.append({
                    'month': month_label,
                    'expirations': count,
                    'year': year,
                    'monthNum': month,
                    'isCurrent': is_current,
                    'granularity': 'monthly'
                })
        
        return trends
   
    @classmethod
    def get_dashboard_metrics(cls) -> Dict:
        # print("Calculating dashboard metrics...")
        """
        # ULTRA-OPTIMIZED: Use estimated count + separate indexed queries.
        # Each query leverages indexes independently (faster than $facet).
        # """
        import time
        start_time = time.time()
        
        now = cls.get_current_time_iso()
        now_plus_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        scoped_metrics = MongoDBClient.get_current_scope() not in ('', 'all', 'global')
        validity_hint = 'idx_scope_validity_end' if scoped_metrics else 'idx_validity_end'
        zlint_hint = 'idx_scope_zlint_errors' if scoped_metrics else 'idx_zlint_errors'
        
        print(f"[METRICS] Starting ultra-optimized queries at {cls.get_current_time_iso()}")
        
        # Query 1: Total count - USE ESTIMATED (instant!)
        print("[METRICS] Query 1: Counting total (estimated)...")
        t1 = time.time()
        total = cls.collection.estimated_document_count()
        print(f"[METRICS] Total count: {total} ({time.time()-t1:.3f}s)")
        
        if total == 0:
            return {
                'globalHealth': {
                    'score': 0,
                    'maxScore': 100,
                    'status': 'CRITICAL',
                    'lastUpdated': datetime.now(timezone.utc).strftime('%H:%M')
                },
                'activeCertificates': {'count': 0, 'total': 0},
                'expiringSoon': {'count': 0, 'daysThreshold': 30, 'actionNeeded': False},
                'criticalVulnerabilities': {'count': 0, 'new': 0},
                'expiredCertificates': {'count': 0, 'total': 0}

            }
        
        # Query 2: Expired count - INDEXED query on validity.end
        print("[METRICS] Query 2: Counting expired (indexed)...")
        t2 = time.time()
        expired_count = cls.collection.count_documents(
            {'parsed.validity.end': {'$lt': now}},
            hint=validity_hint
        )
        print(f"[METRICS] Expired count: {expired_count} ({time.time()-t2:.3f}s)")
        
        # Query 3: Expiring soon - INDEXED query on validity.end
        print("[METRICS] Query 3: Counting expiring soon (indexed)...")
        t3 = time.time()
        expiring_count = cls.collection.count_documents(
            {'parsed.validity.end': {'$gte': now, '$lte': now_plus_30}},
            hint=validity_hint
        )
        print(f"[METRICS] Expiring count: {expiring_count} ({time.time()-t3:.3f}s)")
        
        # Query 4: Vulnerabilities - INDEXED query on zlint.errors_present
        print("[METRICS] Query 4: Counting vulnerabilities (indexed)...")
        t4 = time.time()
        critical_vulns = cls.collection.count_documents(
            {'zlint.errors_present': True},
            hint=zlint_hint
        )
        print(f"[METRICS] Vulnerability count: {critical_vulns} ({time.time()-t4:.3f}s)")
        
        # Calculate derived values
        active_count = total - expired_count
        
        # Calculate health score
        active_percentage = (active_count / total) * 100 if total > 0 else 0
        vuln_penalty = min(20, (critical_vulns / total) * 100) if total > 0 else 0
        health_score = int(min(100, max(0, active_percentage - vuln_penalty)))
        
        # Determine status
        if health_score >= 80:
            health_status = 'SECURE'
        elif health_score >= 50:
            health_status = 'AT_RISK'
        else:
            health_status = 'CRITICAL'
        
        elapsed = time.time() - start_time
        print(f"[METRICS] ✅ All queries completed in {elapsed:.2f} seconds")
        print(f"[METRICS] Results - Total: {total}, Expired: {expired_count}, Expiring: {expiring_count}, Vulns: {critical_vulns}")
        
        return {
            'globalHealth': {
                'score': health_score,
                'maxScore': 100,    
                'status': health_status,
                'lastUpdated': datetime.now(timezone.utc).strftime('%H:%M')
            },
            'activeCertificates': {
                'count': active_count,
                'total': total
            },
            'expiringSoon': {
                'count': expiring_count,
                'daysThreshold': 30,
                'actionNeeded': expiring_count > 100
            },
            'criticalVulnerabilities': {
                'count': critical_vulns,
                'new': max(0, critical_vulns // 10) #needs attention as this will alwasys take modulus and return the value as new vulnerablities 
            },
            'expiredCertificates': {
                'count': expired_count
            }
        }
    
    @classmethod
    def get_geographic_distribution_fast(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        """
        ⚡ FAST VERSION: Get Geographic distribution from pre-computed collection
        
        This method reads from a materialized view that's updated periodically (every 6-12 hours)
        by the compute_geographic_distribution.py script.
        
        Performance: ~0.01s (reads from pre-computed results)
        
        Limitation: 
        - Does NOT support base_filter (global filters) - returns full pre-computed data
        - If you need filtered results, falls back to get_geographic_distribution() (slow)
        
        Args:
            limit: Number of top countries to return (default: 10)
            base_filter: If provided, falls back to slow method (not supported)
            
        Returns:
            List of geographic distribution data in API-ready format
        """
        print("I am in fast method bhai sahab")
        # If filter is provided, fall back to slow method
        if base_filter:
            print("[WARNING] Geographic Distribution: base_filter provided, falling back to slow aggregation")
            return cls.get_geographic_distribution(limit=limit, base_filter=base_filter)
        
        try:
            # Read from pre-computed collection
            geo_collection = MongoDBClient.get_results_db()['geographic-distribution']
            scope_filter = MongoDBClient.get_precomputed_scope_filter()
            scoped_doc = geo_collection.find_one(scope_filter)
            if scoped_doc and scoped_doc.get('countries') is not None:
                countries = [
                    item for item in scoped_doc.get('countries', [])
                    if item.get('name') and item.get('name') != 'Others'
                ]
                countries = sorted(countries, key=lambda item: item.get('rank', 999999))[:limit]
                if not countries:
                    print("[WARNING] Geographic Distribution: Empty scoped countries array, falling back to slow method")
                    return cls.get_geographic_distribution(limit=limit, base_filter=None)

                last_computed = scoped_doc.get('last_computed') or scoped_doc.get('computed_at')
                if last_computed and isinstance(last_computed, datetime):
                    now_utc = datetime.now(timezone.utc)
                    if last_computed.tzinfo is None:
                        last_computed = last_computed.replace(tzinfo=timezone.utc)
                    age_hours = (now_utc - last_computed).total_seconds() / 3600
                    if age_hours > 24:
                        print(f"[WARNING] Geographic Distribution: Pre-computed data is {age_hours:.1f} hours old")

                total_count = sum(record.get('count', 0) for record in countries)
                max_count = countries[0].get('count', 1) if countries else 1
                return [
                    {
                        'id': record.get('geo_id', f"geo-{index}"),
                        'country': record.get('name'),
                        'count': record.get('count', 0),
                        'maxCount': max_count,
                        'percentage': round((record.get('count', 0) / total_count * 100), 2) if total_count else 0,
                        'color': record.get('color', '#6b7280'),
                        'certificate_ids': []
                    }
                    for index, record in enumerate(countries)
                ]
            
            # Get metadata to check freshness
            metadata = geo_collection.find_one({'$and': [{'_id': 'metadata'}, scope_filter]})
            if not metadata and MongoDBClient.get_precomputed_scope() == 'all':
                metadata = geo_collection.find_one({'_id': 'metadata'})
            if not metadata:
                print("[WARNING] Geographic Distribution: No pre-computed data found, falling back to slow method")
                return cls.get_geographic_distribution(limit=limit, base_filter=None)
            
            # Check if data is stale (older than 24 hours)
            last_computed = metadata.get('last_computed')
            if last_computed:
                # Ensure both datetimes are timezone-aware
                now_utc = datetime.now(timezone.utc)
                if isinstance(last_computed, datetime):
                    # If last_computed is naive, make it aware (assume UTC)
                    if last_computed.tzinfo is None:
                        last_computed = last_computed.replace(tzinfo=timezone.utc)
                    
                    age_hours = (now_utc - last_computed).total_seconds() / 3600
                    if age_hours > 24:
                        print(f"[WARNING] Geographic Distribution: Pre-computed data is {age_hours:.1f} hours old")
            
            # Fetch top N countries (excluding 'Others' category - it's for internal use only)
            geo_records = list(
                geo_collection
                .find({'$and': [
                    {'_id': {'$nin': ['metadata', 'Others']}},
                    {'country': {'$ne': 'Others'}},
                    scope_filter,
                ]})
                .sort('rank', 1)  # Sort by rank ascending
                .limit(limit)
            )
            
            if not geo_records:
                print("[WARNING] Geographic Distribution: No records found, falling back to slow method")
                return cls.get_geographic_distribution(limit=limit, base_filter=None)
            
            # Calculate total count (excluding Others) for percentage recalculation
            total_count = sum(record['count'] for record in geo_records)
            max_count = geo_records[0]['count'] if geo_records else 1
            
            # Transform to API format with recalculated percentages and certificate_ids
            geo_list = []
            for record in geo_records:
                # Recalculate percentage relative to displayed countries only
                percentage = (record['count'] / total_count * 100) if total_count > 0 else 0
                
                # Convert ObjectId to string for JSON serialization
                cert_ids = record.get('certificate_ids', [])
                cert_ids_str = [str(oid) for oid in cert_ids] if cert_ids else []
                
                geo_list.append({
                    'id': record.get('geo_id', str(record['_id'])),
                    'country': record['country'],
                    'count': record['count'],
                    'maxCount': max_count,
                    'percentage': round(percentage, 2),
                    'color': record['color'],
                    'certificate_ids': cert_ids_str  # Convert ObjectIds to strings
                })
            
            return geo_list
            
        except Exception as e:
            print(f"[ERROR] Geographic Distribution Fast: {str(e)}, falling back to slow method")
            return cls.get_geographic_distribution(limit=limit, base_filter=None)
        
   
    @classmethod
    def get_geographic_distribution(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        """Get certificate distribution by country (from domain TLD)
        Optimized: Compute TLD directly in MongoDB aggregation
        
        Args:
            base_filter: Global filter query - applied before aggregation
        """
        
        # Get total certificates count (with or without filter)
        if base_filter:
            total = cls.collection.count_documents(base_filter)
        else:
            total = cls.collection.count_documents({})
        
        if total == 0:
            return []
        
        # Build aggregation pipeline
        pipeline = []
        
        # Apply base filter first if provided
        if base_filter:
            pipeline.append({'$match': base_filter})
        
        # Add domain extraction and grouping stages
        pipeline.extend([
            {'$match': {'domain': {'$exists': True, '$ne': None, '$ne': ''}}},
            {'$project': {
                'domain_parts': {'$split': ['$domain', '.']},
            }},
            {'$project': {
                'tld': {'$arrayElemAt': ['$domain_parts', -1]}
            }},
            {'$match': {'tld': {'$exists': True, '$ne': None}}},
            {'$group': {
                '_id': '$tld',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ])
        
        results = list(cls.collection.aggregate(pipeline))
        
        # Map TLDs to countries (small dataset, fast in Python)
        country_counts = {}
        for r in results:
            tld = r['_id'].lower() if r['_id'] else 'unknown'
            country = cls.get_tld_country('example.' + tld)  # Use helper with dummy domain
            if country != 'Unknown':
                country_counts[country] = country_counts.get(country, 0) + r['count']
        
        # Sort and limit
        sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        colors = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#6b7280']
        
        max_count = sorted_countries[0][1] if sorted_countries else 1
        
        return [
            {
                'id': f'geo-{i}',
                'country': country,
                'count': count,
                'maxCount': max_count,
                'percentage': round((count / total) * 100, 1),
                'color': colors[i % len(colors)]
            }
            for i, (country, count) in enumerate(sorted_countries)
        ]



    @staticmethod
    def get_current_time_iso() -> str:
        """Get current time in ISO format for MongoDB queries"""
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    @staticmethod
    def get_tld_country(domain: str) -> str:
        """Derive country from domain TLD"""
        if not domain:
            return 'Unknown'
        parts = domain.lower().split('.')
        if len(parts) >= 2:
            # Check for two-part TLDs first (e.g., co.uk)
            two_part_tld = '.'.join(parts[-2:])
            if two_part_tld in TLD_TO_COUNTRY:
                return TLD_TO_COUNTRY[two_part_tld]
            # Check single TLD
            tld = parts[-1]
            return TLD_TO_COUNTRY.get(tld, 'Unknown')
        return 'Unknown'

    @staticmethod
    def country_name_to_tld(country: str) -> Optional[str]:
        """Convert a display country name like 'Pakistan' to its stored scope TLD."""
        if not country:
            return None

        normalized = country.strip().lower()
        direct_tld = normalized.lstrip('.')
        if direct_tld in TLD_TO_COUNTRY:
            return direct_tld

        for tld, country_name in TLD_TO_COUNTRY.items():
            if country_name.lower() == normalized:
                return tld
        return direct_tld or None

    # below functions are used by get_all and get_by_id functions to compute status, grade, and vulnerabilities for each certificate record before sending to frontend.

    @staticmethod

    def get_status(validity_end: str) -> str:
        """Determine certificate status based on validity end date"""
        try:
            end_date = datetime.fromisoformat(validity_end.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            days_remaining = (end_date - now).days
            
            if days_remaining < 0:
                return 'EXPIRED'
            elif days_remaining <= 30:
                return 'EXPIRING_SOON'
            else:
                return 'VALID'
        except:
            return 'VALID'
    
    @staticmethod
    def get_grade_from_zlint(zlint_data: Dict) -> str:
        """Calculate grade based on zlint errors/warnings"""
        if not zlint_data or 'lints' not in zlint_data:
            return 'A'
        
        lints = zlint_data.get('lints', {})
        error_count = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'error')
        warn_count = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'warn')
        
        if error_count >= 3:
            return 'F'
        elif error_count >= 2:
            return 'C'
        elif error_count >= 1:
            return 'B'
        elif warn_count >= 3:
            return 'B+'
        elif warn_count >= 1:
            return 'A-'
        else:
            return 'A+'
    
    @staticmethod
    def count_vulnerabilities(zlint_data: Dict) -> Dict[str, int]:
        """Count errors and warnings from zlint data"""
        if not zlint_data or 'lints' not in zlint_data:
            return {'errors': 0, 'warnings': 0}
        
        lints = zlint_data.get('lints', {})
        errors = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'error')
        warnings = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'warn')
        
        return {'errors': errors, 'warnings': warnings}
    
    @staticmethod
    def format_vulnerabilities(zlint_data: Dict) -> str:
        """Format vulnerabilities as display string"""
        counts = SharedModels.count_vulnerabilities(zlint_data)
        if counts['errors'] > 0:
            return f"{counts['errors']} Critical"
        elif counts['warnings'] > 0:
            return f"{counts['warnings']} Warning"
        return "0 Found"
    
    @classmethod
    def build_filter_query(
        cls,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        countries: Optional[List[str]] = None,
        issuers: Optional[List[str]] = None,
        grades: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        validation_levels: Optional[List[str]] = None
    ) -> Dict:
        """
        Build MongoDB $match filter from query params.
        All filters are combined with AND logic.
        
        Date range uses overlap check:
        - Certificate is included if valid at ANY point during the range
        - Query: validFrom <= endDate AND validTo >= startDate
        """
        filters = []
        now = datetime.now(timezone.utc)
        
        # Date range filter - certificates where validity.end is within the range
        # User request: certificates ending within the date range (end_date between filter start and end)
        if start_date and end_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                # Certificate's end date should be >= filter start AND <= filter end
                filters.append({
                    '$and': [
                        {'parsed.validity.end': {'$gte': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}},
                        {'parsed.validity.end': {'$lte': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}}
                    ]
                })
            except (ValueError, AttributeError):
                pass  # Invalid date format, skip filter
        
        # Country filter (derived from TLD)
        if countries and len(countries) > 0:
            # We'll filter on common_name TLD - need to use $where or compute in aggregation
            # For now, we'll skip and handle in aggregation stage
            pass
        
        # Issuer filter - OPTIMIZED to use indexed parsed.issuer_org_primary field
        if issuers and len(issuers) > 0:
            # Use the simpler indexed field for fast lookups
            filters.append({
                'parsed.issuer_organization': {'$in': issuers}
            })
        
        # Grade filter - needs to be computed, handled in specific methods
        # For now, store for reference
        
        # Status filter
        if statuses and len(statuses) > 0:
            status_filters = []
            for status in statuses:
                if status.upper() == 'VALID':
                    # Valid = not expired and not expiring soon (>30 days)
                    thirty_days = now + timedelta(days=30)
                    status_filters.append({
                        'parsed.validity.end': {'$gt': thirty_days.strftime('%Y-%m-%dT%H:%M:%SZ')}
                    })
                elif status.upper() == 'EXPIRED':
                    status_filters.append({
                        'parsed.validity.end': {'$lte': now.strftime('%Y-%m-%dT%H:%M:%SZ')}
                    })
                elif status.upper() == 'EXPIRING_SOON':
                    # Expiring in next 30 days
                    thirty_days = now + timedelta(days=30)
                    status_filters.append({
                        '$and': [
                            {'parsed.validity.end': {'$gt': now.strftime('%Y-%m-%dT%H:%M:%SZ')}},
                            {'parsed.validity.end': {'$lte': thirty_days.strftime('%Y-%m-%dT%H:%M:%SZ')}}
                        ]
                    })
                elif status.upper() == 'WEAK':
                    # Weak encryption - RSA key < 2048
                    status_filters.append({
                        '$and': [
                            {'parsed.subject_key_info.key_algorithm.name': 'RSA'},
                            {'parsed.subject_key_info.rsa_public_key.length': {'$lt': 2048}}
                        ]
                    })
            if status_filters:
                filters.append({'$or': status_filters})
        
        # Validation level filter
        if validation_levels and len(validation_levels) > 0:
            # Prefer direct validation_level field if present in the documents.
            # This is more accurate than heuristics and matches the rest of the model.
            level_filters = []
            for level in validation_levels:
                normalized_level = level.strip().upper()
                if normalized_level in ['EV', 'OV', 'DV']:
                    level_filters.append({'parsed.validation_level': normalized_level})
                elif normalized_level:
                    # Fallback to heuristics for unknown or alternate labels
                    if normalized_level == 'EV':
                        level_filters.append({
                            'parsed.extensions.certificate_policies': {'$exists': True}
                        })
                    elif normalized_level == 'OV':
                        level_filters.append({
                            'parsed.subject.organization': {'$exists': True}
                        })
                    elif normalized_level == 'DV':
                        level_filters.append({
                            'parsed.subject.organization': {'$exists': False}
                        })
            if level_filters:
                filters.append({'$or': level_filters})
        
        # Combine all filters with AND
        if not filters:
            return {}
        elif len(filters) == 1:
            return filters[0]
        else:
            return {'$and': filters}
    
    @staticmethod
    def serialize_certificate(doc: Dict) -> Dict:
        """Serialize a certificate document for API response"""
        parsed = doc.get('parsed', {})
        validity = parsed.get('validity', {})
        subject = parsed.get('subject', {})
        issuer = parsed.get('issuer', {})
        key_info = parsed.get('subject_key_info', {})
        zlint = doc.get('zlint', {})
        extensions = parsed.get('extensions', {})
        
        # Use domain field directly from document, fallback to common_name
        domain = doc.get('domain', '')
        if not domain:
            domain = subject.get('common_name', ['Unknown'])[0] if subject.get('common_name') else 'Unknown'
        
        issuer_org = issuer.get('organization', ['Unknown'])[0] if issuer.get('organization') else 'Unknown'
        
        # Get key algorithm name and length
        algo_name = key_info.get('key_algorithm', {}).get('name', 'Unknown')
        key_length = 0
        if key_info.get('rsa_public_key'):
            key_length = key_info['rsa_public_key'].get('length', 0)
        elif key_info.get('ecdsa_public_key'):
            key_length = key_info['ecdsa_public_key'].get('length', 0)
        
        # Create full encryption type string (e.g., "RSA 2048 SHA-256")
        sig_algo = parsed.get('signature_algorithm', {}).get('name', '')
        if key_length:
            encryption_type = f"{algo_name} {key_length}"
            if sig_algo and 'SHA' in sig_algo.upper():
                encryption_type += f" {sig_algo.split('-')[-1] if '-' in sig_algo else sig_algo}"
        else:
            encryption_type = algo_name
        
        # Get validation level directly from parsed field
        validation_level = parsed.get('validation_level', 'DV')
        
        # Build zlintDetails - only include error/warn lints if present
        zlint_details = {}
        if zlint.get('errors_present', False) or zlint.get('warnings_present', False):
            lints = zlint.get('lints', {})
            for lint_name, lint_data in lints.items():
                if isinstance(lint_data, dict):
                    result = lint_data.get('result', '')
                    if result in ('error', 'warn'):
                        zlint_details[lint_name] = lint_data
        
        # Extract key usage flags
        key_usage = extensions.get('key_usage', {})
        key_usage_dict = {
            'digitalSignature': key_usage.get('digital_signature', False),
            'keyEncipherment': key_usage.get('key_encipherment', False),
            'dataEncipherment': key_usage.get('data_encipherment', False),
            'keyCertSign': key_usage.get('key_cert_sign', False),
            'crlSign': key_usage.get('crl_sign', False),
        } if key_usage else None
        
        # Extract extended key usage
        ext_key_usage = extensions.get('extended_key_usage', {})
        ext_key_usage_dict = {
            'serverAuth': ext_key_usage.get('server_auth', False),
            'clientAuth': ext_key_usage.get('client_auth', False),
            'codeSigning': ext_key_usage.get('code_signing', False),
            'emailProtection': ext_key_usage.get('email_protection', False),
        } if ext_key_usage else None
        
        # Get common name (first entry)
        common_name = subject.get('common_name', [''])[0] if subject.get('common_name') else ''
        
        # Get signature info
        signature = parsed.get('signature', {})
        is_self_signed = signature.get('self_signed', False)

        # Get public key details
        public_key = ''
        if key_info.get('rsa_public_key'):
            public_key = key_info['rsa_public_key'].get('modulus', '')
        elif key_info.get('ecdsa_public_key'):
            # For ECDSA, we might want x and y coordinates or just indicate ECDSA
            # For now, we'll try to get 'public_key' if it exists, or leave empty
            public_key = key_info['ecdsa_public_key'].get('public_key', '')
            
        spki_fingerprint = key_info.get('fingerprint_sha256', '')
        san_names = (
            extensions.get('subject_alt_name', {}).get('dns_names')
            or parsed.get('names', [])
            or []
        )
        
        return {
            'id': str(doc.get('_id', '')),
            'domain': domain,
            'issuer': issuer_org,
            'issuerDn': parsed.get('issuer_dn', ''),
            'validFrom': validity.get('start', ''),
            'validTo': validity.get('end', ''),
            'status': SharedModels.get_status(validity.get('end', '')),
            'grade': SharedModels.get_grade_from_zlint(zlint),
            'encryptionType': encryption_type,
            'keyLength': key_length,
            'signatureAlgorithm': parsed.get('signature_algorithm', {}).get('name', 'Unknown'),
            'vulnerabilities': SharedModels.format_vulnerabilities(zlint),
            'vulnerabilityCount': SharedModels.count_vulnerabilities(zlint),
            'san': san_names,
            'country': SharedModels.get_tld_country(domain),
            'scanDate': validity.get('start', ''),
            'validationLevel': validation_level,
            'zlintDetails': zlint_details if zlint_details else None,
            # Enhanced fields
            'commonName': common_name,
            'subjectDn': parsed.get('subject_dn', ''),
            'selfSigned': is_self_signed,
            'serialNumber': parsed.get('serial_number', ''),
            'fingerprintSha256': parsed.get('fingerprint_sha256', ''),
            'fingerprintSha1': parsed.get('fingerprint_sha1', ''),
            'fingerprintMd5': parsed.get('fingerprint_md5', ''),
            'validityLength': validity.get('length', 0),
            'isCa': extensions.get('basic_constraints', {}).get('is_ca', False),
            'keyUsage': key_usage_dict,
            'extendedKeyUsage': ext_key_usage_dict,
            'crlDistributionPoints': extensions.get('crl_distribution_points', []),
            'authorityInfoAccess': extensions.get('authority_info_access', {}).get('issuer_urls', []),
            'publicKey': public_key,
            'publicKeyHash': spki_fingerprint,
            'sanCount': len(san_names),
            'spkiFingerprint': spki_fingerprint,
            'spkiSubjectFingerprint': doc.get('spki_subject_fingerprint', ''),
        }

    @classmethod
    def _get_shared_key_fingerprints(cls) -> List[str]:
        try:
            shared_groups_collection = MongoDBClient.get_results_db()['shared-keys-detailed']
            return list(shared_groups_collection.distinct(
                'public_key_hash',
                {
                    '$and': [
                        MongoDBClient.get_precomputed_scope_filter(),
                        {
                            '$or': [
                                {'doc_type': 'shared_key_group'},
                                {'doc_type': {'$exists': False}, '_id': {'$ne': 'metadata'}},
                            ]
                        }
                    ]
                }
            ))
        except Exception:
            shared_keys_pipeline = [
                {'$match': {
                    'parsed.subject_key_info.fingerprint_sha256': {'$exists': True, '$ne': None},
                    'parsed.fingerprint_sha256': {'$exists': True, '$ne': None}
                }},
                {'$group': {
                    '_id': '$parsed.subject_key_info.fingerprint_sha256',
                    'cert_fingerprints': {'$addToSet': '$parsed.fingerprint_sha256'}
                }},
                {'$addFields': {'distinct_certs': {'$size': '$cert_fingerprints'}}},
                {'$match': {'distinct_certs': {'$gt': 1}}},
                {'$project': {'_id': 1}}
            ]
            return [
                row['_id']
                for row in cls.collection.aggregate(shared_keys_pipeline, allowDiskUse=True)
            ]

    @classmethod
    def _get_shared_key_context(cls, public_key_hashes: List[str]) -> Dict[str, Dict[str, Any]]:
        hashes = [item for item in public_key_hashes if item]
        if not hashes:
            return {}
        try:
            collection = MongoDBClient.get_results_db()['shared-keys-detailed']
            docs = collection.find({
                '$and': [
                    MongoDBClient.get_precomputed_scope_filter(),
                    {'public_key_hash': {'$in': hashes}},
                    {
                        '$or': [
                            {'doc_type': 'shared_key_group'},
                            {'doc_type': {'$exists': False}, '_id': {'$ne': 'metadata'}},
                        ]
                    }
                ]
            }, {
                'public_key_hash': 1,
                'public_key_hash_short': 1,
                'certificate_count': 1,
                'sample_domains': 1,
                'key_type': 1,
                'issuers': 1,
                'risk_level': 1,
            })
            return {
                doc.get('public_key_hash'): {
                    'publicKeyHash': doc.get('public_key_hash', ''),
                    'publicKeyHashShort': doc.get('public_key_hash_short', ''),
                    'certificateCount': doc.get('certificate_count', 0),
                    'sampleDomains': doc.get('sample_domains', []),
                    'keyType': doc.get('key_type', 'Unknown'),
                    'issuers': doc.get('issuers', []),
                    'riskLevel': doc.get('risk_level', 'UNKNOWN'),
                }
                for doc in docs
                if doc.get('public_key_hash')
            }
        except Exception as exc:
            print(f"[SHARED CERTIFICATES] Shared-key context unavailable: {exc}")
            return {}

    @staticmethod
    def _risk_level(score: int) -> str:
        if score >= 85:
            return 'Critical'
        if score >= 70:
            return 'High'
        if score >= 40:
            return 'Medium'
        return 'Low'

    @classmethod
    def _add_risk_fields(cls, cert: Dict[str, Any]) -> Dict[str, Any]:
        score = 0
        factors = []
        positives = []

        if cert.get('status') == 'EXPIRED':
            score += 30
            factors.append({'label': 'Expired certificate', 'points': 30})
        elif cert.get('status') == 'VALID':
            score -= 5
            positives.append({'label': 'Certificate is currently valid', 'points': -5})

        if cert.get('sharedKeyDetails'):
            score += 30
            factors.append({'label': 'Shared public key', 'points': 30})

        encryption = cert.get('encryptionType') or ''
        if encryption.upper().startswith('RSA') and (cert.get('keyLength') or 0) < 2048:
            score += 20
            factors.append({'label': f"Weak encryption ({encryption})", 'points': 20})
        elif (cert.get('keyLength') or 0) >= 2048 or encryption.upper().startswith(('ECDSA', 'EC')):
            score -= 10
            positives.append({'label': f"Strong key ({encryption})", 'points': -10})

        validity_days = int((cert.get('validityLength') or 0) / 86400)
        cert['validityDays'] = validity_days
        if validity_days > 398:
            score += 10
            factors.append({'label': f'Long validity ({validity_days} days)', 'points': 10})
        elif 0 < validity_days <= 398:
            score -= 5
            positives.append({'label': 'Modern validity period', 'points': -5})

        zlint_counts = cert.get('vulnerabilityCount') or {}
        errors = zlint_counts.get('errors', 0)
        warnings = zlint_counts.get('warnings', 0)
        zlint_penalty = 0
        if errors or warnings:
            zlint_penalty = min(10, errors + ((warnings + 1) // 2))
        if zlint_penalty:
            score += zlint_penalty
            factors.append({'label': f'ZLint issues ({errors} errors, {warnings} warnings)', 'points': zlint_penalty})
        else:
            score -= 5
            positives.append({'label': 'No ZLint errors or warnings', 'points': -5})

        score = max(0, min(100, score))
        cert.update({
            'riskScore': score,
            'riskLevel': cls._risk_level(score),
            'riskFactors': factors,
            'positiveSignals': positives,
            'sharedPublicKey': bool(cert.get('sharedKeyDetails')),
        })
        return cert
    
    @classmethod
    def _hydrate_certificate_ids(cls, certificate_ids: List[Any], page: int, page_size: int) -> List[Dict[str, Any]]:
        skip = (page - 1) * page_size
        page_ids = certificate_ids[skip:skip + page_size]
        if not page_ids:
            return []

        object_ids = []
        for cert_id in page_ids:
            if isinstance(cert_id, ObjectId):
                object_ids.append(cert_id)
                continue
            try:
                object_ids.append(ObjectId(str(cert_id)))
            except Exception:
                continue

        if not object_ids:
            return []

        docs_by_id = {
            doc['_id']: doc
            for doc in cls.collection.find({'_id': {'$in': object_ids}})
        }

        certificates = []
        for cert_id in object_ids:
            doc = docs_by_id.get(cert_id)
            if doc:
                certificates.append(cls.serialize_certificate(doc))
        
        # print("certificates are fetched from db and hydrated based on the certificate ids")
        return certificates

    @classmethod
    def _get_validity_analysis_doc(cls) -> Optional[Dict[str, Any]]:
        try:
            return MongoDBClient.find_scoped_result_doc('validity-analysis', fallback_id='validity_analysis')
        except Exception as e:
            print(f"[VALIDITY FILTER] Error reading pre-computed validity analysis: {e}")
            return None

    @classmethod
    def _get_validity_filter_ids(
        cls,
        validity_bucket: Optional[str] = None,
        expiring_month: Optional[int] = None,
        expiring_year: Optional[int] = None,
        issued_month: Optional[int] = None,
        issued_year: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        doc = cls._get_validity_analysis_doc()
        if not doc:
            return None
        # print("validity analysis doc is fetched for validity filters")
        if validity_bucket:
            bucket_label_map = {
                '0-90': '< 90 Days',
                '90-365': '90 Days - 1 Year',
                '365-730': '1 - 2 Years',
                '730+': '> 2 Years'
            }
            expected_range = bucket_label_map.get(validity_bucket, validity_bucket)

            for bucket in doc.get('validity_distribution', []):
                if bucket.get('range') == expected_range or bucket.get('bucket') == validity_bucket:
                    return {
                        'certificate_ids': bucket.get('certificate_ids', []),
                        'total': bucket.get('count', 0),
                        'has_more': bucket.get('has_more', False)
                    }
            return None

        if expiring_month is not None and expiring_year is not None:
            for item in doc.get('issuance_timeline', []):
                if item.get('monthNum') == expiring_month and item.get('year') == expiring_year:
                    return {
                        'certificate_ids': item.get('expiring_certificate_ids', []),
                        'total': item.get('expiring', 0),
                        'has_more': item.get('expiring_has_more', False)
                    }
            return None

        if issued_month is not None and issued_year is not None:
            for item in doc.get('issuance_timeline', []):
                if item.get('monthNum') == issued_month and item.get('year') == issued_year:
                    return {
                        'certificate_ids': item.get('issued_certificate_ids', []),
                        'total': item.get('issued', 0),
                        'has_more': item.get('issued_has_more', False)
                    }
            return None

        return None

    @classmethod
    def get_all(cls, page: int = 1, page_size: int = 10, 
                status: Optional[str] = None, 
                country: Optional[str] = None,
                issuer: Optional[str] = None,
                search: Optional[str] = None,
                encryption_type: Optional[str] = None,
                has_vulnerabilities: Optional[bool] = None,
                expiring_month: Optional[int] = None,
                expiring_year: Optional[int] = None,
                expiring_days: Optional[int] = None,
                validity_bucket: Optional[str] = None,
                issued_month: Optional[int] = None,
                issued_year: Optional[int] = None,
                issued_within_days: Optional[int] = None,
                # New Signature/Hash page filters
                signature_algorithm: Optional[str] = None,
                weak_hash: Optional[bool] = None,
                self_signed: Optional[bool] = None,
                key_size: Optional[int] = None,
                hash_type: Optional[str] = None,
                # SAN Analytics page filters
                san_tld: Optional[str] = None,
                san_type: Optional[str] = None,
                san_count_min: Optional[int] = None,
                san_count_max: Optional[int] = None,
                expiring_start: Optional[str] = None,
                expiring_end: Optional[str] = None,
                
                # Shared Keys page filter

                shared_key: Optional[bool] = None,
                # Vulnerabilities page filter
                risk_filter: Optional[str] = None,
                # Validation level filter
                validation_levels: Optional[List[str]] = None,
                base_filter: Optional[Dict] = None) -> Dict:
        """Get paginated list of certificates with optional filters
        
        Args:
            expiring_days: Filter for certs expiring within N days (e.g., 30, 60, 90)
            validity_bucket: Filter by validity period bucket (e.g., "0-90", "90-365", "365-730", "730+")
            issued_month: Filter by issuance month (1-12)
            issued_year: Filter by issuance year (e.g., 2025)
            issued_within_days: Filter for certs issued within N days (e.g., 30)
            signature_algorithm: Filter by exact signature algorithm (e.g., "SHA256-RSA")
            weak_hash: Filter certs with weak hash (MD5, SHA-1)
            self_signed: Filter self-signed certificates
            key_size: Filter by exact key size (e.g., 2048, 4096)
            hash_type: Filter by hash algorithm (e.g., "SHA-256", "SHA-1")
            san_tld: Filter by TLD in SAN entries (e.g., ".com", ".pk")
            san_type: Filter by SAN type ("wildcard" or "standard")
            san_count_min: Filter by minimum SAN count
            san_count_max: Filter by maximum SAN count
            expiring_start: Filter by exact expiration start date (ISO string)
            expiring_end: Filter by exact expiration end date (ISO string)
            shared_key: Filter for certs involved in true key reuse (different certs sharing same public key)
            risk_filter: Vulnerability-page filter: all, expired, shared-key, weak-encryption, long-validity, zlint
            base_filter: Global filter query from build_filter_query() - merged with specific filters
        """
        now = cls.get_current_time_iso()
        now_dt = datetime.now(timezone.utc)
        now_plus_30 = (now_dt + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')

        filters = []

        if base_filter:
            filters.append(base_filter.copy())

        if search:
            prefix = re.escape(search)
            filters.append({'domain': {'$regex': f'^{prefix}'}})

        if issuer:
            if issuer.lower() == 'others':
                top_ca_pipeline = [
                    {'$project': {'issuer_org': {'$arrayElemAt': ['$parsed.issuer.organization', 0]}}},
                    {'$match': {'issuer_org': {'$exists': True, '$ne': None}}},
                    {'$group': {'_id': '$issuer_org', 'count': {'$sum': 1}}},
                    {'$sort': {'count': -1}},
                    {'$limit': 10}
                ]
                top_cas = [r['_id'] for r in cls.collection.aggregate(top_ca_pipeline, allowDiskUse=True)]
                filters.append({
                    '$or': [
                        {'parsed.issuer.organization': {'$nin': top_cas}},
                        {'parsed.issuer.organization': {'$exists': False}},
                        {'parsed.issuer.organization': []}
                    ]
                })
            else:
                filters.append({'parsed.issuer.organization': issuer})

        if status:
            status_upper = status.upper()
            if status_upper == 'EXPIRED':
                filters.append({'parsed.validity.end': {'$lt': now}})
            elif status_upper == 'EXPIRING_SOON':
                filters.append({'parsed.validity.end': {'$gte': now, '$lte': now_plus_30}})
            elif status_upper == 'VALID':
                filters.append({'parsed.validity.end': {'$gt': now}})

        if country:
            scope_tld = cls.country_name_to_tld(country)
            print(f"[COUNTRY FILTER] Querying scope for {country} -> {scope_tld}")
            filters.append({'scope': scope_tld})

        if encryption_type:
            parts = encryption_type.split()
            if parts:
                algo_name = parts[0]
                filters.append({'parsed.subject_key_info.key_algorithm.name': algo_name})
                if len(parts) >= 2:
                    try:
                        key_length = int(parts[1])
                        if algo_name.upper() == 'RSA':
                            filters.append({'parsed.subject_key_info.rsa_public_key.length': key_length})
                        elif algo_name.upper() in ['ECDSA', 'EC']:
                            filters.append({'parsed.subject_key_info.ecdsa_public_key.length': key_length})
                    except ValueError:
                        pass

        if has_vulnerabilities:
            filters.append({'zlint.errors_present': True})

        normalized_risk_filter = (risk_filter or '').strip().lower()
        if normalized_risk_filter:
            risk_conditions = {
                'expired': {'parsed.validity.end': {'$lt': now}},
                'weak-encryption': {'parsed.subject_key_info.rsa_public_key.length': {'$lt': 2048}},
                'long-validity': {'parsed.validity.length': {'$gt': 398 * 86400}},
                'zlint': {'$or': [{'zlint.errors_present': True}, {'zlint.warnings_present': True}]},
            }
            if normalized_risk_filter == 'shared-key':
                shared_key = True
            elif normalized_risk_filter == 'all':
                all_conditions = list(risk_conditions.values())
                shared_fingerprints_for_risk = cls._get_shared_key_fingerprints()
                if shared_fingerprints_for_risk:
                    all_conditions.append({
                        'parsed.subject_key_info.fingerprint_sha256': {'$in': shared_fingerprints_for_risk[:10000]}
                    })
                filters.append({'$or': all_conditions})
            elif normalized_risk_filter in risk_conditions:
                filters.append(risk_conditions[normalized_risk_filter])

        if signature_algorithm:
            filters.append({'parsed.signature_algorithm.name': signature_algorithm})

        if weak_hash:
            filters.append({
                '$or': [
                    {'parsed.signature_algorithm.name': {'$regex': '^SHA1|^SHA-1', '$options': 'i'}},
                    {'parsed.signature_algorithm.name': {'$regex': '^MD5', '$options': 'i'}}
                ]
            })

        if self_signed:
            filters.append({'parsed.signature.self_signed': True})

        if key_size:
            print(f"Applying key size filter: {key_size} bits")
            filters.append({
                '$or': [
                    {'parsed.subject_key_info.rsa_public_key.length': key_size},
                    {'parsed.subject_key_info.ecdsa_public_key.length': key_size}
                ]
            })

        if hash_type:
            print(f"Applying hash type filter: {hash_type}")
            hash_patterns = {
                'SHA-256': '^SHA256|^SHA-256',
                'SHA-384': '^SHA384|^SHA-384',
                'SHA-512': '^SHA512|^SHA-512',
                'SHA-1': '^SHA1|^SHA-1',
                'MD5': '^MD5'
            }
            pattern = hash_patterns.get(hash_type, f'^{re.escape(hash_type.replace("-", ""))}')
            filters.append({'parsed.signature_algorithm.name': {'$regex': pattern, '$options': 'i'}})

        if expiring_month and expiring_year:
            from calendar import monthrange
            _, last_day = monthrange(expiring_year, expiring_month)
            filters.append({'parsed.validity.end': {
                '$gte': f"{expiring_year}-{expiring_month:02d}-01T00:00:00Z",
                '$lte': f"{expiring_year}-{expiring_month:02d}-{last_day:02d}T23:59:59Z"
            }})

        if expiring_start and expiring_end:
            print(f"Applying custom expiration range filter: {expiring_start} to {expiring_end}")
            filters.append({'parsed.validity.end': {'$gte': expiring_start, '$lte': expiring_end}})

        if issued_month and issued_year:
            from calendar import monthrange
            _, last_day = monthrange(issued_year, issued_month)
            filters.append({'parsed.validity.start': {
                '$gte': f"{issued_year}-{issued_month:02d}-01T00:00:00Z",
                '$lte': f"{issued_year}-{issued_month:02d}-{last_day:02d}T23:59:59Z"
            }})

        if issued_within_days:
            print(f"Applying issued within last {issued_within_days} days filter")
            past_date = (now_dt - timedelta(days=issued_within_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
            filters.append({'parsed.validity.start': {'$gte': past_date, '$lte': now}})

        if expiring_days:
            target_date = (now_dt + timedelta(days=expiring_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
            filters.append({'parsed.validity.end': {'$gt': now, '$lte': target_date}})

        if validation_levels:
            normalized_levels = [
                level.strip().upper()
                for level in validation_levels
                if isinstance(level, str) and level.strip().upper() in ['DV', 'OV', 'EV']
            ]
            if normalized_levels:
                filters.append({'parsed.validation_level': {'$in': normalized_levels}})
            
        if validity_bucket:
            bucket_ranges = {
                '0-90': (0, 90),
                '90-365': (90, 365),
                '365-730': (365, 730),
                '730+': (730, 100000)
            }
            if validity_bucket in bucket_ranges:
                min_days, max_days = bucket_ranges[validity_bucket]
                filters.append({'parsed.validity.length': {
                    '$gte': min_days * 86400,
                    '$lt': max_days * 86400
                }})

        # SAN filters are intentionally disabled here because SAN analytics now
        # handles these paths separately. Kept for reference:
        # if san_tld:
        #     tld_pattern = san_tld.lstrip('.')
        #     filters.append({'parsed.extensions.subject_alt_name.dns_names': {
        #         '$regex': f'\\.{tld_pattern}$',
        #         '$options': 'i'
        #     }})
        # if san_type:
        #     if san_type.lower() == 'wildcard':
        #         filters.append({'parsed.extensions.subject_alt_name.dns_names': {
        #             '$regex': '^\\*\\.',
        #             '$options': 'i'
        #         }})
        #     elif san_type.lower() == 'standard':
        #         filters.append({'parsed.extensions.subject_alt_name.dns_names': {'$exists': True, '$ne': []}})
        #         filters.append({'parsed.extensions.subject_alt_name.dns_names': {'$not': {'$regex': '^\\*\\.'}}})
        # if san_count_min is not None or san_count_max is not None:
        #     san count requires aggregation with $size and is handled by SAN-specific code.

        if shared_key:
            shared_fingerprints = cls._get_shared_key_fingerprints()
            filters.append({
                'parsed.subject_key_info.fingerprint_sha256': {
                    '$in': shared_fingerprints if shared_fingerprints else []
                }
            })

        if not filters:
            query = {}
        elif len(filters) == 1:
            query = filters[0]
        else:
            query = {'$and': filters}

        print(f"[CERTIFICATES QUERY] filters={len(filters)} risk_filter={normalized_risk_filter or 'none'}")

        search_hint = None
        if search:
            search_hint = (
                'idx_domain'
                if MongoDBClient.get_current_scope() in ('', 'all', 'global')
                else 'idx_scope_domain'
            )

        risk_hint = None
        scoped_query = MongoDBClient.get_current_scope() not in ('', 'all', 'global')
        if normalized_risk_filter == 'expired':
            risk_hint = 'idx_scope_validity_end' if scoped_query else 'idx_validity_end'
        elif normalized_risk_filter == 'weak-encryption':
            risk_hint = 'idx_scope_rsa_public_key_length' if scoped_query else 'idx_rsa_public_key_length'
        elif normalized_risk_filter == 'long-validity':
            risk_hint = 'idx_scope_validity_length' if scoped_query else 'idx_validity_length'
        elif normalized_risk_filter == 'shared-key':
            risk_hint = 'idx_scope_public_key_fingerprint' if scoped_query else 'idx_public_key_fingerprint'

        if not query:
            total = cls.collection.estimated_document_count()
        elif search_hint:
            total = cls.collection.count_documents(query, hint=search_hint)
        elif risk_hint:
            total = cls.collection.count_documents(query, hint=risk_hint)
        else:
            total = cls.collection.count_documents(query)

        skip = (page - 1) * page_size
        find_cursor = cls.collection.find(query)
        if search_hint:
            find_cursor = find_cursor.hint(search_hint)
        elif risk_hint:
            find_cursor = find_cursor.hint(risk_hint)
        elif not issuer:
            find_cursor = find_cursor.sort('_id', 1)
            if not query:
                if MongoDBClient.get_current_scope() in ('', 'all', 'global'):
                    find_cursor = find_cursor.hint('_id_')
                else:
                    find_cursor = find_cursor.hint('idx_scope_id')
        cursor = find_cursor.skip(skip).limit(page_size)

        certificates = [cls.serialize_certificate(doc) for doc in cursor]
        shared_context = cls._get_shared_key_context([
            cert.get('publicKeyHash') for cert in certificates
        ])
        for cert in certificates:
            public_key_hash = cert.get('publicKeyHash')
            if public_key_hash and public_key_hash in shared_context:
                cert['sharedKeyDetails'] = shared_context[public_key_hash]
            if normalized_risk_filter:
                cls._add_risk_fields(cert)

        pagination = {
            'page': page,
            'pageSize': page_size,
            'total': total,
            'totalPages': max(1, (total + page_size - 1) // page_size)
        }
        return {
            'certificates': certificates,
            'pagination': pagination
        }

        # Legacy get_all implementation is kept below for reference only.
        # Runtime returns from the normalized single-query flow above.
        
        # now = cls.get_current_time_iso()
        # now_plus_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # # Build query based on filters
        # query = {}
        
        # # Apply base filter from global filters (date range, etc)
        # if base_filter:
        #     query = base_filter.copy()
        
        # if search:
        #     # Prefix search on domain (index-friendly with idx_domain).
        #     prefix = re.escape(search)
        #     query['domain'] = {'$regex': f'^{prefix}'}
        
        # if issuer:
        #     if issuer.lower() == 'others':
        #         # Get top 10 CAs and exclude them using $nin
        #         top_ca_pipeline = [
        #             {'$project': {
        #                 'issuer_org': {'$arrayElemAt': ['$parsed.issuer.organization', 0]}
        #             }},
        #             {'$match': {'issuer_org': {'$exists': True, '$ne': None}}},
        #             {'$group': {
        #                 '_id': '$issuer_org',
        #                 'count': {'$sum': 1}
        #             }},
        #             {'$sort': {'count': -1}},
        #             {'$limit': 10}
        #         ]
        #         top_cas = [r['_id'] for r in cls.collection.aggregate(top_ca_pipeline)]
        #         # Match certificates where issuer is NOT in top 10
        #         query['$and'] = query.get('$and', [])
        #         query['$and'].append({
        #             '$or': [
        #                 {'parsed.issuer.organization': {'$nin': top_cas}},
        #                 {'parsed.issuer.organization': {'$exists': False}}
        #             ]
        #         })
        #     else:
        #         # FIX: Use the actual issuer.organization field that exists in the database
        #         # parsed.issuer.organization is an array, so we use $in to match any element
        #         query['parsed.issuer.organization'] = {'$in': [issuer]}
        
        # # Apply status filter - VALID includes ALL non-expired certificates
        # if status:
        #     status_upper = status.upper()
        #     if status_upper == 'EXPIRED':
        #         query['parsed.validity.end'] = {'$lt': now}
        #     elif status_upper == 'EXPIRING_SOON':
        #         query['parsed.validity.end'] = {'$gte': now, '$lte': now_plus_30}
        #     elif status_upper == 'VALID':
        #         # VALID = ALL non-expired certificates (includes expiring_soon)
        #         query['parsed.validity.end'] = {'$gt': now}
        
        # # Filter by encryption type (e.g., "RSA 2048", "ECDSA 256")
        # if encryption_type:
        #     parts = encryption_type.split()
        #     if len(parts) >= 1:
        #         algo_name = parts[0]
        #         query['parsed.subject_key_info.key_algorithm.name'] = algo_name
        #         if len(parts) >= 2:
        #             try:
        #                 key_length = int(parts[1])
        #                 # Check both RSA and ECDSA key length fields
        #                 if algo_name.upper() == 'RSA':
        #                     query['parsed.subject_key_info.rsa_public_key.length'] = key_length
        #                 elif algo_name.upper() in ['ECDSA', 'EC']:
        #                     query['parsed.subject_key_info.ecdsa_public_key.length'] = key_length
        #             except ValueError:
        #                 pass
        
        # # Filter by exact signature algorithm (e.g., "SHA256-RSA", "ECDSA-SHA256")
        # if signature_algorithm:
        #     query['parsed.signature_algorithm.name'] = signature_algorithm
        
        # # Filter by weak hash (SHA-1, MD5) - for Weak Hash Alert card
        # if weak_hash:
        #     query['$or'] = query.get('$or', [])
        #     if not query['$or']:
        #         query['$or'] = [
        #             {'parsed.signature_algorithm.name': {'$regex': '^SHA1|^SHA-1', '$options': 'i'}},
        #             {'parsed.signature_algorithm.name': {'$regex': '^MD5', '$options': 'i'}}
        #         ]
        
        # # Filter by self-signed certificates
        # if self_signed:
        #     query['parsed.signature.self_signed'] = True
        
        # # Filter by exact key size (e.g., 2048, 4096)
        # if key_size:

        #     print(f"Applying key size filter: {key_size} bits")

        #     query['$or'] = query.get('$or', [])
        #     if not query['$or']:
        #         query['$or'] = [
        #             {'parsed.subject_key_info.rsa_public_key.length': key_size},
        #             {'parsed.subject_key_info.ecdsa_public_key.length': key_size}
        #         ]
        
        # # Filter by hash type (e.g., "SHA-256", "SHA-1")
        # if hash_type:
        #     # Map hash type to regex pattern for signature_algorithm.name
        #     print(f"Applying hash type filter: {hash_type}")
        #     hash_patterns = {
        #         'SHA-256': '^SHA256',
        #         'SHA-384': '^SHA384',
        #         'SHA-512': '^SHA512',
        #         'SHA-1': '^SHA1|^SHA-1',
        #         'MD5': '^MD5'
        #     }
        #     pattern = hash_patterns.get(hash_type, f'^{hash_type.replace("-", "")}')
        #     query['parsed.signature_algorithm.name'] = {'$regex': pattern, '$options': 'i'}
        
        # # Filter by expiring month/year - get certs that expire/expired in that month
        # if expiring_month and expiring_year:
        #     from calendar import monthrange
        #     # Get first and last day of the month
        #     _, last_day = monthrange(expiring_year, expiring_month)
        #     month_start = f"{expiring_year}-{expiring_month:02d}-01T00:00:00Z"
        #     month_end = f"{expiring_year}-{expiring_month:02d}-{last_day:02d}T23:59:59Z"
        #     query['parsed.validity.end'] = {'$gte': month_start, '$lte': month_end}
        
        # # Filter by custom expiration range (e.g. for weekly view)
        # if expiring_start and expiring_end:
        #     print(f"Applying custom expiration range filter: {expiring_start} to {expiring_end}")
        #     # If both month filter and range filter are present, range takes precedence
        #     # or we could combine them, but range is usually more specific
        #     query['parsed.validity.end'] = {'$gte': expiring_start, '$lte': expiring_end}
        
        # # Filter by issued month/year - get certs that were issued (validFrom) in that month
        # if issued_month and issued_year:
        #     from calendar import monthrange
        #     # Get first and last day of the month
        #     _, last_day = monthrange(issued_year, issued_month)
        #     month_start = f"{issued_year}-{issued_month:02d}-01T00:00:00Z"
        #     month_end = f"{issued_year}-{issued_month:02d}-{last_day:02d}T23:59:59Z"
        #     query['parsed.validity.start'] = {'$gte': month_start, '$lte': month_end}
        
        # # Filter by issued within N days (for "Issued (30d)" card click)
        # if issued_within_days:
        #     print(f"Applying issued within last {issued_within_days} days filter")
        #     now_dt = datetime.now(timezone.utc)
        #     past_date = (now_dt - timedelta(days=issued_within_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        #     # Certificates with validity start date within the last N days
        #     query['parsed.validity.start'] = {
        #         '$gte': past_date,  # Issued within last N days
        #         '$lte': now  # Up to now
        #     }
        
        # # Filter by expiring within N days (distinct from 30-day expiring_soon status)
        # if expiring_days:
        #     now_dt = datetime.now(timezone.utc)
        #     target_date = (now_dt + timedelta(days=expiring_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        #     # Override any existing validity.end filter
        #     query['parsed.validity.end'] = {
        #         '$gt': now,  # Not yet expired
        #         '$lte': target_date  # Within expiring_days window
        #     }

        # # Filter by validation level (DV, OV, EV)
        # if validation_levels and len(validation_levels) > 0:
        #     validation_queries = []
        #     for level in validation_levels:
        #         normalized_level = level.strip().upper()
        #         if normalized_level in ['DV', 'OV', 'EV']:
        #             validation_queries.append({'parsed.validation_level': normalized_level})
        #     if validation_queries:
        #         validation_filter = validation_queries[0] if len(validation_queries) == 1 else {'$or': validation_queries}
        #         if not query:
        #             query = validation_filter
        #         else:
        #             if '$and' in query:
        #                 query['$and'].append(validation_filter)
        #             else:
        #                 query = {'$and': [query, validation_filter]}

        # # Filter by validity period bucket (duration in days)
        # # ✅ OPTIMIZED: Use pre-computed validity.length field instead of date parsing
        # if validity_bucket:
        #     # Extract min/max days from bucket string
        #     # Buckets: "0-90", "90-365", "365-730", "730+"
        #     bucket_ranges = {
        #         '0-90': (0, 90),
        #         '90-365': (90, 365),
        #         '365-730': (365, 730),
        #         '730+': (730, 100000)
        #     }
        #     if validity_bucket in bucket_ranges:
        #         min_days, max_days = bucket_ranges[validity_bucket]
        #         # Convert days to seconds (validity.length is in seconds)
        #         min_seconds = min_days * 86400
        #         max_seconds = max_days * 86400
                
        #         # Use direct query on validity.length field (pre-computed in DB)
        #         # This is MUCH faster than date parsing aggregation
        #         query['parsed.validity.length'] = {
        #             '$gte': min_seconds,
        #             '$lt': max_seconds
        #         }
        
        # # Handle has_vulnerabilities with OPTIMIZED query using boolean flag
        # if has_vulnerabilities:
        #     # Use the zlint.errors_present boolean flag for fast indexed lookup
        #     # This is the same approach as Global Health / Active Certs - FAST
        #     vuln_query = {'zlint.errors_present': True}
            
        #     # Get total count - simple indexed query
        #     total = cls.collection.count_documents(vuln_query)
            
        #     # Get paginated results - simple find with skip/limit
        #     skip = (page - 1) * page_size
        #     cursor = cls.collection.find(vuln_query).skip(skip).limit(page_size)
            
        #     certificates = []
        #     for doc in cursor:
        #         cert = cls.serialize_certificate(doc)
        #         certificates.append(cert)
            
        #     return {
        #         'certificates': certificates,
        #         'pagination': {
        #             'page': page,
        #             'pageSize': page_size,
        #             'total': total,
        #             'totalPages': max(1, (total + page_size - 1) // page_size)
        #         }
        #     }
        
        # # ⚡ OPTIMIZED: Handle country filter using pre-computed certificate IDs
        # # PERFORMANCE: 110 seconds → 0.1 seconds (1,100x faster!)
        # if country:
        #     print(f"[COUNTRY FILTER] Using pre-computed IDs for: {country}")
        #     try:
        #         # Get certificate IDs from pre-computed collection
        #         country_collection = MongoDBClient.get_results_db()['geographic-distribution']
        #         country_doc = country_collection.find_one({'_id': country})
                
        #         if not country_doc:
        #             print(f"[COUNTRY FILTER] No pre-computed data for: {country}")
        #             # Fall back to empty result
        #             return {
        #                 'certificates': [],
        #                 'pagination': {
        #                     'page': page,
        #                     'pageSize': page_size,
        #                     'total': 0,
        #                     'totalPages': 0
        #                 }
        #             }
                
        #         # Get all certificate IDs for this country
        #         cert_ids = country_doc.get('certificate_ids', [])
        #         total = country_doc.get('count', len(cert_ids))
        #         has_more = country_doc.get('has_more', total > len(cert_ids))
                
        #         print(f"[COUNTRY FILTER] Found {total} certificates for {country}")
                
        #         # Paginate certificate IDs
        #         skip = (page - 1) * page_size
        #         page_ids = cert_ids[skip:skip + page_size]
                
        #         docs_by_id = {
        #             doc['_id']: doc
        #             for doc in cls.collection.find({'_id': {'$in': page_ids}})
        #         }
        #         certificates = []
        #         for cert_id in page_ids:
        #             doc = docs_by_id.get(cert_id)
        #             if doc:
        #                 certificates.append(cls.serialize_certificate(doc))
                
        #         return {
        #             'certificates': certificates,
        #             'pagination': {
        #                 'page': page,
        #                 'pageSize': page_size,
        #                 'total': total,
        #                 'totalPages': max(1, (total + page_size - 1) // page_size),
        #                 'has_more': has_more and (skip + len(certificates) < min(total, len(cert_ids)))
        #             }
        #         }
                
        #     except Exception as e:
        #         print(f"[COUNTRY FILTER] Error accessing pre-computed data: {e}")
        #         # Fall back to empty result rather than slow regex
        #         return {
        #             'certificates': [],
        #             'pagination': {
        #                 'page': page,
        #                 'pageSize': page_size,
        #                 'total': 0,
        #                 'totalPages': 0
        #             }
        #         }
        
        # # ⚡ OPTIMIZED: Handle validity filters using pre-computed IDs from validity-analysis
        # if validity_bucket or (expiring_month and expiring_year) or (issued_month and issued_year):
        #     print("[VALIDITY FILTER] Using pre-computed IDs for validity filter")
        #     if search or issuer or encryption_type or has_vulnerabilities or expiring_days or san_tld or san_type or san_count_min is not None or san_count_max is not None or expiring_start or expiring_end or signature_algorithm or weak_hash or self_signed or key_size or hash_type or shared_key or base_filter:
        #         print("[VALIDITY FILTER] Additional filters detected, falling back to query path")
        #     else:
        #         ids_data = cls._get_validity_filter_ids(
        #             validity_bucket=validity_bucket,
        #             expiring_month=expiring_month,
        #             expiring_year=expiring_year,
        #             issued_month=issued_month,
        #             issued_year=issued_year,
        #         )
        #         if ids_data is None:
        #             print("[VALIDITY FILTER] No pre-computed results for this filter. Falling back to live query.")
        #         else:
        #             certificate_ids = ids_data.get('certificate_ids', [])
        #             total = ids_data.get('total', 0)
        #             has_more = ids_data.get('has_more', total > len(certificate_ids))

        #             certificates = cls._hydrate_certificate_ids(certificate_ids, page, page_size)
        #             skip = (page - 1) * page_size

        #             return {
        #                 'certificates': certificates,
        #                 'pagination': {
        #                     'page': page,
        #                     'pageSize': page_size,
        #                     'total': total,
        #                     'totalPages': max(1, (total + page_size - 1) // page_size),
        #                     'has_more': has_more and (skip + len(certificates) < min(total, len(certificate_ids)))
        #                 }
        #             }

        # # SAN TLD filter - filter certs where any dns_name ends with the TLD
        # if san_tld:
        #     # Remove leading dot if present for regex
        #     tld_pattern = san_tld.lstrip('.')
        #     # Match dns_names ending with the TLD
        #     query['parsed.extensions.subject_alt_name.dns_names'] = {
        #         '$regex': f'\\.{tld_pattern}$',
        #         '$options': 'i'
        #     }
        
        # # SAN type filter - filter by wildcard or standard SANs
        # if san_type:
        #     if san_type.lower() == 'wildcard':
        #         # Match certs with at least one wildcard SAN (starts with *.)
        #         query['parsed.extensions.subject_alt_name.dns_names'] = {
        #             '$regex': '^\\*\\.',
        #             '$options': 'i'
        #         }
        #     elif san_type.lower() == 'standard':
        #         # Match certs where no SAN starts with *. 
        #         # This is trickier - we'll use $not to exclude wildcards
        #         query['$and'] = query.get('$and', [])
        #         query['$and'].append({
        #             'parsed.extensions.subject_alt_name.dns_names': {
        #                 '$exists': True,
        #                 '$ne': []
        #             }
        #         })
        #         query['$and'].append({
        #             'parsed.extensions.subject_alt_name.dns_names': {
        #                 '$not': {'$regex': '^\\*\\.'}
        #             }
                    
        #             })
        
        # # ⚡ OPTIMIZED: Shared key filter - use pre-computed materialized view
        # # Previously this ran a 2-minute aggregation on every request
        # if shared_key:
        #     try:
        #         # Get shared key fingerprints from pre-computed materialized view
        #         shared_groups_collection = MongoDBClient.get_results_db()['shared-keys-groups']
                
        #         # Get all shared key fingerprints (excluding metadata doc)
        #         shared_fingerprints = list(shared_groups_collection.find(
        #             {'_id': {'$ne': 'metadata'}},
        #             {'_id': 1}
        #         ))
                
        #         shared_fingerprints = [doc['_id'] for doc in shared_fingerprints]
        #     except Exception:
        #         # Fallback to original slow method if materialized view not available
        #         # (This should only happen if compute_shared_keys.py hasn't been run)
        #         shared_keys_pipeline = [
        #             {'$match': {
        #                 'parsed.subject_key_info.fingerprint_sha256': {'$exists': True, '$ne': None},
        #                 'parsed.fingerprint_sha256': {'$exists': True, '$ne': None}
        #             }},
        #             {'$group': {
        #                 '_id': '$parsed.subject_key_info.fingerprint_sha256',
        #                 'cert_fingerprints': {'$addToSet': '$parsed.fingerprint_sha256'}
        #             }},
        #             {'$addFields': {
        #                 'distinct_certs': {'$size': '$cert_fingerprints'}
        #             }},
        #             {'$match': {'distinct_certs': {'$gt': 1}}},
        #             {'$project': {'_id': 1}}
        #         ]
                
        #         shared_fingerprints = [r['_id'] for r in cls.collection.aggregate(shared_keys_pipeline, allowDiskUse=True)]
            
        #     if shared_fingerprints:
        #         # Filter certs to only those with shared public keys
        #         if '$and' not in query:
        #             query['$and'] = []
        #         query['$and'].append({
        #             'parsed.subject_key_info.fingerprint_sha256': {'$in': shared_fingerprints}
        #         })
        #     else:
        #         # No shared keys found, return empty result
        #         return {
        #             'certificates': [],
        #             'pagination': {
        #                 'page': page,
        #                 'pageSize': page_size,
        #                 'total': 0,
        #                 'totalPages': 0
        #             }
        #         }
        
        # # SAN count filter - filter by number of SANs (dns_names array size)
        # if san_count_min is not None or san_count_max is not None:
        #     # Use aggregation pipeline for array size filtering
        #     pipeline = [
        #         {'$match': query if query else {}},
        #         # Add a field for the count of dns_names
        #         {'$addFields': {
        #             'sanCount': {
        #                 '$size': {'$ifNull': ['$parsed.extensions.subject_alt_name.dns_names', []]}
        #             }
        #         }},
        #     ]
            
        #     # Build match condition for san count
        #     san_count_match = {}
        #     if san_count_min is not None:
        #         san_count_match['$gte'] = san_count_min
        #     if san_count_max is not None:
        #         san_count_match['$lte'] = san_count_max
            
        #     if san_count_match:
        #         pipeline.append({'$match': {'sanCount': san_count_match}})
            
        #     # Get total count first
        #     count_pipeline = pipeline + [{'$count': 'total'}]
        #     count_result = list(cls.collection.aggregate(count_pipeline, allowDiskUse=True))
        #     total = count_result[0]['total'] if count_result else 0
            
        #     # Get paginated results
        #     skip = (page - 1) * page_size
        #     result_pipeline = pipeline + [
        #         {'$skip': skip},
        #         {'$limit': page_size}
        #     ]
            
        #     certificates = []
        #     for doc in cls.collection.aggregate(result_pipeline, allowDiskUse=True):
        #         cert = cls.serialize_certificate(doc)
        #         certificates.append(cert)
            
        #     return {
        #         'certificates': certificates,
        #         'pagination': {
        #             'page': page,
        #             'pageSize': page_size,
        #             'total': total,
        #             'totalPages': max(1, (total + page_size - 1) // page_size)
        #         }
        #     }
        
        # # Get total count with filters applied
        # # ✅ OPTIMIZATION: Use estimated_document_count() when query is empty (878K docs)
        # if not query or query == {}:
        #     total = cls.collection.estimated_document_count()
        # elif issuer and not search and issuer.lower() != 'others':
        #     # ULTRA-FAST: Get count from pre-computed CA analytics for exact issuer matches
        #     # ⚠️ CRITICAL: Only use pre-computed count if NO other filters are present!
        #     # If any additional filters are applied, fall back to live count_documents()
        #     # to ensure accurate pagination
        #     has_additional_filters = (
        #         status or encryption_type or signature_algorithm or weak_hash or 
        #         self_signed or key_size or hash_type or expiring_days or validity_bucket or
        #         (issued_month and issued_year) or issued_within_days or 
        #         validation_levels or san_tld or san_type or 
        #         (san_count_min is not None or san_count_max is not None) or
        #         (expiring_start or expiring_end) or shared_key or base_filter
        #     )
            
        #     if not has_additional_filters:
        #         # Safe to use pre-computed count (issuer-only filter)
        #         try:
        #             ca_doc = MongoDBClient.find_scoped_result_doc('ca-analysis', fallback_id='ca_analysis')
        #             ca_record = next(
        #                 (item for item in ca_doc.get('ca-list', []) if item.get('name') == issuer),
        #                 None
        #             ) if ca_doc else None
        #             if ca_record:
        #                 total = ca_record.get('count', 0)
        #             else:
        #                 # Fallback to live count if not in pre-computed data
        #                 total = cls.collection.count_documents(query)
        #         except Exception as e:
        #             # Fallback to standard count on error
        #             total = cls.collection.count_documents(query)
        #     else:
        #         # Additional filters present: use live count for accurate pagination
        #         print(f"[PAGINATION] Issuer + additional filters detected, using live count")
        #         total = cls.collection.count_documents(query)
        # else:
        #     total = cls.collection.count_documents(query)
        
        # # Get paginated results
        # # ✅ OPTIMIZATION: Sort by _id (indexed) for fast pagination
        # # When using issuer filter, skip sort to avoid expensive in-memory sort operation
        # skip = (page - 1) * page_size
        # if search:
        #     # Prefix search: use indexed domain filter and stable _id sort.
        #     cursor = cls.collection.find(query).sort('_id', 1).skip(skip).limit(page_size)
        # elif issuer:
        #     # Issuer filter: Return results in natural order to avoid expensive in-memory sort
        #     # MongoDB would have to sort 339K+ documents if we add sort here
        #     # Better to return results in natural order (insertion order)
        #     cursor = cls.collection.find(query).skip(skip).limit(page_size)
        # else:
        #     # Regular query: Use hint to optimize with _id index
        #     cursor = cls.collection.find(query).sort('_id', 1).hint('_id_').skip(skip).limit(page_size)
        
        # certificates = []
        # for doc in cursor:
        #     cert = cls.serialize_certificate(doc)
        #     certificates.append(cert)
        
        # return {
        #     'certificates': certificates,
        #     'pagination': {
        #         'page': page,
        #         'pageSize': page_size,  
        #         'total': total,
        #         'totalPages': max(1, (total + page_size - 1) // page_size)
        #     }
        # }    
    

    @classmethod
    def get_by_id(cls, cert_id: str) -> Optional[Dict]:
        """Get single certificate by ID"""
        try:
            doc = cls.collection.find_one({'_id': ObjectId(cert_id)})
            if doc:
                return cls.serialize_certificate(doc)
            return None
        except Exception as e:
            print(f"Error getting certificate by ID: {e}")
            return None

    # =========================================================================
    # NEW CA-ANALYSIS IMPLEMENTATION
    # -------------------------------------------------------------------------
    # Overrides the earlier get_ca_distribution_fast method so shared
    # /api/shared/ca-analytics/ reads from:
    #
    #   <results_db>.ca-analysis / {"_id": "ca_analysis"}
    #
    # The earlier method is kept above for reference and rollback.
    # =========================================================================

    @classmethod
    def get_ca_distribution_fast(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        if base_filter:
            print("[WARNING] CA Analytics: base_filter provided, falling back to slow aggregation")
            return cls.get_ca_distribution(limit=limit, base_filter=base_filter)

        try:
            analysis_doc = MongoDBClient.find_scoped_result_doc('ca-analysis', fallback_id='ca_analysis')
            if not analysis_doc:
                print("[WARNING] CA Analytics: No ca-analysis data found, falling back to slow method")
                return cls.get_ca_distribution(limit=limit, base_filter=None)

            ca_records = sorted(
                analysis_doc.get('ca-list', []),
                key=lambda item: item.get('rank', 999999),
            )[:limit]

            if not ca_records:
                print("[WARNING] CA Analytics: Empty ca-list, falling back to slow method")
                return cls.get_ca_distribution(limit=limit, base_filter=None)

            total_certificates = analysis_doc.get('total_certs', 0)
            top_ca_count = sum(record.get('count', 0) for record in ca_records)
            others_count = max(0, total_certificates - top_ca_count)

            ca_list = [
                {
                    'id': record.get('ca_id', f"ca-{i}"),
                    'name': record.get('name'),
                    'count': record.get('count', 0),
                    'maxCount': record.get('max_count', ca_records[0].get('count', 0)),
                    'percentage': record.get('percentage', 0),
                    'color': record.get('color', '#6b7280')
                }
                for i, record in enumerate(ca_records)
            ]

            if others_count > 0 and ca_records:
                max_count = ca_records[0].get('max_count', ca_records[0].get('count', 0))
                ca_list.append({
                    'id': 'ca-others',
                    'name': 'Others',
                    'count': others_count,
                    'maxCount': max_count,
                    'percentage': round((others_count / total_certificates) * 100, 1) if total_certificates else 0,
                    'color': '#6b7280',
                    'isOthers': True
                })

            return ca_list

        except Exception as e:
            print(f"[ERROR] CA Analytics Fast: {str(e)}, falling back to slow method")
            return cls.get_ca_distribution(limit=limit, base_filter=None)
