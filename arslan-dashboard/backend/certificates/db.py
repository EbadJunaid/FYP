# backend/certificates/db.py
from pymongo import MongoClient
from django.conf import settings

# MongoDB Connection Singleton with Multiple Database Support
class MongoDBClient:
    _client = None

    @classmethod
    def get_client(cls):
        """Get MongoDB client instance (singleton)"""
        if cls._client is None:
            # Connect to MongoDB server once
            cls._client = MongoClient("mongodb://localhost:27017/")
        return cls._client
    
    @classmethod
    def get_db(cls, database_name='tranco-latest-8-lakh'):
        """
        Get specific database from MongoDB server
        
        Args:
            database_name: Name of the database to access
            
        Returns:
            MongoDB database instance
            
        Examples:
            # Main certificates database
            main_db = MongoDBClient.get_db('tranco-latest-8-lakh')
            
            # Pre-computed results database
            results_db = MongoDBClient.get_db('tranco-latest-8-lakh-results')
        """
        client = cls.get_client()
        return client[database_name]


# Default database (main certificates collection)
db = MongoDBClient.get_db('tranco-latest-8-lakh')

# Results database (pre-computed analytics)
results_db = MongoDBClient.get_db('tranco-latest-8-lakh-results')