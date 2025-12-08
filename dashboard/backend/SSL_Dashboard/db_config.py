from pymongo import MongoClient
from django.conf import settings


class DBConnection:
    def __init__(self):
        self.client = MongoClient(
            host=settings.MONGODB_HOST,
            port=settings.MONGODB_PORT,
        )
        self.db = self.client[settings.MONGODB_DATABASE]

    def get_collection(self, name):
        return self.db[name]
