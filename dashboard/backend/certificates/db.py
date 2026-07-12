# backend/certificates/db.py
import json
import re
from pathlib import Path

from pymongo import MongoClient
from django.conf import settings

# ============================================================================
# DATABASE CONFIGURATION - CHANGE HERE TO SWITCH DATABASES
# ============================================================================
# To use main database (878k certificates):
#     MAIN_DB = 'tranco-latest-8-lakh'
#     RESULTS_DB = 'tranco-latest-8-lakh-results'
#
# To use Pakistani domains (7,724 certificates):
#     MAIN_DB = 'pakistani-domains'
#     RESULTS_DB = 'pakistani-domains-results'
# ============================================================================

# Global variables for current database (can be changed at runtime)
# _CURRENT_MAIN_DB = 'tranco-latest-8-lakh'
# _CURRENT_RESULTS_DB = 'tranco-latest-8-lakh-results'
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "project-config.json"
with open(_CONFIG_PATH) as _f:
    _CONFIG_DATA = json.load(_f)["databases"][0]
_BASE_MAIN_DB = _CONFIG_DATA["main"]
_BASE_RESULTS_DB = _CONFIG_DATA["results"]

_CURRENT_MAIN_DB = _BASE_MAIN_DB
_CURRENT_RESULTS_DB = _BASE_RESULTS_DB
_CURRENT_SCOPE = 'all'
MAIN_DB = _CURRENT_MAIN_DB
RESULTS_DB = _CURRENT_RESULTS_DB

# Logical scope options.
#
# To add countries/scopes everywhere in the dashboard, edit only:
#     backend/certificates/Scopes.json
#
# Add one compact entry there, for example:
#     "jp": "Japan"
#
# The frontend dropdown reads these options from /api/databases/available/,
# and every API request uses the selected scope with the single physical DB pair above.
SCOPES_FILE = Path(__file__).with_name('Scopes.json')
LEGACY_SCOPE_IDS = {
    'pk': 'pakistani',
    'in': 'indian',
    'us': 'united-states',
}


def _slugify_scope_id(name):
    slug = re.sub(r'[^a-z0-9]+', '-', name.strip().lower()).strip('-')
    return slug or 'scope'


def _load_scope_config():
    fallback = {
        'all': {
            'id': 'global',
            'name': 'Global',
            'description': 'All certificates',
        },
        'countries': {
            'pk': 'Pakistan',
            'in': 'India',
            'us': 'United States',
        },
    }
    try:
        with SCOPES_FILE.open('r', encoding='utf-8') as scopes_file:
            loaded = json.load(scopes_file)
            return loaded if isinstance(loaded, dict) else fallback
    except (OSError, json.JSONDecodeError):
        return fallback


def _build_scope_options():
    scope_config = _load_scope_config()
    all_config = scope_config.get('all') or {}
    options = [
        {
            'id': all_config.get('id', 'global'),
            'scope': 'all',
            'name': all_config.get('name', 'Global'),
            'description': all_config.get('description', 'All certificates'),
        }
    ]

    countries = scope_config.get('countries') or {}
    for scope, country in sorted(countries.items()):
        scope_code = str(scope).strip().lower()
        if not scope_code or scope_code == 'all':
            continue

        if isinstance(country, dict):
            country_name = country.get('name') or scope_code.upper()
            scope_id = country.get('id') or LEGACY_SCOPE_IDS.get(scope_code) or _slugify_scope_id(country_name)
            display_name = country.get('display_name') or f'{country_name} Domains'
            description = country.get('description') or f'{country_name} scope'
        else:
            country_name = str(country).strip() or scope_code.upper()
            scope_id = LEGACY_SCOPE_IDS.get(scope_code) or _slugify_scope_id(country_name)
            display_name = f'{country_name} Domains'
            description = f'{country_name} scope'

        options.append({
            'id': scope_id,
            'scope': scope_code,
            'name': display_name,
            'description': description,
        })

    return options


SCOPE_OPTIONS = _build_scope_options()

# Available logical databases configuration
# AVAILABLE_DATABASES = {
#     'global': {
#         'main': 'tranco-latest-8-lakh',
#         'results': 'tranco-latest-8-lakh-results',
#         'name': 'Global',
#         'description': '878k certificates'
#     },
#     'pakistani': {
#         'main': 'pakistani-domains',
#         'results': 'pakistani-domains-results',
#         'name': 'Pakistani Domains',
#         'description': '7,724 certificates'
#     }
# }
AVAILABLE_DATABASES = {
    option['id']: {
        'main': _BASE_MAIN_DB,
        'results': _BASE_RESULTS_DB,
        **option,
    }
    for option in SCOPE_OPTIONS
}
# ============================================================================

