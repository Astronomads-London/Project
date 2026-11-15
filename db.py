import os
import math
from datetime import datetime, timezone, timedelta
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import ASCENDING

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

if "ReportedData" not in database.list_collection_names():
    database.create_collection("ReportedData")


# Collections:
users_collection = database["Users"]




# Helper Functions
def user_exists(username: str) -> bool:
    return users_collection.find_one({"username": username}) is not None

def new_user(username: str, password_hash: str, birthday: str, height: float, mass: float, sex: str):
    try:
        user = {
            "username": username,
            "password_hash": password_hash,
            "birthday": birthday,
            "height": height,
            "mass": mass,
            "sex": sex,
            "water_target": 2500,
            "exercise_target": 60,
            "sleep_target": 8,
            "hydration_reminder": 0, # 0 = off, 1 = every hour, 2 = every 2 hours
            "environment": "ISS", # Mars, Moon
            "launch_date": datetime.utcnow().isoformat(),
            "mission_duration": 180, # in days
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

def edit_user(username: str, field: str, new_value):
    try:
        result = users_collection.update_one({"username": username}, {"$set": {field: new_value}})
        return result.modified_count > 0
    except Exception as e:
        print(f"❌ Error occurred while editing user: {e}")
        return False

def _reported_value(indicator_key, entry):
    if indicator_key == "bp":
        return {"sys": entry["sys"], "dia": entry["dia"]}
    if indicator_key == "urine":
        if "color_alert" in entry:
            return {"color_alert": entry["color_alert"]}
        return {
            key: value
            for key, value in entry.items()
            if key != "source"
        }
    if indicator_key == "bone_urine":
        return {
            key: value
            for key, value in entry.items()
            if key != "source"
        }
    if indicator_key == "fluid_ml":
        return entry["v"]
    return {
        key: value
        for key, value in entry.items()
        if key != "source"
    }

