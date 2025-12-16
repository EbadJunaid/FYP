from pymongo import MongoClient
from django.conf import settings

class DBConnection:
    def __init__(self):
        # Check if the MONGO_URI setting exists and is not empty (Production/Atlas)
        if hasattr(settings, 'MONGO_URI') and settings.MONGO_URI:
            self.client = MongoClient(settings.MONGO_URI)
        else:
            # Fallback to Host/Port (Local Development)
            self.client = MongoClient(
                host=settings.MONGODB_HOST,
                port=settings.MONGODB_PORT,
            )
        
        # Access the specific database
        self.db = self.client[settings.MONGODB_DATABASE]

    def get_collection(self, name):
        return self.db[name]