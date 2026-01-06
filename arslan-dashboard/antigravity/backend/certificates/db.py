# backend/certificates/db.py
from pymongo import MongoClient
from django.conf import settings

# This utility ensures we don't create a new connection on every request
class MongoDBClient:
    _client = None

    @classmethod
    def get_db(cls):
        if cls._client is None:
            # In a production MVC, these would be in settings.py or .env
            cls._client = MongoClient("mongodb://localhost:27017/")
        return cls._client['antigravity']

db = MongoDBClient.get_db()