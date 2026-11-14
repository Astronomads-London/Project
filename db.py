import os
from datetime import datetime
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

def new_user(username: str, password_hash: str, age: int, height: float, mass: float, sex: str):
    try:
        user = {
            "username": username,
            "password_hash": password_hash,
            "age": age,
            "height": height,
            "mass": mass,
            "sex": sex
        }
        users_collection.insert_one(user)
        return True
    except Exception as e:
        print(f"❌ Error occurred while creating new user: {e}")
        return False

def return_user_hash(username: str) -> str:
    user = users_collection.find_one({"username": username})
    if user:
        return user["password_hash"]
    return None

def new_data_entry(username: str, category: str, data: dict) -> bool:
    if not user_exists(username):
        raise ValueError("User does not exist")

    match category:
        case "daily_exercise":
            entry = {
                **data,
                "date": datetime.now().strftime("%d%m%Y"),
            }
            users_collection.update_one(
                {"username": username},
                {"$push": {"daily_exercise": entry}}
            )
            return True
        case "water_intake":
            entry = {
                **data,
                "date": datetime.now().strftime("%d%m%Y"),
            }
            users_collection.update_one(
                {"username": username},
                {"$push": {"water_intake": entry}}
            )
            return True
        case "body_temperature":
            entry = {
                **data,
                "date": datetime.now().strftime("%d%m%Y"),
            }
            users_collection.update_one(
                {"username": username},
                {"$push": {"body_temperature": entry}}
            )
            return True
        case "sleep_time":
            entry = {
                **data,
                "date": datetime.now().strftime("%d%m%Y"),
            }
            users_collection.update_one(
                {"username": username},
                {"$push": {"sleep_time": entry}}
            )
            return True
        case "blood_pressure":
            entry = {
                **data,
                "date": datetime.now().strftime("%d%m%Y"),
            }
            users_collection.update_one(
                {"username": username},
                {"$push": {"blood_pressure": entry}}
            )
            return True
        case "mood_checkin":
            entry = {
                **data,
                "date": datetime.now().strftime("%d%m%Y"),
            }
            users_collection.update_one(
                {"username": username},
                {"$push": {"mood_checkin": entry}}
            )
            return True
        case "blood_oxygen":
            entry = {
                **data,
                "date": datetime.now().strftime("%d%m%Y"),
            }
            users_collection.update_one(
                {"username": username},
                {"$push": {"blood_oxygen": entry}}
            )
            return True
        case "blood_glucose":
            entry = {
                **data,
                "date": datetime.now().strftime("%d%m%Y"),
            }
            users_collection.update_one(
                {"username": username},
                {"$push": {"blood_glucose": entry}}
            )
            return True
        case "resting_heart_rate":
            entry = {
                **data,
                "date": datetime.now().strftime("%d%m%Y"),
            }
            users_collection.update_one(
                {"username": username},
                {"$push": {"resting_heart_rate": entry}}
            )
            return True
        case _:
            raise ValueError("Invalid category")