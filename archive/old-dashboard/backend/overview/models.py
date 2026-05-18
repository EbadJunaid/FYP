from datetime import datetime, timedelta, timezone
from collections import OrderedDict
from SSL_Dashboard.filter_query import Filter
from SSL_Dashboard.db_config import DBConnection

class OverviewDataService:
    def __init__(self, db_connection=None):
        self.flt = Filter()
        if db_connection is None:
            db_connection = DBConnection()
        self.certs = db_connection.get_collection("certificates")

    # Low-level methods that now expect filter_query dict
    def get_total_certificates(self, filter_query):
        return self.certs.count_documents(filter_query)
    
    def get_all_certificates(self, filter_query):
        return self.certs.count_documents(filter_query)

    def get_active_certificates(self, filter_query):
        # Add/override status filter just for active
        fq = dict(filter_query)  # shallow copy
        fq.pop("parsed.validity.end", None)
        fq = self.flt.filter_status("active", fq)
        return self.certs.count_documents(fq)

    def get_expired_certificates(self, filter_query):
        fq = dict(filter_query)
        fq.pop("parsed.validity.end", None)
        fq = self.flt.filter_status("expired", fq)
        return self.certs.count_documents(fq)

    def get_expiring_soon(self, filter_query):
        fq = dict(filter_query)
        fq.pop("parsed.validity.end", None)
        fq = self.flt.filter_status("expiring_soon", fq)
        return self.certs.count_documents(fq)

    def get_unique_domains_count(self, filter_query):
        return len(self.certs.distinct("parsed.subject.common_name.0", filter_query))

    def get_unique_issuers_count(self, filter_query):
        return len(self.certs.distinct("parsed.issuer.organization.0", filter_query))

    def get_signature_algorithm_counts(self, filter_query):
        match_stage = {"$match": filter_query} if filter_query else {}
        pipeline = []
        if match_stage:
            pipeline.append(match_stage)
        pipeline.append({"$group": {
            "_id": "$parsed.signature_algorithm.name",
            "count": {"$sum": 1}
        }})
        results = list(self.certs.aggregate(pipeline))
        return {item["_id"]: item["count"] for item in results if item["_id"] is not None}

    def get_total_warnings(self, filter_query):
        fq = dict(filter_query)
        fq["zlint.warnings_present"]=True
        return self.certs.count_documents(fq)
        

    def get_total_errors(self, filter_query):
        fq = dict(filter_query)
        fq["zlint.errors_present"]=True
        return self.certs.count_documents(fq)
    
    def get_total_fatals(self, filter_query):
        fq = dict(filter_query)
        fq["zlint.fatals_present"]=True
        return self.certs.count_documents(fq)
        
        
    # Main summary method: builds filter ONCE, passes everywhere
    def get_summary(self, **kwargs):
        status = kwargs.get("status")
        filter_query = self.flt._build_base_filter(**kwargs)
        if status == "expired":
            active_count = 0
            expiring_soon_count = 0
            expired_count = self.get_expired_certificates(filter_query)
        elif status == "active":
            active_count = self.get_active_certificates(filter_query)
            expired_count = 0
            expiring_soon_count = 0

        elif status == "expiring_soon":
            active_count=0
            expired_count=0
            expiring_soon_count=self.get_expiring_soon(filter_query)
        else:
            active_count = self.get_active_certificates(filter_query)
            expired_count = self.get_expired_certificates(filter_query)
            expiring_soon_count=self.get_expiring_soon(filter_query)

        return {
            "total_certificates": self.get_total_certificates(filter_query),
            "active_certificates": active_count,
            "expired_certificates": expired_count,
            "expiring_soon": expiring_soon_count,
            "unique_domains_count": self.get_unique_domains_count(filter_query),
            "unique_issuers_count": self.get_unique_issuers_count(filter_query),
            "signature_algorithm_counts": self.get_signature_algorithm_counts(filter_query),
            "warnings":self.get_total_warnings(filter_query),
            "errors":self.get_total_errors(filter_query),
            "fatals":self.get_total_fatals(filter_query),
        }


    def get_trends(self, months_to_show=12, **kwargs):
        # Build filter just once
        base_filter = self.flt._build_base_filter(**kwargs)
        now = datetime.now(timezone.utc)
        this_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        month_list = [(this_month - timedelta(days=30 * i)).replace(day=1) for i in reversed(range(months_to_show))]
        month_labels = [self.flt.date.month_key(m) for m in month_list]
        trend_data = OrderedDict()
        for label, month_start in zip(month_labels, month_list):
            month_end = self.flt.date._end_of_month(month_start)
            month_start_iso = month_start.isoformat().replace("+00:00", "Z")
            month_end_iso = month_end.isoformat().replace("+00:00", "Z")

            # Copy base filter for each time window
            filter_issued = dict(base_filter)
            filter_active = dict(base_filter)
            filter_expired = dict(base_filter)
            filter_exp_soon = dict(base_filter)

            filter_issued["parsed.validity.start"] = {"$gte": month_start_iso, "$lt": month_end_iso}
            filter_active["parsed.validity.start"] = {"$lt": month_end_iso}
            filter_active["parsed.validity.end"] = {"$gte": month_start_iso}
            filter_expired["parsed.validity.end"] = {"$gte": month_start_iso, "$lt": month_end_iso}

            soon_start_iso = month_start_iso
            soon_end_iso = (month_start + timedelta(days=30)).isoformat().replace("+00:00", "Z")
            filter_exp_soon["parsed.validity.end"] = {"$gte": soon_start_iso, "$lt": soon_end_iso}

            issued_count = self.certs.count_documents(filter_issued)
            active_count = self.certs.count_documents(filter_active)
            expired_count = self.certs.count_documents(filter_expired)
            expiring_soon_count = self.certs.count_documents(filter_exp_soon)

            trend_data[label] = {
                "issued": issued_count,
                "active": active_count,
                "expired": expired_count,
                "expiring_soon": expiring_soon_count,
            }
        issued_list = [trend_data[key]["issued"] for key in month_labels]
        active_list = [trend_data[key]["active"] for key in month_labels]
        expired_list = [trend_data[key]["expired"] for key in month_labels]
        soon_list = [trend_data[key]["expiring_soon"] for key in month_labels]
        return {
            "labels": month_labels,
            "issued": issued_list,
            "active": active_list,
            "expired": expired_list,
            "expiring_soon": soon_list,
        }