class ScopedCollection:
    """Small wrapper that applies the active logical scope to live certificate reads."""

    def __init__(self, collection):
        self._collection = collection

    def _scope_filter(self):
        return MongoDBClient.get_live_scope_filter()

    def _merge_query(self, query=None):
        query = query or {}
        scope_filter = self._scope_filter()
        if not scope_filter:
            return query
        if not query:
            return scope_filter
        return {'$and': [query, scope_filter]}

    def find(self, filter=None, *args, **kwargs):
        return self._collection.find(self._merge_query(filter), *args, **kwargs)

    def find_one(self, filter=None, *args, **kwargs):
        return self._collection.find_one(self._merge_query(filter), *args, **kwargs)

    def count_documents(self, filter, *args, **kwargs):
        return self._collection.count_documents(self._merge_query(filter), *args, **kwargs)

    def estimated_document_count(self, *args, **kwargs):
        scope_filter = self._scope_filter()
        if scope_filter:
            return self._collection.count_documents(scope_filter)
        return self._collection.estimated_document_count(*args, **kwargs)

    def aggregate(self, pipeline, *args, **kwargs):
        scope_filter = self._scope_filter()
        scoped_pipeline = list(pipeline)
        if scope_filter:
            scoped_pipeline = [{'$match': scope_filter}] + scoped_pipeline
        return self._collection.aggregate(scoped_pipeline, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._collection, name)


