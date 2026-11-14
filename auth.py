from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

ph = PasswordHasher()

def auth_login(username, stored_username, password, stored_hash):
    if username == stored_username:
        try:
            return ph.verify(stored_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            return False
    else:
        return False

def hash_password(raw_password):
    return ph.hash(raw_password)