class CertificateDetailService:
    """
    Handles paginated, structured, and filtered retrieval
    of certificate details.
    """

    def __init__(self, db_connection=None):
        self.flt = Filter()
        if db_connection is None:
            db_connection = DBConnection()
        self.certs = db_connection.get_collection("certificates")

    def _extract_certificate_fields(self, cert):
        """
        Extract only important structured fields from each certificate.
        Returns a clean and frontend-ready dictionary.
        """

        subject = cert.get("parsed", {}).get("subject", {})
        issuer = cert.get("parsed", {}).get("issuer", {})
        validity = cert.get("parsed", {}).get("validity", {})
        signature_algo = cert.get("parsed", {}).get("signature_algorithm", {})
        public_key = cert.get("parsed", {}).get("public_key", {})

        # Domain
        # domain = subject.get("common_name", [None])[0]
        domain=cert.get("domain",{})

        # Country (either in subject or issuer)
        country = subject.get("country", [None])
        country = country[0] if isinstance(country, list) else country

        # Validity dates
        valid_from = validity.get("start")
        valid_to = validity.get("end")

        # Determine status
        now_utc = datetime.now(timezone.utc)
        status = "active"
        if valid_to:
            try:
                expiry_dt = datetime.fromisoformat(valid_to.replace("Z", "+00:00"))
                if expiry_dt < now_utc:
                    status = "expired"
                elif (expiry_dt - now_utc).days <= 30:
                    status = "expiring_soon"
            except Exception:
                status = "unknown"

        return {
            "id": str(cert.get("_id")),
            "domain": domain,
            "status": status,
            "issuer": {
                "organization": issuer.get("organization", [None])[0],
                "country": issuer.get("country", [None])[0],
                "state": issuer.get("state_or_province", [None])[0],
                "locality": issuer.get("locality", [None])[0],
                "organizational_unit": issuer.get("organizational_unit", [None])[0],
                "common_name": issuer.get("common_name", [None])[0]
            },
            "validity": {
                "valid_from": valid_from,
                "valid_to": valid_to,
            },
            "country": country,
            "algorithm": signature_algo.get("name"),
            "public_key": {
                "type": public_key.get("type"),
                "bits": public_key.get("bit_size"),
                "fingerprint_sha256": cert.get("parsed", {}).get("fingerprints", {}).get("sha256"),
            }
        }

    def get_certificates(self, page: int = 1, page_size: int = 20, **kwargs):
        """
        Fetch paginated certificate details based on applied filters.
        Only returns clean structured fields.
        """

        # Ensure valid page values
        page = max(page, 1)
        page_size = max(min(page_size, 200), 1)

        # Build filter
        filter_query = self.flt._build_base_filter(**kwargs)
        
        total = self.certs.count_documents(filter_query)
        skip_count = (page - 1) * page_size

        cursor = (
            self.certs.find(filter_query)
            .skip(skip_count)
            .limit(page_size)
            .sort("parsed.validity.end", -1)
        )

        raw_certificates = list(cursor)

        # Convert each certificate into structured output
        structured = [self._extract_certificate_fields(cert) for cert in raw_certificates]

        return {
            "page": page,
            "page_size": page_size,
            "total_records": total,
            "total_pages": (total + page_size - 1) // page_size,
            "results": structured,
        }

    def _extract_certificate_warnings(self, cert):
        """
        Extract all zlint warnings from a certificate.
        Keep only lint entries where result == 'warn'.
        """

        warnings = []

        lints = cert.get("zlint", {}).get("lints", {})

        if isinstance(lints, dict):
            for lint_name, lint_info in lints.items():
                result = lint_info.get("result")

                if result == "warn":  # we only collect warnings
                    warnings.append({
                        "lint_name": lint_name,
                        "result": result,
                        "details": {k: v for k, v in lint_info.items() if k != "result"}
                    })

        return {
            "id": str(cert.get("_id")),
            "domain": cert.get("domain"),
            "warnings": warnings
        }


    def get_certificate_warnings(self, page: int = 1, page_size: int = 20, **kwargs):
        """
        Fetch certificates that contain at least one zlint warning.
        Pagination is applied AFTER filtering out non-warning certificates.
        """

        # Validate page limits
        page = max(page, 1)
        page_size = max(min(page_size, 200), 1)

        # Build filter query
        filter_query = self.flt._build_base_filter(**kwargs)

        # Get all certificates matching filters (no pagination yet)
        cursor = self.certs.find(filter_query).sort("parsed.validity.end", -1)
        raw_certificates = list(cursor)

        # Extract warnings + keep only certs that actually contain warnings
        warning_certs = []
        for cert in raw_certificates:
            extracted = self._extract_certificate_warnings(cert)
            if extracted["warnings"]:  # keep only those with warnings
                warning_certs.append(extracted)

        # Total warning count
        total = len(warning_certs)

        # Now apply pagination
        start = (page - 1) * page_size
        end = start + page_size
        paginated = warning_certs[start:end]

        return {
            "page": page,
            "page_size": page_size,
            "total_records": total,
            "total_pages": (total + page_size - 1) // page_size,
            "results": paginated,
        }


