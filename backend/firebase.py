import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# Module-level client — initialized once, reused everywhere
_db: firestore.Client | None = None


def init_firestore() -> firestore.Client:
    """Initialize Firebase Admin SDK and return the Firestore client."""
    global _db
    if _db is not None:
        return _db

    key_path = os.getenv("FIREBASE_KEY_PATH")
    if not key_path:
        raise RuntimeError("FIREBASE_KEY_PATH is not set in .env")

    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)
    _db = firestore.client()
    return _db


def get_db() -> firestore.Client:
    """Return the active Firestore client. Must call init_firestore() first."""
    if _db is None:
        raise RuntimeError("Firestore has not been initialized. Call init_firestore() on startup.")
    return _db
