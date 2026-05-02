"""
Shared utilities
================
- token_required decorator (raw PyJWT)
- Input validators
- JSON response helpers
- Email via Resend
"""

import re
import jwt
import secrets
import logging
from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import request, jsonify, current_app
from models import Admin, OPPORTUNITY_CATEGORIES

logger = logging.getLogger("qatar_foundation.utils")


# ─────────────────────────────────────────────────────────────────────────────
#  JSON response helpers
# ─────────────────────────────────────────────────────────────────────────────

def success_response(data=None, message="Success", status_code=200):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status_code


def error_response(message, status_code=400, errors=None):
    payload = {"success": False, "message": message}
    if errors:
        payload["errors"] = errors
    return jsonify(payload), status_code


# ─────────────────────────────────────────────────────────────────────────────
#  token_required decorator  (raw PyJWT — simple and explicit)
# ─────────────────────────────────────────────────────────────────────────────

def token_required(f):
    """
    Reads Bearer token from Authorization header,
    decodes it with JWT_SECRET_KEY,
    loads the Admin from DB,
    injects it as the first argument of the decorated function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"success": False, "message": "Token missing"}), 401

        try:
            secret = current_app.config["JWT_SECRET_KEY"]
            data   = jwt.decode(token, secret, algorithms=["HS256"])
            admin_id = data.get("user")
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Token is invalid"}), 401

        current_user = Admin.query.get(admin_id)
        if not current_user:
            return jsonify({"success": False, "message": "Admin not found"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# ─────────────────────────────────────────────────────────────────────────────
#  Token generation helpers
# ─────────────────────────────────────────────────────────────────────────────

def generate_jwt(admin_id, secret, hours=2):
    payload = {
        "user": admin_id,
        "exp":  datetime.now(timezone.utc) + timedelta(hours=hours)
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def generate_reset_token():
    return secrets.token_urlsafe(48)


def reset_token_expiry(hours=1):
    return datetime.now(timezone.utc) + timedelta(hours=hours)


# ─────────────────────────────────────────────────────────────────────────────
#  Validators
# ─────────────────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9.\-]+$")


def validate_email_format(email):
    return bool(_EMAIL_RE.match(email.strip()))


def validate_signup_payload(data):
    errors = []
    full_name = (data.get("full_name") or "").strip()
    email     = (data.get("email")     or "").strip()
    password  = data.get("password")  or ""
    confirm   = data.get("confirm_password") or ""

    if not full_name:              errors.append("Full name is required.")
    if not email:                  errors.append("Email is required.")
    elif not validate_email_format(email): errors.append("Invalid email format.")
    if not password:               errors.append("Password is required.")
    elif len(password) < 8:        errors.append("Password must be at least 8 characters.")
    if not confirm:                errors.append("Confirm password is required.")
    elif password != confirm:      errors.append("Passwords do not match.")
    return errors


def validate_opportunity_payload(data):
    errors = []
    if not (data.get("opportunity_name") or "").strip(): errors.append("Opportunity name is required.")
    if not (data.get("duration")         or "").strip(): errors.append("Duration is required.")
    if not (data.get("start_date")       or "").strip(): errors.append("Start date is required.")
    if not (data.get("description")      or "").strip(): errors.append("Description is required.")

    category = (data.get("category") or "").strip()
    if not category:
        errors.append("Category is required.")
    elif category not in OPPORTUNITY_CATEGORIES:
        errors.append(f"Category must be one of: {', '.join(OPPORTUNITY_CATEGORIES)}.")

    max_app = data.get("max_applicants")
    if max_app not in (None, "", "null"):
        try:
            if int(max_app) < 1:
                errors.append("Max applicants must be a positive integer.")
        except (ValueError, TypeError):
            errors.append("Max applicants must be a valid integer.")

    return errors