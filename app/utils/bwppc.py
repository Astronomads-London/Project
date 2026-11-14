"""
Astronaut mental health check-in.

Asks the four-part questionnaire (sleep, workload and stress, crew
relationships, personal wellbeing) with follow-up questions that depend on the answers,
saves every check-in to a JSON file, and returns the answers as a dict.

Each section starts broad and only digs deeper when an answer suggests
something might be wrong, so a good day stays a short check-in.

Run it:  python bwppc.py
"""

import json
from datetime import datetime
from pathlib import Path

SAVE_FILE = Path("checkins.json")


# ---------- helpers for asking questions ----------

def ask_text(question):
    """Ask an open question. Keeps asking until something is typed."""
    while True:
        answer = input(question + "\n> ").strip()
        if answer:
            return answer
        print("Please type an answer.")


def ask_number(question, low, high):
    """Ask for a whole number between low and high."""
    while True:
        answer = input(f"{question} ({low}-{high})\n> ").strip()
        if answer.isdigit() and low <= int(answer) <= high:
            return int(answer)
        print(f"Please enter a number from {low} to {high}.")


def ask_yes_no(question):
    """Ask a yes/no question. Returns True for yes, False for no."""
    while True:
        answer = input(question + " (y/n)\n> ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer y or n.")


def ask_choice(question, options):
    """Ask the person to pick one option from a list."""
    print(question)
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option}")
    pick = ask_number("Choose one", 1, len(options))
    return options[pick - 1]


# ---------- section 1: sleep ----------

def sleep_section():
    answers = {}
    answers["hours_slept"] = ask_number("How many hours did you sleep last night?", 0, 16)
    answers["sleep_rating"] = ask_number("How would you rate your sleep?", 1, 10)
    answers["fully_rested"] = ask_yes_no("Are you waking up fully rested?")

    # Poor sleep = short night OR low rating OR not rested
    poor_sleep = (answers["hours_slept"] < 6
                  or answers["sleep_rating"] <= 5
                  or not answers["fully_rested"])
    answers["sleep_type"] = "fragmented_or_reduced" if poor_sleep else "normal"

    if poor_sleep:
        answers["poor_sleep_nights"] = ask_number(
            "How many nights in a row has your sleep been like this?", 1, 30)
        answers["sleep_problem"] = ask_choice(
            "Which describes it best?",
            ["Hard to fall asleep", "Waking up during the night",
             "Waking up too early", "More than one of these"],
        )
        answers["cause_of_poor_sleep"] = ask_choice(
            "What is the main cause of your lack of sleep?",
            ["Noise", "Light", "Temperature", "Worry or stress",
             "Workload or schedule", "Physical discomfort", "Other"],
        )
        cause = answers["cause_of_poor_sleep"]
        if cause == "Other":
            answers["cause_other"] = ask_text("Please describe the cause.")
        elif cause == "Worry or stress":
            answers["worry_topic"] = ask_text(
                "What is on your mind when you are trying to sleep?")
        elif cause == "Workload or schedule":
            answers["schedule_shifted"] = ask_yes_no(
                "Has your sleep time been moved around in the last few days?")
        elif cause == "Physical discomfort":
            answers["discomfort_details"] = ask_text(
                "Where is the discomfort, and has it been reported to the flight surgeon?")

        answers["activity_when_awake"] = ask_text(
            "When you can't fall asleep, what are you doing?")
        answers["used_sleep_aid"] = ask_yes_no(
            "Have you taken anything to help you sleep in the last few nights?")
    else:
        answers["first_thought_on_waking"] = ask_text(
            "What is the first thought that comes to your head when you wake up?")
        answers["waking_thought_tone"] = ask_choice(
            "Is that thought usually...",
            ["Positive", "Neutral", "Negative"],
        )

    # How sleep is affecting the day, whatever the night was like
    answers["daytime_alertness"] = ask_number("How alert do you feel during the day?", 1, 10)
    answers["lapses_during_tasks"] = ask_yes_no(
        "Have you nodded off or lost focus during a task recently?")
    if answers["lapses_during_tasks"]:
        answers["lapse_details"] = ask_text("What were you doing when it happened?")

    return answers


# ---------- section 2: workload and stress ----------

