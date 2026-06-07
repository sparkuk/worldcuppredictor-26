import hashlib
from typing import Optional
from models import User
from storage import StorageEngine

def hash_password(password: str) -> str:
    """Hashes a password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a password against a hash."""
    return hash_password(password) == hashed

def authenticate(username: str, password_text: str, storage: StorageEngine) -> Optional[User]:
    """Checks credentials and returns User if valid, None otherwise."""
    users = storage.load_users()
    pwd_hash = hash_password(password_text)
    for u in users:
        if u.username == username and u.password_hash == pwd_hash:
            return u
    return None

# main to 
def main():
    pwd = input("Enter password to hash:")
    print(hash_password(pwd))

if __name__ == "__main__":
    main()
