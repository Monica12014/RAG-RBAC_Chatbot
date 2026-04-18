# auth.py - User authentication and role management

# This is our "database" of users
# In a real app this would be a proper database
# Format: "username": {"password": "password", "role": "role-name"}

USERS = {
    "walmart_user": {
        "password": "walmart123",
        "role": "walmart"
    },
    "tesla_user": {
        "password": "tesla123",
        "role": "tesla"
    },
    "amazon_user": {
        "password": "amazon123",
        "role": "amazon"
    },
    "google_user": {
        "password": "google123",
        "role": "google"
    },
    "microsoft_user": {
        "password": "microsoft123",
        "role": "microsoft"
    },
    "admin": {
        "password": "admin123",
        "role": "admin"
    }
}


def login(username: str, password: str):
    """
    Check if username and password are correct.
    Returns the user's role if correct, None if wrong.
    """
    user = USERS.get(username)
    if user and user["password"] == password:
        return user["role"]
    return None


def get_allowed_namespace(role: str):
    """
    Each role can only access their own namespace in Pinecone.
    Admin can access all namespaces (returns None = no restriction).
    """
    if role == "admin":
        return None
    return role  # e.g. "walmart", "tesla", "amazon"


def add_user(username: str, password: str, role: str):
    """
    Add a new user to the USERS dict.
    Returns (True, success_message) or (False, error_message).
    """
    if username in USERS:
        return False, f"User '{username}' already exists."
    if not username or not password or not role:
        return False, "Username, password, and role are all required."
    USERS[username] = {"password": password, "role": role}
    return True, f"User '{username}' added successfully with role '{role}'."


def delete_user(username: str):
    """
    Delete a user from the USERS dict.
    Returns (True, success_message) or (False, error_message).
    Prevents deletion of the admin account.
    """
    if username == "admin":
        return False, "Cannot delete the admin account."
    if username not in USERS:
        return False, f"User '{username}' not found."
    del USERS[username]
    return True, f"User '{username}' deleted successfully."


def get_all_users():
    """
    Returns the full USERS dict (without exposing passwords in the UI).
    The dict format is: { "username": { "password": "...", "role": "..." } }
    app.py only displays the role, so passwords stay safe.
    """
    return USERS