def workload_section():
    answers = {}
    answers["schedule"] = ask_choice(
        "How is your daily schedule?",
        ["Manageable", "Busy but manageable", "Too stressful"],
    )
    if answers["schedule"] != "Manageable":
        answers["days_feeling_this_way"] = ask_number(
            "How many days has it felt like this?", 1, 30)
        answers["gets_real_breaks"] = ask_yes_no(
            "Do you get real breaks during the day (not just between tasks)?")

    answers["stress_level"] = ask_number("How stressed do you feel overall today?", 1, 10)
    answers["most_stressful_activity"] = ask_text(
        "What activity gives you the most stress?")
    answers["why_stressful"] = ask_choice(
        "Why is that activity stressful?",
        ["Time pressure", "Fear of making a mistake", "Physically tiring",
         "Unclear instructions", "Working with someone difficult", "Other"],
    )
    answers["task_confidence"] = ask_number(
        "How confident do you feel handling your tasks right now?", 1, 10)

    answers["annoyed_by_ground_changes"] = ask_yes_no(
        "When plans change because of the ground team, do you feel annoyed?")
    answers["emotions_on_plan_changes"] = ask_text(
        "What emotions do you feel when plans change?")
    if answers["annoyed_by_ground_changes"]:
        answers["told_ground_team"] = ask_yes_no(
            "Have you been able to tell the ground team how this affects you?")

    answers["has_someone_to_vent_to"] = ask_yes_no(
        "Do you have someone you can vent your frustrations to?")
    if answers["has_someone_to_vent_to"]:
        answers["vent_person"] = ask_text("Who is it?")
        answers["vent_person_details"] = ask_text(
            f"Tell me about {answers['vent_person']}. "
            "How often do you talk, and does it help?")
    else:
        answers["wants_support_contact"] = ask_yes_no(
            "Would you like a private session with the flight psychologist?")

    # Life back home is a big source of stress (or relief) on long missions
    answers["home_connection"] = ask_number(
        "How connected do you feel to family and friends back home?", 1, 10)
    answers["last_home_contact"] = ask_choice(
        "When did you last speak to them?",
        ["Today", "In the last few days", "Over a week ago", "Can't remember"],
    )
    if answers["home_connection"] <= 4:
        answers["home_worries"] = ask_text(
            "Is anything happening at home that is worrying you?")
    return answers


# ---------- section 3: crew relationships ----------

def crew_section():
    answers = {}
    answers["crew_relationship_rating"] = ask_number(
        "How is your relationship with other crew members at the moment?", 1, 10)
    answers["everyone_hospitable"] = ask_yes_no("Has everyone been hospitable?")
    if not answers["everyone_hospitable"]:
        answers["unhospitable_details"] = ask_text("What happened?")

    answers["anyone_quiet_irritable_annoying"] = ask_yes_no(
        "Has anyone been quiet, irritable or annoying?")
    if answers["anyone_quiet_irritable_annoying"]:
        answers["who_and_how"] = ask_text("Who, and what have you noticed?")
        answers["led_to_conflict"] = ask_yes_no(
            "Has this turned into an argument or disagreement?")
        if answers["led_to_conflict"]:
            answers["conflict_resolved"] = ask_choice(
                "Has it been sorted out?",
                ["Yes", "Partly", "No"],
            )
            if answers["conflict_resolved"] != "Yes":
                answers["wants_mediation"] = ask_yes_no(
                    "Would it help to talk it through with someone outside the crew?")

    answers["feels_included"] = ask_yes_no(
        "Do you feel included in crew decisions and activities?")

    # Deep check
    answers["prefers"] = ask_choice(
        "Do you prefer being alone or being with others?",
        ["Alone", "With others", "A mix of both"],
    )
    if answers["prefers"] == "Alone":
        answers["prefers_alone_is_new"] = ask_yes_no(
            "Is that new for you since the mission started?")
    answers["free_time_activities"] = ask_text(
        "What activities do you feel like doing in your free time?")
    answers["enjoys_free_time"] = ask_yes_no(
        "Do you still enjoy those activities as much as you used to?")
    answers["enough_private_space"] = ask_yes_no(
        "Do you get enough private space and time to yourself?")
    return answers


# ---------- section 4: personal wellbeing ----------

LOW_MOOD_WORDS = ("Anxious", "Sad", "Irritable", "Lonely", "Numb")


def personal_section():
    answers = {}
    answers["mood_rating"] = ask_number("Overall, how is your mood today?", 1, 10)
    answers["mood_word"] = ask_choice(
        "Which word best describes how you feel today?",
        ["Calm", "Happy", "Tired", "Anxious", "Sad", "Irritable", "Lonely", "Numb", "Other"],
    )
    if answers["mood_word"] == "Other":
        answers["mood_word_other"] = ask_text("How would you describe it?")

    low_mood = answers["mood_rating"] <= 4 or answers["mood_word"] in LOW_MOOD_WORDS
    if low_mood:
        answers["low_mood_duration"] = ask_choice(
            "How long have you been feeling this way?",
            ["Just today", "A few days", "Over a week", "Longer than that"],
        )
        answers["low_mood_reason"] = ask_text(
            "Is there something behind it, or does it feel like it came from nowhere?")

    answers["feels_like_themselves"] = ask_yes_no("Do you feel like yourself lately?")
    if not answers["feels_like_themselves"]:
        answers["what_feels_different"] = ask_text("What feels different?")

    answers["feeling_overwhelmed"] = ask_yes_no(
        "Have you felt overwhelmed or unable to cope at any point this week?")
    answers["appetite"] = ask_choice(
        "How has your appetite been?",
        ["Normal", "Eating less than usual", "Eating more than usual"],
    )

    answers["misses_most"] = ask_text("What do you miss most about home?")
    answers["looking_forward_to"] = ask_text(
        "What is something you are looking forward to, on the mission or after it?")
    answers["proud_of"] = ask_text(
        "What is one thing from the last few days you are proud of, big or small?")
    answers["what_helps"] = ask_text("What helps you most when you are having a hard day?")

    answers["something_unsaid"] = ask_yes_no(
        "Is there anything on your mind that you haven't told anyone?")
    if answers["something_unsaid"]:
        answers["unsaid_details"] = ask_text(
            "You can share it here if you want, or type 'skip' to keep it to yourself.")

    answers["thoughts_of_self_harm"] = ask_yes_no(
        "In the last two weeks, have you had thoughts that you would be better off dead, "
        "or of hurting yourself?")
    if answers["thoughts_of_self_harm"]:
        print("\nThank you for telling me. You are not alone with this. Please speak to the "
              "flight surgeon or flight psychologist today. They are there to help, "
              "and this check-in will alert them.\n")
    return answers


