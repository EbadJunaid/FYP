
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from .db import db, MongoDBClient

TLD_TO_COUNTRY = {
    'pk': 'Pakistan',
    'us': 'United States',
    'com': 'United States',
    'uk': 'United Kingdom',
    'co.uk': 'United Kingdom',
    'de': 'Germany',
    'fr': 'France',
    'jp': 'Japan',
    'ca': 'Canada',
    'au': 'Australia',
    'nl': 'Netherlands',
    'in': 'India',
    'cn': 'China',
    'br': 'Brazil',
    'kr': 'South Korea',
    'sg': 'Singapore',
    'ie': 'Ireland',
    'se': 'Sweden',
    'ch': 'Switzerland',
    'it': 'Italy',
    'es': 'Spain',
    'ru': 'Russia',
    'mx': 'Mexico',
    'za': 'South Africa',
    'nz': 'New Zealand',
    'org': 'International',
    'net': 'International',
    'io': 'International',
    'dev': 'International',
    'ebad': 'ebad',  # For testing unknown TLD handling
    'soy' : 'say' # For testing again 
}

class SharedModels:
    collection = db['certificates']

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
                'criticalVulnerabilities': {'count': 0, 'new': 0}
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
                'new': max(0, critical_vulns // 10)
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
    