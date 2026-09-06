from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt

from app.extensions import db
from app.models import User


def get_current_user():
    """Best-effort current user lookup from the JWT cookie, for nav/templates. Returns None if absent/invalid."""
    try:
        verify_jwt_in_request(optional=True)
    except Exception:
        return None
    identity = get_jwt_identity()
    if not identity:
        return None
    return db.session.get(User, int(identity))


def current_role():
    try:
        return get_jwt().get("role")
    except Exception:
        return None
