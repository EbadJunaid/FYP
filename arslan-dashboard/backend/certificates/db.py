# backend/certificates/db.py
from pymongo import MongoClient
from django.conf import settings

# MongoDB Connection Singleton
class MongoDBClient:
    _client = None

    @classmethod
    def get_db(cls):
        if cls._client is None:
            # Connect to MongoDB
            cls._client = MongoClient("mongodb://localhost:27017/")
        # Use the correct database name

        return cls._client['pk-domains-v3']
        # return cls._client['tranco_8_lac']

       
        # return cls._client['Tranco_data_Multi']


db = MongoDBClient.get_db()