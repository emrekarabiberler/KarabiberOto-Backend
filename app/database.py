import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "karabiber_oto")

# Simple check to see if we should use Mock (for testing environments without MongoDB)
USE_MOCK = os.getenv("USE_MOCK", "false").lower() == "true"

class MockCollection:
    def __init__(self):
        self.data = []
    def find(self, query=None):
        return self
    async def to_list(self, length):
        return self.data
    async def insert_one(self, document):
        if "_id" not in document:
            from bson import ObjectId
            document["_id"] = ObjectId()
        self.data.append(document)
        class Result:
            def __init__(self, id): self.inserted_id = id
        return Result(document["_id"])
    async def find_one(self, query):
        for item in self.data:
            match = True
            for k, v in query.items():
                if item.get(k) != v:
                    match = False
                    break
            if match: return item
        return None

class MockDatabase:
    def __init__(self):
        self.collections = {"products": MockCollection()}
    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection()
        return self.collections[name]

if USE_MOCK:
    print("⚠️ WARNING: Running in MOCK MODE. Data will not be persisted.")
    database = MockDatabase()
else:
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=2000)
    database = client[DATABASE_NAME]

def get_database():
    return database
