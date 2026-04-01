# auth.py - User authentication and role management

import json
import os

USERS_FILE = "users.json"


def load_users():
    """
    Loads users from users.json file.
    """
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users: dict):
    """
    Saves users to users.json file.
    """
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def login(username: str, password: str):
    """
    Check if username and password are correct.
    Returns the user's role if correct, None if wrong.
    """
    users = load_users()
    user = users.get(username)

    if user and user["password"] == password:
        return user["role"]

    return None


def get_allowed_namespace(role: str):
    """
    Each role can only access their own namespace in Pinecone.
    Admin can access all namespaces.
    """
    if role == "admin":
        return None
    return role


def add_user(username: str, password: str, role: str):
    """
    Adds a new user to users.json.
    No code changes needed — just call this function.
    """
    users = load_users()

    if username in users:
        return False, f"User '{username}' already exists."

    users[username] = {
        "password": password,
        "role": role
    }
    save_users(users)
    return True, f"User '{username}' added successfully with role '{role}'."


def delete_user(username: str):
    """
    Deletes a user from users.json.
    """
    users = load_users()

    if username not in users:
        return False, f"User '{username}' not found."

    if username == "admin":
        return False, "Cannot delete admin user."

    del users[username]
    save_users(users)
    return True, f"User '{username}' deleted successfully."


def get_all_users():
    """
    Returns all users (without passwords).
    """
    users = load_users()
    return {
        username: {"role": data["role"]}
        for username, data in users.items()
    }