
from datetime import datetime, timezone, timedelta
import re
from typing import List, Dict, Any, Optional
from bson import ObjectId

from ..db import db, MongoDBClient

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
    "ls": "Lesotho", "ao": "Angola", "na": "Namibia", "gh": "Ghana", "ng": "Nigeria", "dz": "Algeria",
    'ebad': 'ebad',  # For testing unknown TLD handling
    'soy' : 'say' # For testing again 
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
    
    @classmethod
    def get_ca_distribution_fast(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        """
        ⚡ FAST VERSION: Get Certificate Authority distribution from pre-computed collection
        
        This method reads from a materialized view that's updated periodically (every 6-12 hours)
        by the compute_ca_analytics.py script.
        
        Performance: ~0.01s (reads from pre-computed results)
        
        Limitation: 
        - Does NOT support base_filter (global filters) - returns full pre-computed data
        - If you need filtered results, falls back to get_ca_distribution() (slow)
        
        Args:
            limit: Number of top CAs to return (default: 10)
            base_filter: If provided, falls back to slow method (not supported)
            
        Returns:
            List of CA distribution data in API-ready format
        """
        
        # If filter is provided, fall back to slow method
        if base_filter:
            print("[WARNING] CA Analytics: base_filter provided, falling back to slow aggregation")
            return cls.get_ca_distribution(limit=limit, base_filter=base_filter)
        
        try:
            # Read from pre-computed collection
            ca_analytics_collection = MongoDBClient.get_results_db()['ca-analytics']
            
            # Get metadata to check freshness
            metadata = ca_analytics_collection.find_one({'_id': 'metadata'})
            if not metadata:
                print("[WARNING] CA Analytics: No pre-computed data found, falling back to slow method")
                return cls.get_ca_distribution(limit=limit, base_filter=None)
            
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
                        print(f"[WARNING] CA Analytics: Pre-computed data is {age_hours:.1f} hours old")
            
            # Fetch top N CAs
            ca_records = list(
                ca_analytics_collection
                .find({'_id': {'$ne': 'metadata'}})  # Exclude metadata document
                .sort('rank', 1)  # Sort by rank ascending
                .limit(limit)
            )
            
            if not ca_records:
                print("[WARNING] CA Analytics: No CA records found, falling back to slow method")
                return cls.get_ca_distribution(limit=limit, base_filter=None)
            
            # Get total for "Others" calculation
            total_certificates = metadata.get('total_certificates', 0)
            top_ca_count = sum(record['count'] for record in ca_records)
            others_count = max(0, total_certificates - top_ca_count)
            
            # Transform to API format
            ca_list = [
                {
                    'id': record['ca_id'],
                    'name': record['name'],
                    'count': record['count'],
                    'maxCount': record['max_count'],
                    'percentage': record['percentage'],
                    'color': record['color']
                }
                for record in ca_records
            ]
            
            # Add "Others" if needed
            if others_count > 0 and ca_records:
                max_count = ca_records[0]['max_count']
                ca_list.append({
                    'id': 'ca-others',
                    'name': 'Others',
                    'count': others_count,
                    'maxCount': max_count,
                    'percentage': round((others_count / total_certificates) * 100, 1),
                    'color': '#6b7280',
                    'isOthers': True
                })
            
            return ca_list
            
        except Exception as e:
            print(f"[ERROR] CA Analytics Fast: {str(e)}, falling back to slow method")
            return cls.get_ca_distribution(limit=limit, base_filter=None)
 
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
                })
                
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
                })
                
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
            hint='idx_validity_end'  # Force use of index
        )
        print(f"[METRICS] Expired count: {expired_count} ({time.time()-t2:.3f}s)")
        
        # Query 3: Expiring soon - INDEXED query on validity.end
        print("[METRICS] Query 3: Counting expiring soon (indexed)...")
        t3 = time.time()
        expiring_count = cls.collection.count_documents(
            {'parsed.validity.end': {'$gte': now, '$lte': now_plus_30}},
            hint='idx_validity_end'  # Force use of index
        )
        print(f"[METRICS] Expiring count: {expiring_count} ({time.time()-t3:.3f}s)")
        
        # Query 4: Vulnerabilities - INDEXED query on zlint.errors_present
        print("[METRICS] Query 4: Counting vulnerabilities (indexed)...")
        t4 = time.time()
        critical_vulns = cls.collection.count_documents(
            {'zlint.errors_present': True},
            hint='idx_zlint_errors'  # Force use of index
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
            geo_collection = MongoDBClient.get_results_db()['geographic-distribution-1']
            
            # Get metadata to check freshness
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
                .find({
                    '_id': {'$nin': ['metadata', 'Others']},  # Exclude metadata and Others
                    'country': {'$ne': 'Others'}  # Double-check country field
                })
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
            # EV, OV, DV derived from policy identifiers or subject organization presence
            level_filters = []
            for level in validation_levels:
                if level.upper() == 'EV':
                    # EV certs have specific policy OIDs and extended validation
                    level_filters.append({
                        'parsed.extensions.certificate_policies': {'$exists': True}
                    })
                elif level.upper() == 'OV':
                    # OV certs have organization in subject
                    level_filters.append({
                        'parsed.subject.organization': {'$exists': True}
                    })
                elif level.upper() == 'DV':
                    # DV certs typically don't have organization
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
            'san': parsed.get('names', []),
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
            'spkiFingerprint': spki_fingerprint,
            'spkiSubjectFingerprint': doc.get('spki_subject_fingerprint', ''),
        }
    
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
            base_filter: Global filter query from build_filter_query() - merged with specific filters
        """
        
        now = cls.get_current_time_iso()
        now_plus_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Build query based on filters
        query = {}
        
        # Apply base filter from global filters (date range, etc)
        if base_filter:
            query = base_filter.copy()
        
        if search:
            # Prefix search on domain (index-friendly with idx_domain).
            prefix = re.escape(search)
            query['domain'] = {'$regex': f'^{prefix}'}
        
        if issuer:
            if issuer.lower() == 'others':
                # Get top 10 CAs and exclude them using $nin
                top_ca_pipeline = [
                    {'$project': {
                        'issuer_org': {'$arrayElemAt': ['$parsed.issuer.organization', 0]}
                    }},
                    {'$match': {'issuer_org': {'$exists': True, '$ne': None}}},
                    {'$group': {
                        '_id': '$issuer_org',
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'count': -1}},
                    {'$limit': 10}
                ]
                top_cas = [r['_id'] for r in cls.collection.aggregate(top_ca_pipeline)]
                # Match certificates where issuer is NOT in top 10
                query['$and'] = query.get('$and', [])
                query['$and'].append({
                    '$or': [
                        {'parsed.issuer.organization': {'$nin': top_cas}},
                        {'parsed.issuer.organization': {'$exists': False}}
                    ]
                })
            else:
                # FIX: Use the actual issuer.organization field that exists in the database
                # parsed.issuer.organization is an array, so we use $in to match any element
                query['parsed.issuer.organization'] = {'$in': [issuer]}
        
        # Apply status filter - VALID includes ALL non-expired certificates
        if status:
            status_upper = status.upper()
            if status_upper == 'EXPIRED':
                query['parsed.validity.end'] = {'$lt': now}
            elif status_upper == 'EXPIRING_SOON':
                query['parsed.validity.end'] = {'$gte': now, '$lte': now_plus_30}
            elif status_upper == 'VALID':
                # VALID = ALL non-expired certificates (includes expiring_soon)
                query['parsed.validity.end'] = {'$gt': now}
        
        # Filter by encryption type (e.g., "RSA 2048", "ECDSA 256")
        if encryption_type:
            parts = encryption_type.split()
            if len(parts) >= 1:
                algo_name = parts[0]
                query['parsed.subject_key_info.key_algorithm.name'] = algo_name
                if len(parts) >= 2:
                    try:
                        key_length = int(parts[1])
                        # Check both RSA and ECDSA key length fields
                        if algo_name.upper() == 'RSA':
                            query['parsed.subject_key_info.rsa_public_key.length'] = key_length
                        elif algo_name.upper() in ['ECDSA', 'EC']:
                            query['parsed.subject_key_info.ecdsa_public_key.length'] = key_length
                    except ValueError:
                        pass
        
        # Filter by exact signature algorithm (e.g., "SHA256-RSA", "ECDSA-SHA256")
        if signature_algorithm:
            query['parsed.signature_algorithm.name'] = signature_algorithm
        
        # Filter by weak hash (SHA-1, MD5) - for Weak Hash Alert card
        if weak_hash:
            query['$or'] = query.get('$or', [])
            if not query['$or']:
                query['$or'] = [
                    {'parsed.signature_algorithm.name': {'$regex': '^SHA1|^SHA-1', '$options': 'i'}},
                    {'parsed.signature_algorithm.name': {'$regex': '^MD5', '$options': 'i'}}
                ]
        
        # Filter by self-signed certificates
        if self_signed:
            query['parsed.signature.self_signed'] = True
        
        # Filter by exact key size (e.g., 2048, 4096)
        if key_size:
            query['$or'] = query.get('$or', [])
            if not query['$or']:
                query['$or'] = [
                    {'parsed.subject_key_info.rsa_public_key.length': key_size},
                    {'parsed.subject_key_info.ecdsa_public_key.length': key_size}
                ]
        
        # Filter by hash type (e.g., "SHA-256", "SHA-1")
        if hash_type:
            # Map hash type to regex pattern for signature_algorithm.name
            hash_patterns = {
                'SHA-256': '^SHA256',
                'SHA-384': '^SHA384',
                'SHA-512': '^SHA512',
                'SHA-1': '^SHA1|^SHA-1',
                'MD5': '^MD5'
            }
            pattern = hash_patterns.get(hash_type, f'^{hash_type.replace("-", "")}')
            query['parsed.signature_algorithm.name'] = {'$regex': pattern, '$options': 'i'}
        
        # Filter by expiring month/year - get certs that expire/expired in that month
        if expiring_month and expiring_year:
            from calendar import monthrange
            # Get first and last day of the month
            _, last_day = monthrange(expiring_year, expiring_month)
            month_start = f"{expiring_year}-{expiring_month:02d}-01T00:00:00Z"
            month_end = f"{expiring_year}-{expiring_month:02d}-{last_day:02d}T23:59:59Z"
            query['parsed.validity.end'] = {'$gte': month_start, '$lte': month_end}
        
        # Filter by custom expiration range (e.g. for weekly view)
        if expiring_start and expiring_end:
            # If both month filter and range filter are present, range takes precedence
            # or we could combine them, but range is usually more specific
            query['parsed.validity.end'] = {'$gte': expiring_start, '$lte': expiring_end}
        
        # Filter by issued month/year - get certs that were issued (validFrom) in that month
        if issued_month and issued_year:
            from calendar import monthrange
            # Get first and last day of the month
            _, last_day = monthrange(issued_year, issued_month)
            month_start = f"{issued_year}-{issued_month:02d}-01T00:00:00Z"
            month_end = f"{issued_year}-{issued_month:02d}-{last_day:02d}T23:59:59Z"
            query['parsed.validity.start'] = {'$gte': month_start, '$lte': month_end}
        
        # Filter by issued within N days (for "Issued (30d)" card click)
        if issued_within_days:
            now_dt = datetime.now(timezone.utc)
            past_date = (now_dt - timedelta(days=issued_within_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
            # Certificates with validity start date within the last N days
            query['parsed.validity.start'] = {
                '$gte': past_date,  # Issued within last N days
                '$lte': now  # Up to now
            }
        
        # Filter by expiring within N days (distinct from 30-day expiring_soon status)
        if expiring_days:
            now_dt = datetime.now(timezone.utc)
            target_date = (now_dt + timedelta(days=expiring_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
            # Override any existing validity.end filter
            query['parsed.validity.end'] = {
                '$gt': now,  # Not yet expired
                '$lte': target_date  # Within expiring_days window
            }
        
        # Filter by validity period bucket (duration in days)
        # ✅ OPTIMIZED: Use pre-computed validity.length field instead of date parsing
        if validity_bucket:
            # Extract min/max days from bucket string
            # Buckets: "0-90", "90-365", "365-730", "730+"
            bucket_ranges = {
                '0-90': (0, 90),
                '90-365': (90, 365),
                '365-730': (365, 730),
                '730+': (730, 100000)
            }
            if validity_bucket in bucket_ranges:
                min_days, max_days = bucket_ranges[validity_bucket]
                # Convert days to seconds (validity.length is in seconds)
                min_seconds = min_days * 86400
                max_seconds = max_days * 86400
                
                # Use direct query on validity.length field (pre-computed in DB)
                # This is MUCH faster than date parsing aggregation
                query['parsed.validity.length'] = {
                    '$gte': min_seconds,
                    '$lt': max_seconds
                }
        
        # Handle has_vulnerabilities with OPTIMIZED query using boolean flag
        if has_vulnerabilities:
            # Use the zlint.errors_present boolean flag for fast indexed lookup
            # This is the same approach as Global Health / Active Certs - FAST
            vuln_query = {'zlint.errors_present': True}
            
            # Get total count - simple indexed query
            total = cls.collection.count_documents(vuln_query)
            
            # Get paginated results - simple find with skip/limit
            skip = (page - 1) * page_size
            cursor = cls.collection.find(vuln_query).skip(skip).limit(page_size)
            
            certificates = []
            for doc in cursor:
                cert = cls.serialize_certificate(doc)
                certificates.append(cert)
            
            return {
                'certificates': certificates,
                'pagination': {
                    'page': page,
                    'pageSize': page_size,
                    'total': total,
                    'totalPages': max(1, (total + page_size - 1) // page_size)
                }
            }
        
        # ⚡ OPTIMIZED: Handle country filter using pre-computed certificate IDs
        # PERFORMANCE: 110 seconds → 0.1 seconds (1,100x faster!)
        if country:
            print(f"[COUNTRY FILTER] Using pre-computed IDs for: {country}")
            try:
                # Get certificate IDs from pre-computed collection
                country_collection = MongoDBClient.get_results_db()['geographic-distribution-1']
                country_doc = country_collection.find_one({'_id': country})
                
                if not country_doc:
                    print(f"[COUNTRY FILTER] No pre-computed data for: {country}")
                    # Fall back to empty result
                    return {
                        'certificates': [],
                        'pagination': {
                            'page': page,
                            'pageSize': page_size,
                            'total': 0,
                            'totalPages': 0
                        }
                    }
                
                # Get all certificate IDs for this country
                cert_ids = country_doc.get('certificate_ids', [])
                total = country_doc.get('count', len(cert_ids))
                has_more = country_doc.get('has_more', total > len(cert_ids))
                
                print(f"[COUNTRY FILTER] Found {total} certificates for {country}")
                
                # Paginate certificate IDs
                skip = (page - 1) * page_size
                page_ids = cert_ids[skip:skip + page_size]
                
                docs_by_id = {
                    doc['_id']: doc
                    for doc in cls.collection.find({'_id': {'$in': page_ids}})
                }
                certificates = []
                for cert_id in page_ids:
                    doc = docs_by_id.get(cert_id)
                    if doc:
                        certificates.append(cls.serialize_certificate(doc))
                
                return {
                    'certificates': certificates,
                    'pagination': {
                        'page': page,
                        'pageSize': page_size,
                        'total': total,
                        'totalPages': max(1, (total + page_size - 1) // page_size),
                        'has_more': has_more and (skip + len(certificates) < min(total, len(cert_ids)))
                    }
                }
                
            except Exception as e:
                print(f"[COUNTRY FILTER] Error accessing pre-computed data: {e}")
                # Fall back to empty result rather than slow regex
                return {
                    'certificates': [],
                    'pagination': {
                        'page': page,
                        'pageSize': page_size,
                        'total': 0,
                        'totalPages': 0
                    }
                }
        
        # SAN TLD filter - filter certs where any dns_name ends with the TLD
        if san_tld:
            # Remove leading dot if present for regex
            tld_pattern = san_tld.lstrip('.')
            # Match dns_names ending with the TLD
            query['parsed.extensions.subject_alt_name.dns_names'] = {
                '$regex': f'\\.{tld_pattern}$',
                '$options': 'i'
            }
        
        # SAN type filter - filter by wildcard or standard SANs
        if san_type:
            if san_type.lower() == 'wildcard':
                # Match certs with at least one wildcard SAN (starts with *.)
                query['parsed.extensions.subject_alt_name.dns_names'] = {
                    '$regex': '^\\*\\.',
                    '$options': 'i'
                }
            elif san_type.lower() == 'standard':
                # Match certs where no SAN starts with *. 
                # This is trickier - we'll use $not to exclude wildcards
                query['$and'] = query.get('$and', [])
                query['$and'].append({
                    'parsed.extensions.subject_alt_name.dns_names': {
                        '$exists': True,
                        '$ne': []
                    }
                })
                query['$and'].append({
                    'parsed.extensions.subject_alt_name.dns_names': {
                        '$not': {'$regex': '^\\*\\.'}
                    }
                    
                    })
        
        # ⚡ OPTIMIZED: Shared key filter - use pre-computed materialized view
        # Previously this ran a 2-minute aggregation on every request
        if shared_key:
            try:
                # Get shared key fingerprints from pre-computed materialized view
                shared_groups_collection = MongoDBClient.get_results_db()['shared-keys-groups']
                
                # Get all shared key fingerprints (excluding metadata doc)
                shared_fingerprints = list(shared_groups_collection.find(
                    {'_id': {'$ne': 'metadata'}},
                    {'_id': 1}
                ))
                
                shared_fingerprints = [doc['_id'] for doc in shared_fingerprints]
            except Exception:
                # Fallback to original slow method if materialized view not available
                # (This should only happen if compute_shared_keys.py hasn't been run)
                shared_keys_pipeline = [
                    {'$match': {
                        'parsed.subject_key_info.fingerprint_sha256': {'$exists': True, '$ne': None},
                        'parsed.fingerprint_sha256': {'$exists': True, '$ne': None}
                    }},
                    {'$group': {
                        '_id': '$parsed.subject_key_info.fingerprint_sha256',
                        'cert_fingerprints': {'$addToSet': '$parsed.fingerprint_sha256'}
                    }},
                    {'$addFields': {
                        'distinct_certs': {'$size': '$cert_fingerprints'}
                    }},
                    {'$match': {'distinct_certs': {'$gt': 1}}},
                    {'$project': {'_id': 1}}
                ]
                
                shared_fingerprints = [r['_id'] for r in cls.collection.aggregate(shared_keys_pipeline, allowDiskUse=True)]
            
            if shared_fingerprints:
                # Filter certs to only those with shared public keys
                if '$and' not in query:
                    query['$and'] = []
                query['$and'].append({
                    'parsed.subject_key_info.fingerprint_sha256': {'$in': shared_fingerprints}
                })
            else:
                # No shared keys found, return empty result
                return {
                    'certificates': [],
                    'pagination': {
                        'page': page,
                        'pageSize': page_size,
                        'total': 0,
                        'totalPages': 0
                    }
                }
        
        # SAN count filter - filter by number of SANs (dns_names array size)
        if san_count_min is not None or san_count_max is not None:
            # Use aggregation pipeline for array size filtering
            pipeline = [
                {'$match': query if query else {}},
                # Add a field for the count of dns_names
                {'$addFields': {
                    'sanCount': {
                        '$size': {'$ifNull': ['$parsed.extensions.subject_alt_name.dns_names', []]}
                    }
                }},
            ]
            
            # Build match condition for san count
            san_count_match = {}
            if san_count_min is not None:
                san_count_match['$gte'] = san_count_min
            if san_count_max is not None:
                san_count_match['$lte'] = san_count_max
            
            if san_count_match:
                pipeline.append({'$match': {'sanCount': san_count_match}})
            
            # Get total count first
            count_pipeline = pipeline + [{'$count': 'total'}]
            count_result = list(cls.collection.aggregate(count_pipeline, allowDiskUse=True))
            total = count_result[0]['total'] if count_result else 0
            
            # Get paginated results
            skip = (page - 1) * page_size
            result_pipeline = pipeline + [
                {'$skip': skip},
                {'$limit': page_size}
            ]
            
            certificates = []
            for doc in cls.collection.aggregate(result_pipeline, allowDiskUse=True):
                cert = cls.serialize_certificate(doc)
                certificates.append(cert)
            
            return {
                'certificates': certificates,
                'pagination': {
                    'page': page,
                    'pageSize': page_size,
                    'total': total,
                    'totalPages': max(1, (total + page_size - 1) // page_size)
                }
            }
        
        # Get total count with filters applied
        # ✅ OPTIMIZATION: Use estimated_document_count() when query is empty (878K docs)
        if not query or query == {}:
            total = cls.collection.estimated_document_count()
        elif issuer and not search and issuer.lower() != 'others':
            # ULTRA-FAST: Get count from pre-computed CA analytics for exact issuer matches
            # This avoids expensive count operations on large result sets
            try:
                ca_analytics = MongoDBClient.get_results_db()['ca-analytics']
                ca_doc = ca_analytics.find_one({'name': issuer})
                print("before if condition")
                if ca_doc:
                    print("hello in if codition")
                    total = ca_doc['count']
                else:
                    print("hello in else codition")
                    # Fallback to aggregation count if not in pre-computed data
                    pipeline = [{'$match': query}, {'$count': 'total'}]
                    count_result = list(cls.collection.aggregate(pipeline))
                    total = count_result[0]['total'] if count_result else 0
            except Exception as e:
                # Fallback to standard count on error
                total = cls.collection.count_documents(query)
        else:
            total = cls.collection.count_documents(query)
        
        # Get paginated results
        # ✅ OPTIMIZATION: Sort by _id (indexed) for fast pagination
        # When using issuer filter, skip sort to avoid expensive in-memory sort operation
        skip = (page - 1) * page_size
        if search:
            # Prefix search: use indexed domain filter and stable _id sort.
            cursor = cls.collection.find(query).sort('_id', 1).skip(skip).limit(page_size)
        elif issuer:
            # Issuer filter: Return results in natural order to avoid expensive in-memory sort
            # MongoDB would have to sort 339K+ documents if we add sort here
            # Better to return results in natural order (insertion order)
            cursor = cls.collection.find(query).skip(skip).limit(page_size)
        else:
            # Regular query: Use hint to optimize with _id index
            cursor = cls.collection.find(query).sort('_id', 1).hint('_id_').skip(skip).limit(page_size)
        
        certificates = []
        for doc in cursor:
            cert = cls.serialize_certificate(doc)
            certificates.append(cert)
        
        return {
            'certificates': certificates,
            'pagination': {
                'page': page,
                'pageSize': page_size,
                'total': total,
                'totalPages': max(1, (total + page_size - 1) // page_size)
            }
        }    
    

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