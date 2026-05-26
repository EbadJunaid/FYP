# backend/certificates/db.py
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
_CURRENT_MAIN_DB = 'tranco-latest-8-lakh'
_CURRENT_RESULTS_DB = 'tranco-latest-8-lakh-results'
# _CURRENT_MAIN_DB = 'test-api-tranco'
# _CURRENT_RESULTS_DB = 'test-api-tranco-results'
MAIN_DB = _CURRENT_MAIN_DB
RESULTS_DB = _CURRENT_RESULTS_DB

# Available databases configuration
AVAILABLE_DATABASES = {
    'global': {
        'main': 'tranco-latest-8-lakh',
        'results': 'tranco-latest-8-lakh-results',
        'name': 'Global',
        'description': '878k certificates'
    },
    'pakistani': {
        'main': 'pakistani-domains',
        'results': 'pakistani-domains-results',
        'name': 'Pakistani Domains',
        'description': '7,724 certificates'
    }
}
# AVAILABLE_DATABASES = {
#     'global': {
#         'main': 'test-api-tranco',
#         'results': 'test-api-tranco-results',
#         'name': 'Global',
#         'description': '878k certificates'
#     },
#     'pakistani': {
#         'main': 'test-api-pakistani',
#         'results': 'test-api-pakistani-results',
#         'name': 'Pakistani Domains',
#         'description': '7,724 certificates'
#     }
# }
# ============================================================================

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
            db_id: Database ID from AVAILABLE_DATABASES ('global' or 'pakistani')
            
        Returns:
            bool: True if successful, False otherwise
        """
        global _CURRENT_MAIN_DB, _CURRENT_RESULTS_DB, db, results_db
        
        if db_id not in AVAILABLE_DATABASES:
            return False
        
        # Update global database references
        _CURRENT_MAIN_DB = AVAILABLE_DATABASES[db_id]['main']
        _CURRENT_RESULTS_DB = AVAILABLE_DATABASES[db_id]['results']
        
        # Update class variable
        cls._current_db_id = db_id
        
        # Reinitialize database connections
        import certificates.db as db_module
        db_module.db = cls.get_db(_CURRENT_MAIN_DB)
        db_module.results_db = cls.get_db(_CURRENT_RESULTS_DB)
        
        # Update models to use new database
        from certificates.models import CertificateModel
        from certificates.shared_models import SharedModels
        from certificates.validity_models import ValidityModels
        from certificates.ca_models import CAModel
        from certificates.signature_hash_models import SignatureHashModel
        from certificates.trends_models import TrendsModel
        from certificates.san_models import SANModel
        from certificates.overview_models import OverviewModels

        CertificateModel.collection = db_module.db['certificates']
        SharedModels.collection = db_module.db['certificates']
        ValidityModels.collection = db_module.db['certificates']
        CAModel.collection = db_module.db['certificates']
        SignatureHashModel.collection = db_module.db['certificates']
        TrendsModel.collection = db_module.db['certificates']
        SANModel.collection = db_module.db['certificates']
        OverviewModels.collection = db_module.db['certificates']
        
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
            **AVAILABLE_DATABASES.get(cls._current_db_id, {})
        }
    
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


# Default database (main certificates collection)
db = MongoDBClient.get_db(_CURRENT_MAIN_DB)

# Results database (pre-computed analytics)
results_db = MongoDBClient.get_db(_CURRENT_RESULTS_DB)