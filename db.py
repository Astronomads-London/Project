import os
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
reported_data_collection = database["ReportedData"]



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
            "streak": 0,
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

def get_user(username: str) -> dict:
    try:
        user = users_collection.find_one({"username": username})
        return user
    except Exception as e:
        print(f"❌ Error occurred while retrieving user: {e}")
        return None

def edit_user(username: str, field: str = None, new_value = None, **kwargs):
    try:
        update_dict = {}
        if field is not None:
            update_dict[field] = new_value
        if kwargs:
            update_dict.update(kwargs)
        if not update_dict:
            return True
        result = users_collection.update_one({"username": username}, {"$set": update_dict})
        return result.matched_count > 0 or result.modified_count > 0
    except Exception as e:
        print(f"❌ Error occurred while editing user: {e}")
        return False

def edit_today_data(username: str, field: str, new_value) -> bool:
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_fields = (
        "resting_heart_rate",
        "body_temp",
        "o2_level",
        "glucose_level",
        "blood_pressure",
        "breaths_per_min",
        "water",
    )
    if field not in data_fields:
        raise ValueError(f"Unknown health data field: {field}")

    defaults = {name: None for name in data_fields if name != field}

    try:
        result = reported_data_collection.update_one(
            {"username": username, "date": today_str},
            {
                "$setOnInsert": {
                    "username": username,
                    "date": today_str,
                    **defaults,
                },
                "$set": {field: new_value},
            },
            upsert=True,
        )
        return result.matched_count > 0 or result.upserted_id is not None
    except Exception as e:
        print(f"❌ Error occurred while editing today's data: {e}")
        return False

def get_today_data(username: str) -> dict:
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    data_fields = (
        "resting_heart_rate",
        "body_temp",
        "o2_level",
        "glucose_level",
        "blood_pressure",
        "breaths_per_min",
        "water",
    )
    try:
        data = reported_data_collection.find_one({"username": username, "date": today_str})
        if data:
            return {field: data.get(field) for field in data_fields}
        else:
            return {field: None for field in data_fields}
    except Exception as e:
        print(f"❌ Error occurred while retrieving today's data: {e}")
        return {field: None for field in data_fields}

def get_last_7_days_data(username:str, field:str) -> list:
    today = datetime.now(timezone.utc)
    seven_days_ago = today - timedelta(days=6)
    try:
        data_cursor = reported_data_collection.find(
            {
                "username": username,
                "date": {"$gte": seven_days_ago.strftime("%Y-%m-%d"), "$lte": today.strftime("%Y-%m-%d")},
                field: {"$exists": True}
            },
            {field: 1, "date": 1, "_id": 0}
        ).sort("date", ASCENDING)

        return [{ "date": entry["date"], field: entry[field] } for entry in data_cursor]
    except Exception as e:
        print(f"❌ Error occurred while retrieving last 7 days data: {e}")
        return []

