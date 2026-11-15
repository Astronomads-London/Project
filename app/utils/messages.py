"""Messages between flight surgeons and astronauts.

Every astronaut has one conversation, shared by all flight surgeons. Flight
surgeons write treatment instructions into it and the astronaut can reply.
"""
from datetime import datetime

import db

MESSAGE_MAX_LENGTH = 2000
MESSAGE_ERRORS = {
    "empty": "Write a message before sending.",
    "too_long": f"Messages can be at most {MESSAGE_MAX_LENGTH} characters long.",
    "astronaut": "Choose an astronaut to send the message to.",
    "save": "The message could not be sent. Please try again.",
}


def clean_message(raw):
    """Return (text, None) for a message that can be stored, or (None, error code)."""
    if not isinstance(raw, str):
        return None, "empty"
    text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return None, "empty"
    if len(text) > MESSAGE_MAX_LENGTH:
        return None, "too_long"
    return text, None


def present_messages(messages, viewer_role):
    """Return stored messages as the fields the templates show.

    "new" marks a message from the other side that the viewer's side has not opened yet.
    """
    shown = []
    for message in messages:
        sent_at = message.get("sent_at")
        from_surgeon = message.get("sender_role") == db.ROLE_FLIGHT_SURGEON
        sender_role = db.ROLE_FLIGHT_SURGEON if from_surgeon else db.ROLE_ASTRONAUT
        shown.append({
            "astronaut": message.get("astronaut"),
            "sender": message.get("sender"),
            "from_surgeon": from_surgeon,
            "body": message.get("body") or "",
            "sent": (
                f"{sent_at.day} {sent_at:%b %Y, %H:%M} UTC"
                if isinstance(sent_at, datetime) else ""
            ),
            "new": not message.get("read") and sender_role != viewer_role,
        })
    return shown
