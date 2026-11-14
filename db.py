import os
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

TEST_MONGODB_URI = "mongodb+srv://astronomads_db_user:h4LR4FActK0wkJJy@cluster0.bfvf9dg.mongodb.net/?"
if not TEST_MONGODB_URI or not TEST_MONGODB_URI.strip():
    raise RuntimeError("TEST_MONGODB_URI must be set")

client = MongoClient(
     TEST_MONGODB_URI,
     server_api=ServerApi("1")
)

try:
    client.admin.command("ping")
    print("🍃 MongoDB connection successful.")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    raise

database = client["App"]

if "Users" not in database.list_collection_names():
    database.create_collection("Users")


# Collections:
users_collection = database["Users"]

# Helper Functions
def user_exists(username: str) -> bool:
    return users_collection.find_one({"username": username}) is not None

def new_user(username: str, password_hash: str):
    user = {"username": username, "password_hash": password_hash}
    users_collection.insert_one(user)
    return user

def return_user_hash(username: str) -> str:
    user = users_collection.find_one({"username": username})
    if user:
        return user["password_hash"]
    return None

