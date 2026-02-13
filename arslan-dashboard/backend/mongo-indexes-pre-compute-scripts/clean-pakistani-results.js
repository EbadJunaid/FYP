// Clean up incomplete pakistani-domains-results database
// Run this before setup if you had a failed attempt

db = db.getSiblingDB('pakistani-domains-results');

print("Dropping pakistani-domains-results database to start fresh...");
db.dropDatabase();
print("✅ Database dropped. Ready for fresh setup!");
