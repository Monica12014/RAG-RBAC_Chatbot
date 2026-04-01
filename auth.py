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
    Admin can access all namespaces.
    """
    if role == "admin":
        return None  # admin gets no restriction
    
    return role  # e.g. "walmart", "tesla", "amazon"