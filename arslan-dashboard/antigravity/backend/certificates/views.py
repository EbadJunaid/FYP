# backend/certificates/views.py
from django.http import JsonResponse
from .db import db # Import our DB singleton
import datetime

def hello_mongo_view(request):
    try:
        # MVC View Logic: Interacting with the Model/DB layer via PyMongo
        collection = db['test_coll']
        
        # 1. Insert a test document
        test_doc = {
            "message": "Hi Hello from backend and MongoDB",
            "timestamp": datetime.datetime.now()
        }
        collection.insert_one(test_doc)
        
        # 2. Retrieve the latest document (excluding the MongoDB _id for JSON safety)
        latest_doc = collection.find_one({}, {'_id': 0}, sort=[('_id', -1)])
        
        return JsonResponse(latest_doc)
    
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)