# MongoDB Connection Singleton with Multiple Database Support
class MongoDBClient:
    _client = None
    _current_db_id = 'global'  # Track current database ID

    @classmethod
    def get_client(cls):
        """Get MongoDB client instance (singleton)"""
        if cls._client is None:
            # Connect to MongoDB server once
            cls._client = MongoClient("mongodb://localhost:27017/")
        return cls._client
    
    @classmethod
    def get_db(cls, database_name=None):
        """
        Get specific database from MongoDB server
        
        Args:
            database_name: Name of the database to access (defaults to current MAIN_DB)
            
        Returns:
            MongoDB database instance
        """
        global _CURRENT_MAIN_DB
        if database_name is None:
            database_name = _CURRENT_MAIN_DB
        client = cls.get_client()
        return client[database_name]
    
    @classmethod
    def switch_database(cls, db_id: str):
        """
        Switch to a different database configuration
        
        Args:
            db_id: Database ID from AVAILABLE_DATABASES (for example 'global' or 'pakistani')
            
        Returns:
            bool: True if successful, False otherwise
        """
        global _CURRENT_MAIN_DB, _CURRENT_RESULTS_DB, _CURRENT_SCOPE, db, results_db
        
        if db_id not in AVAILABLE_DATABASES:
            return False
        
        # Keep one physical database pair and switch only the logical scope.
        _CURRENT_MAIN_DB = _BASE_MAIN_DB
        _CURRENT_RESULTS_DB = _BASE_RESULTS_DB
        _CURRENT_SCOPE = AVAILABLE_DATABASES[db_id].get('scope', 'all')
        
        # Update class variable
        cls._current_db_id = db_id
        
        # Reinitialize database connections
        import certificates.db as db_module
        db_module.db = cls.get_db(_CURRENT_MAIN_DB)
        db_module.results_db = cls.get_db(_CURRENT_RESULTS_DB)
        
        # Update models to use new database
        from certificates.ca_analytics.db_queries import CAModel
        from certificates.signature_hash.db_queries import SignatureHashModel
        from certificates.san_analytics.db_queries import SANModel
        from certificates.overview.db_queries import OverviewModels
        from certificates.shared_keys.db_queries import SharedKeyModel
        from certificates.trends.db_queries import TrendsModel
        from certificates.validity_analysis.db_queries import ValidityModels
        from certificates.shared_apis.db_queries import SharedModels

        from certificates.models import CertificateModel

        cert_collection = cls.get_certificates_collection()
        CertificateModel.collection = cert_collection
        SharedModels.collection = cert_collection
        ValidityModels.collection = cert_collection
        CAModel.collection = cert_collection
        SignatureHashModel.collection = cert_collection
        TrendsModel.collection = cert_collection
        SANModel.collection = cert_collection
        OverviewModels.collection = cert_collection
        SharedKeyModel.collection = cert_collection
        # Clear all caches when switching databases
        try:
            from certificates.cache_service import cache
            cache.clear_all()
        except ImportError:
            pass  # Cache service not available
        
        return True
    
    @classmethod
    def get_current_database(cls):
        """
        Get current database configuration
        
        Returns:
            dict: Current database info
        """
        # print(cls._current_db_id)
        return {
            'id': cls._current_db_id,
            'main_db': _CURRENT_MAIN_DB,
            'results_db': _CURRENT_RESULTS_DB,
            'scope': _CURRENT_SCOPE,
            **AVAILABLE_DATABASES.get(cls._current_db_id, {})
        }

    @classmethod
    def normalize_scope(cls, scope):
        normalized = (scope or 'all').strip().lower()
        if normalized in ('', 'all', 'global', 'none', 'default'):
            return 'all'
        for db_id, config in AVAILABLE_DATABASES.items():
            if normalized == db_id.lower():
                return config.get('scope', normalized)
        return normalized

    @classmethod
    def set_current_scope(cls, scope):
        global _CURRENT_SCOPE
        normalized_scope = cls.normalize_scope(scope)
        if normalized_scope == _CURRENT_SCOPE:
            return
        _CURRENT_SCOPE = normalized_scope
        matching_db = next(
            (
                db_id
                for db_id, config in AVAILABLE_DATABASES.items()
                if config.get('scope', 'all') == _CURRENT_SCOPE
            ),
            None,
        )
        if matching_db:
            cls._current_db_id = matching_db
        cls.refresh_model_collections()

    @classmethod
    def refresh_model_collections(cls):
        """Point all model collection handles at the scoped certificates wrapper."""
        try:
            import certificates.db as db_module
            cert_collection = cls.get_certificates_collection()

            from certificates.ca_analytics.db_queries import CAModel
            from certificates.signature_hash.db_queries import SignatureHashModel
            from certificates.san_analytics.db_queries import SANModel
            from certificates.overview.db_queries import OverviewModels
            from certificates.shared_keys.db_queries import SharedKeyModel
            from certificates.trends.db_queries import TrendsModel
            from certificates.validity_analysis.db_queries import ValidityModels
            from certificates.shared_apis.db_queries import SharedModels
            from certificates.models import CertificateModel

            CertificateModel.collection = cert_collection
            SharedModels.collection = cert_collection
            ValidityModels.collection = cert_collection
            CAModel.collection = cert_collection
            SignatureHashModel.collection = cert_collection
            TrendsModel.collection = cert_collection
            SANModel.collection = cert_collection
            OverviewModels.collection = cert_collection
            SharedKeyModel.collection = cert_collection
            db_module.results_db = cls.get_db(_CURRENT_RESULTS_DB)
        except Exception:
            pass

    @classmethod
    def get_current_scope(cls):
        return _CURRENT_SCOPE or 'all'

    @classmethod
    def get_precomputed_scope(cls):
        return 'all' if cls.get_current_scope() in ('', 'all', 'global') else cls.get_current_scope()

    @classmethod
    def get_precomputed_scope_filter(cls):
        scope = cls.get_precomputed_scope()
        if scope == 'all':
            return {'$or': [{'scope': 'all'}, {'scope': {'$exists': False}}]}
        return {'scope': scope}

    @classmethod
    def get_live_scope_filter(cls):
        scope = cls.get_current_scope()
        if scope in ('', 'all', 'global'):
            return {}
        return {'scope': scope}
    
    @classmethod
    def get_available_databases(cls):
        """
        Get list of all available databases
        
        Returns:
            dict: Available databases configuration
        """
        return AVAILABLE_DATABASES
    
    @classmethod
    def get_results_db(cls):
        """
        Get current results database (for precomputed data).
        Always returns the currently active results database.
        
        Returns:
            MongoDB database instance for results
        """
        global _CURRENT_RESULTS_DB
        return cls.get_db(_CURRENT_RESULTS_DB)

    @classmethod
    def get_certificates_collection(cls):
        return ScopedCollection(cls.get_db(_CURRENT_MAIN_DB)['certificates'])

    @classmethod
    def find_scoped_result_doc(cls, collection_name: str, fallback_id=None):
        collection = cls.get_results_db()[collection_name]
        scope = cls.get_precomputed_scope()
        doc = collection.find_one({'scope': scope})
        if doc:
            return doc
        if scope == 'all' and fallback_id is not None:
            return collection.find_one({'_id': fallback_id})
        return None


# Default database (main certificates collection)
db = MongoDBClient.get_db(_CURRENT_MAIN_DB)

# Results database (pre-computed analytics)
results_db = MongoDBClient.get_db(_CURRENT_RESULTS_DB)
