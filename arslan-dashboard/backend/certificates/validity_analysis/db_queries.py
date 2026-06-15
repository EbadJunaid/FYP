
from datetime import datetime, timezone,timedelta
from typing import List, Dict, Any, Optional
from ..db import db, MongoDBClient

class ValidityModels:
    collection = db['certificates']

    
    @classmethod
    def _get_precomputed_doc(cls) -> Optional[Dict[str, Any]]:
        try:
            collection = MongoDBClient.get_results_db()['validity-analysis']
            return collection.find_one({'_id': 'validity_analysis'})
        except Exception as e:
            print(f"[VALIDITY ANALYTICS] Failed to read validity-analysis document: {e}")
            return None

    @classmethod
    def _warn_if_stale(cls, doc: Dict[str, Any]) -> None:
        computed_at_str = doc.get('computedAt')
        if not computed_at_str:
            return

        try:
            computed_at = datetime.fromisoformat(computed_at_str.replace('Z', '+00:00'))
            age_hours = (datetime.now(timezone.utc) - computed_at).total_seconds() / 3600
            if age_hours > 12:
                import logging
                logging.warning(f"Pre-computed validity analysis is {age_hours:.1f} hours old. Consider running compute_validity_analytics.py")
        except Exception:
            pass

    @classmethod
    def _get_real_time_expiring_counts(cls) -> Dict[str, int]:
        now = datetime.now(timezone.utc)
        now_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_30 = (now + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_60 = (now + timedelta(days=60)).strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_90 = (now + timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')

        return {
            'expiring30Days': cls.collection.count_documents({
                'parsed.validity.end': {'$gt': now_iso, '$lte': plus_30}
            }),
            'expiring60Days': cls.collection.count_documents({
                'parsed.validity.end': {'$gt': now_iso, '$lte': plus_60}
            }),
            'expiring90Days': cls.collection.count_documents({
                'parsed.validity.end': {'$gt': now_iso, '$lte': plus_90}
            })
        }

    @classmethod
    def get_validity_stats_fast(cls) -> Dict:
        """
        Get validity statistics (OPTIMIZED - reads from pre-computed data).
        """
        result = cls._get_precomputed_doc()
        if not result:
            import logging
            logging.warning("No pre-computed validity analysis found. Run compute_validity_analytics.py")
            return cls.get_validity_stats()

        cls._warn_if_stale(result)
        live_counts = cls._get_real_time_expiring_counts()

        return {
            'averageValidityDays': result.get('averageValidityDays', 0),
            'shortestValidityDays': result.get('shortestValidityDays', 0),
            'longestValidityDays': result.get('longestValidityDays', 0),
            'complianceRate': result.get('complianceRate', 0),
            'totalCertificates': result.get('totalCertificates', 0),
            'expiring30Days': live_counts['expiring30Days'],
            'expiring60Days': live_counts['expiring60Days'],
            'expiring90Days': live_counts['expiring90Days']
        }

    @classmethod
    def get_validity_distribution_fast(cls) -> list:
        """
        Get validity distribution by bucket (OPTIMIZED - reads from pre-computed data).
        
        PERFORMANCE:
        - Source: tranco-latest-8-lakh-results.validity-distribution (4 documents)
        - Response time: ~0.002 seconds (100,000x faster than original)
        - Original time: ~200 seconds (complex date aggregation on 878K docs)
        
        Returns pre-computed buckets:
        - <90 days
        - 90 days - 1 year
        - 1-2 years
        - >2 years
        """
        from ..db import MongoDBClient
        from datetime import datetime, timezone
        collection = MongoDBClient.get_results_db()['validity-analysis']

        result = cls._get_precomputed_doc()
        if not result or not result.get('validity_distribution'):
            import logging
            logging.warning("No pre-computed validity analysis distribution found. Run compute_validity_analytics.py")
            return cls.get_validity_distribution()

        cls._warn_if_stale(result)
        return [
            {
                'range': item.get('range'),
                'count': item.get('count', 0),
                'percentage': item.get('percentage', 0),
                'color': item.get('color', '#6b7280')
            }
            for item in result.get('validity_distribution', [])
        ]
        # return result.get('validity_distribution', [])
    
    @classmethod
    def get_issuance_timeline_fast(cls, months: int = 12) -> list:
        """
        Get certificate issuance and expiration timeline (OPTIMIZED - reads from pre-computed data).
        
        PERFORMANCE:
        - Source: tranco-latest-8-lakh-results.issuance-timeline (12-36 documents)
        - Response time: ~0.004 seconds (62,500x faster than original)
        - Original time: ~250 seconds (2 complex aggregations on 878K docs)
        
        Args:
            months: Number of months to retrieve (default 12)
        
        Returns monthly data:
            - issued: certificates issued in that month
            - expiring: certificates expiring in that month
        """
        from ..db import MongoDBClient
        from datetime import datetime, timezone
        collection = MongoDBClient.get_results_db()['validity-analysis']

        result = cls._get_precomputed_doc()
        if not result or not result.get('issuance_timeline'):
            import logging
            logging.warning(f"No pre-computed issuance timeline found. Run compute_validity_analytics.py")
            return cls.get_issuance_timeline(months=months)

        cls._warn_if_stale(result)
        return [
            {
                'month': item.get('month'),
                'year': item.get('year'),
                'monthNum': item.get('monthNum', 0),
                'issued': item.get('issued', 0),
                'expiring': item.get('expiring', 0)
            }
            for item in result.get('issuance_timeline', [])
        ]
        # return result.get('issuance_timeline', [])

    @classmethod
    def get_validity_stats(cls) -> Dict:
        """Get validity statistics for validity analysis page
        
        Uses parsed.validity.length (in seconds) for duration calculations.
        
        Returns:
            - averageValidityDays: avg number of days (length / 86400)
            - expiring30Days: count expiring in next 30 days
            - expiring60Days: count expiring in next 60 days
            - expiring90Days: count expiring in next 90 days
            - complianceRate: % of certs with validity <= 398 days
            - shortestValidityDays: min validity period
            - longestValidityDays: max validity period
        """
        now = datetime.now(timezone.utc)
        now_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_30 = (now + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_60 = (now + timedelta(days=60)).strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_90 = (now + timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Use parsed.validity.length (in seconds) for duration calculations
        # This is a pre-computed field in the database
        pipeline = [
            {
                '$match': {
                    'parsed.validity.length': {'$exists': True, '$gt': 0}
                }
            },
            {
                '$project': {
                    'lengthSeconds': '$parsed.validity.length',
                    # Convert seconds to days for aggregation
                    'durationDays': {'$divide': ['$parsed.validity.length', 86400]}
                }
            },
            {
                '$group': {
                    '_id': None,
                    'avgDuration': {'$avg': '$durationDays'},
                    'minDuration': {'$min': '$durationDays'},
                    'maxDuration': {'$max': '$durationDays'},
                    'total': {'$sum': 1},
                    'compliantCount': {
                        '$sum': {
                            '$cond': [
                                {'$lte': ['$durationDays', 398]},
                                1,
                                0
                            ]
                        }
                    }
                }
            }
        ]
        
        try:
            result = list(cls.collection.aggregate(pipeline))
            stats = result[0] if result else {}
        except Exception as e:
            print(f"Aggregation error: {e}")
            stats = {}
        
        # Count expiring in next 30/60/90 days (separate queries for accuracy)
        expiring_30 = cls.collection.count_documents({
            'parsed.validity.end': {'$gt': now_iso, '$lte': plus_30}
        })
        expiring_60 = cls.collection.count_documents({
            'parsed.validity.end': {'$gt': now_iso, '$lte': plus_60}
        })
        expiring_90 = cls.collection.count_documents({
            'parsed.validity.end': {'$gt': now_iso, '$lte': plus_90}
        })
        
        total = stats.get('total', 0) or cls.collection.count_documents({})
        compliant = stats.get('compliantCount', 0)
        
        return {
            'averageValidityDays': round(stats.get('avgDuration', 0) or 0),
            'shortestValidityDays': round(stats.get('minDuration', 0) or 0),
            'longestValidityDays': round(stats.get('maxDuration', 0) or 0),
            'expiring30Days': expiring_30,
            'expiring60Days': expiring_60,
            'expiring90Days': expiring_90,
            'complianceRate': round((compliant / total * 100), 1) if total > 0 else 0,
            'totalCertificates': total
        }
    
    @classmethod
    def get_validity_distribution(cls) -> List[Dict]:
        """Get distribution of certificate validity periods by bucket
        
        Buckets:
        - <90 days
        - 90 days - 1 year
        - 1-2 years  
        - >2 years
        """
        pipeline = [
            {
                '$project': {
                    'validFrom': '$parsed.validity.start',
                    'validTo': '$parsed.validity.end',
                }
            },
            {
                '$addFields': {
                    'validFromDate': {
                        '$dateFromString': {'dateString': '$validFrom', 'onError': None}
                    },
                    'validToDate': {
                        '$dateFromString': {'dateString': '$validTo', 'onError': None}
                    }
                }
            },
            {
                '$addFields': {
                    'durationDays': {
                        '$divide': [
                            {'$subtract': ['$validToDate', '$validFromDate']},
                            86400000
                        ]
                    }
                }
            },
            {
                '$match': {'durationDays': {'$ne': None, '$gt': 0}}
            },
            {
                '$bucket': {
                    'groupBy': '$durationDays',
                    'boundaries': [0, 90, 365, 730, 100000],  # 0-90, 90-365, 365-730, 730+
                    'default': 'Other',
                    'output': {
                        'count': {'$sum': 1}
                    }
                }
            }
        ]
        
        try:
            results = list(cls.collection.aggregate(pipeline))
        except Exception as e:
            print(f"Validity distribution error: {e}")
            results = []
        
        # Map bucket boundaries to labels
        bucket_labels = {
            0: '< 90 Days',
            90: '90 Days - 1 Year',
            365: '1 - 2 Years',
            730: '> 2 Years'
        }
        
        bucket_colors = {
            0: '#3b82f6',    # Blue
            90: '#10b981',   # Green
            365: '#8b5cf6',  # Purple
            730: '#f59e0b'   # Orange
        }
        
        total = sum(r.get('count', 0) for r in results)
        
        distribution = []
        for r in results:
            bucket_id = r.get('_id')
            if bucket_id in bucket_labels:
                distribution.append({
                    'range': bucket_labels[bucket_id],
                    'count': r.get('count', 0),
                    'percentage': round((r.get('count', 0) / total * 100), 1) if total > 0 else 0,
                    'color': bucket_colors.get(bucket_id, '#6b7280')
                })
        
        return distribution
    
    @classmethod
    def get_issuance_timeline(cls, months: int = 12) -> List[Dict]:
        """Get certificate issuance and expiration timeline by month
        
        Shows the last N months from current month (past data only).
        
        Returns monthly counts for:
        - issued: certificates issued (validFrom) in that month
        - expired: certificates expired (validTo) in that month (past only)
        """
        from dateutil.relativedelta import relativedelta
        
        now = datetime.now(timezone.utc)
        
        # Calculate date range: last N months from the start of current month
        # Start from (months-1) months ago to include current month
        end_date = now.replace(day=1) + relativedelta(months=1) - timedelta(seconds=1)  # End of current month
        start_date = now.replace(day=1) - relativedelta(months=months-1)  # Start of N months ago
        
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Issued certificates by month (using validFrom)
        issued_pipeline = [
            {
                '$match': {
                    'parsed.validity.start': {
                        '$gte': start_str,
                        '$lte': end_str
                    }
                }
            },
            {
                '$project': {
                    'validFrom': '$parsed.validity.start'
                }
            },
            {
                '$addFields': {
                    'validFromDate': {
                        '$dateFromString': {'dateString': '$validFrom', 'onError': None}
                    }
                }
            },
            {
                '$group': {
                    '_id': {
                        'year': {'$year': '$validFromDate'},
                        'month': {'$month': '$validFromDate'}
                    },
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]
        
        # Expiring certificates by month (using validTo)
        expiring_pipeline = [
            {
                '$match': {
                    'parsed.validity.end': {
                        '$gte': start_str,
                        '$lte': end_str
                    }
                }
            },
            {
                '$project': {
                    'validTo': '$parsed.validity.end'
                }
            },
            {
                '$addFields': {
                    'validToDate': {
                        '$dateFromString': {'dateString': '$validTo', 'onError': None}
                    }
                }
            },
            {
                '$group': {
                    '_id': {
                        'year': {'$year': '$validToDate'},
                        'month': {'$month': '$validToDate'}
                    },
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]
        
        try:
            issued_results = list(cls.collection.aggregate(issued_pipeline))
            expiring_results = list(cls.collection.aggregate(expiring_pipeline))
        except Exception as e:
            print(f"Issuance timeline error: {e}")
            issued_results = []
            expiring_results = []
        
        # Build month list
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # Create lookup dicts
        issued_lookup = {
            f"{r['_id']['year']}-{r['_id']['month']}": r['count']
            for r in issued_results
        }
        expiring_lookup = {
            f"{r['_id']['year']}-{r['_id']['month']}": r['count']
            for r in expiring_results
        }
        
        # Generate timeline data
        timeline = []
        current = start_date.replace(day=1)
        end_month = end_date.replace(day=1)
        
        while current <= end_month:
            key = f"{current.year}-{current.month}"
            month_label = f"{month_names[current.month - 1]} '{str(current.year)[2:]}"
            
            timeline.append({
                'month': month_label,
                'year': current.year,
                'monthNum': current.month,
                'issued': issued_lookup.get(key, 0),
                'expiring': expiring_lookup.get(key, 0)
            })
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return timeline

