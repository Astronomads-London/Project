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

if "PVTResults" not in database.list_collection_names():
    database.create_collection("PVTResults")


# Collections:
users_collection = database["Users"]
reported_data_collection = database["ReportedData"]
pvt_results_collection = database["PVTResults"]

reported_data_collection.create_index(
    [("username", ASCENDING), ("date", ASCENDING)],
    unique=True,
    name="username_1_date_1",
)
if any(
    index["name"] == "crew_id_1_date_1"
    for index in reported_data_collection.list_indexes()
):
    reported_data_collection.drop_index("crew_id_1_date_1")



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
        print(f"d❌ Error occurred while creating new user: {e}")
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
        "sleep_hours",
        "exercise",
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
        "sleep_hours",
        "exercise",
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

def get_current_streak(username: str) -> int:
    data_fields = (
        "resting_heart_rate",
        "body_temp",
        "o2_level",
        "glucose_level",
        "blood_pressure",
        "breaths_per_min",
        "water",
        "sleep_hours",
        "exercise",
    )
    try:
        records = reported_data_collection.find(
            {"username": username},
            {"date": 1, **{field: 1 for field in data_fields}, "_id": 0},
        ).sort("date", -1)
        logged_dates = set()
        for record in records:
            if any(record.get(field) is not None for field in data_fields):
                logged_dates.add(datetime.strptime(record["date"], "%Y-%m-%d").date())

        today = datetime.now(timezone.utc).date()
        expected = today if today in logged_dates else today - timedelta(days=1)
        streak = 0
        while expected in logged_dates:
            streak += 1
            expected -= timedelta(days=1)
        return streak
    except Exception as e:
        print(f"❌ Error occurred while calculating current streak: {e}")
        return 0

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

def save_pvt_result(username: str, started_at: datetime, trials: list, scores: dict) -> bool:
    try:
        pvt_results_collection.insert_one({
            "username": username,
            "test_version": "PVT-B",
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc),
            "duration_ms": 180000,
            "configuration": {
                "foreperiod_min_ms": 0,
                "foreperiod_max_ms": 3000,
                "counter_interval_ms": 50,
                "response_timeout_ms": 30000,
                "lapse_threshold_ms": 500,
                "false_start_threshold_ms": 100,
                "feedback_ms": 1000,
            },
            "trials": trials,
            "scores": scores,
        })
        return True
    except Exception as e:
        print(f"❌ Error occurred while saving PVT results: {e}")
        return False

def get_user_age(username: str) -> int:
    try:
        user = users_collection.find_one({"username": username}, {"birthday": 1, "_id": 0})
        if user and "birthday" in user:
            birthday = datetime.strptime(user["birthday"], "%Y-%m-%d")
            today = datetime.now(timezone.utc)
            age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
            return age
        else:
            print(f"❌ User {username} not found or birthday not set.")
            return None
    except Exception as e:
        print(f"❌ Error occurred while calculating user age: {e}")
        return None