# ---------- simple flags for the app's alert engine ----------

def make_flags(result):
    """Turn answers into simple flags the rest of the app can use."""
    flags = []
    s, w, c, p = result["sleep"], result["workload"], result["crew"], result["personal"]

    # safety first: this one should always be acted on straight away
    if p["thoughts_of_self_harm"]:
        flags.append("urgent_safety_concern")

    # sleep
    if s["sleep_rating"] <= 4 or s["hours_slept"] < 5:
        flags.append("sleep_poor")
    if s.get("poor_sleep_nights", 0) >= 3:
        flags.append("sleep_poor_ongoing")
    if s.get("used_sleep_aid"):
        flags.append("sleep_aid_used")
    if s["daytime_alertness"] <= 4 or s["lapses_during_tasks"]:
        flags.append("daytime_fatigue")  # safety risk during operations

    # workload and stress
    if w["schedule"] == "Too stressful" or w["stress_level"] >= 8:
        flags.append("workload_high")
    if w.get("days_feeling_this_way", 0) >= 5 and not w.get("gets_real_breaks", True):
        flags.append("no_recovery_time")
    if w["task_confidence"] <= 4:
        flags.append("low_confidence")
    if not w["has_someone_to_vent_to"]:
        flags.append("no_support_person")
    if w.get("wants_support_contact"):
        flags.append("requested_psychologist")
    if w["home_connection"] <= 4 or w["last_home_contact"] in ("Over a week ago", "Can't remember"):
        flags.append("disconnected_from_home")

    # crew
    if c["crew_relationship_rating"] <= 4 or c["anyone_quiet_irritable_annoying"]:
        flags.append("crew_tension")
    if c.get("conflict_resolved") in ("Partly", "No"):
        flags.append("conflict_unresolved")
    if c.get("wants_mediation"):
        flags.append("requested_mediation")
    if not c["feels_included"]:
        flags.append("feels_excluded")
    if c["prefers"] == "Alone":
        flags.append("prefers_alone")  # not bad alone; watch alongside low mood
    if c.get("prefers_alone_is_new"):
        flags.append("withdrawing")  # a change from normal matters more than the preference
    if not c["enjoys_free_time"]:
        flags.append("loss_of_interest")

    # personal
    if p["mood_rating"] <= 4 or p["mood_word"] in LOW_MOOD_WORDS:
        flags.append("low_mood")
    if p.get("low_mood_duration") in ("Over a week", "Longer than that"):
        flags.append("low_mood_persistent")
    if not p["feels_like_themselves"]:
        flags.append("not_feeling_like_self")
    if p["feeling_overwhelmed"]:
        flags.append("overwhelmed")
    if p["appetite"] != "Normal":
        flags.append("appetite_change")
    return flags


# ---------- saving ----------

def save_checkin(result):
    """Add this check-in to the JSON file (keeps all previous ones)."""
    history = []
    if SAVE_FILE.exists():
        history = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    history.append(result)
    SAVE_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


def load_checkins(crew_id=None):
    """Read saved check-ins, optionally for one astronaut only."""
    if not SAVE_FILE.exists():
        return []
    history = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    if crew_id:
        history = [h for h in history if h["crew_id"] == crew_id]
    return history


# ---------- main check-in ----------

def run_checkin(crew_id):
    print(f"\n=== Daily check-in for {crew_id} ===\n")
    print("--- 1. Sleep ---")
    sleep = sleep_section()
    print("\n--- 2. Workload and stress ---")
    workload = workload_section()
    print("\n--- 3. Crew relationships ---")
    crew = crew_section()
    print("\n--- 4. How you are doing ---")
    personal = personal_section()

    result = {
        "crew_id": crew_id,
        "time": datetime.now().isoformat(timespec="minutes"),
        "sleep": sleep,
        "workload": workload,
        "crew": crew,
        "personal": personal,
    }
    result["flags"] = make_flags(result)
    save_checkin(result)
    print("\nThanks, your check-in has been saved.")
    return result


if __name__ == "__main__":
    crew_id = ask_text("Crew member ID (e.g. cmdr):")
    answers = run_checkin(crew_id)
    print("\nYour answers:")
    print(json.dumps(answers, indent=2))
