"""
AUTH ROUTES
POST  /api/auth/signup
POST  /api/auth/login
POST  /api/auth/forgot-password
GET   /api/auth/reset-password/<token>
POST  /api/auth/reset-password/<token>
GET   /api/auth/me
POST  /api/auth/logout
"""

import logging
import resend
from flask import Blueprint, request, current_app

from models import db, Admin, ResetToken
from utils.helpers import (
    success_response, error_response,
    validate_signup_payload, validate_email_format,
    generate_jwt, generate_reset_token, reset_token_expiry,
    token_required,
)

logger  = logging.getLogger("qatar_foundation.auth")
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


#  Email helper

def send_reset_email(to_email, token, admin_name):
    api_key   = current_app.config.get("RESEND_API_KEY", "")
    reset_url = f"http://127.0.0.1:5000/reset-password?token={token}"

    if not api_key:
        logger.warning(
            f"\n{'='*65}\n"
            f"  [DEV] No RESEND_API_KEY — use this link to reset:\n"
            f"  {reset_url}\n"
            f"{'='*65}"
        )
        return False

    resend.api_key = api_key
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:linear-gradient(135deg,#1a5c3a,#2d7a50);padding:32px;
                  border-radius:16px 16px 0 0;text-align:center;">
        <h1 style="color:#fff;margin:0;">Qatar Foundation</h1>
        <p style="color:rgba(255,255,255,.8);margin:6px 0 0;">Admin Portal — Password Reset</p>
      </div>
      <div style="background:#fff;padding:32px;border-radius:0 0 16px 16px;
                  box-shadow:0 4px 20px rgba(26,92,58,.1);">
        <p style="color:#1a2e23;font-size:16px;">Hello, <strong>{admin_name}</strong></p>
        <p style="color:#5a7568;">Click below to reset your password. Link expires in 1 hour.</p>
        <div style="text-align:center;margin:32px 0;">
          <a href="{reset_url}"
             style="background:linear-gradient(135deg,#1a5c3a,#2d7a50);color:#fff;
                    padding:14px 36px;border-radius:10px;text-decoration:none;
                    font-size:15px;font-weight:600;">
            Reset My Password
          </a>
        </div>
        <p style="color:#5a7568;font-size:12px;">
          Or paste this link:<br>
          <a href="{reset_url}" style="color:#2d7a50;word-break:break-all;">{reset_url}</a>
        </p>
      </div>
    </div>"""

    try:
        resend.Emails.send({
            "from":    current_app.config.get("MAIL_FROM", "Qatar Foundation <onboarding@resend.dev>"),
            "to":      [to_email],
            "subject": "Reset Your Qatar Foundation Admin Password",
            "html":    html,
        })
        logger.info(f"[EMAIL] Reset sent → {to_email}")
        return True
    except Exception as exc:
        logger.error(f"[EMAIL ERROR] {exc}")
        logger.warning(f"[FALLBACK] Reset URL: {reset_url}")
        return False



#  Signup

@auth_bp.post("/signup")
def signup():
    data   = request.get_json(silent=True) or {}
    errors = validate_signup_payload(data)
    if errors:
        return error_response("Validation failed.", 422, {"fields": errors})

    email = data["email"].strip().lower()
    if Admin.query.filter_by(email=email).first():
        return error_response("An account with this email already exists.", 409)

    admin = Admin(full_name=data["full_name"].strip(), email=email)
    admin.set_password(data["password"])
    db.session.add(admin)
    db.session.commit()

    logger.info(f"New admin: {email}")
    return success_response(
        data={"admin": admin.to_dict()},
        message="Account created successfully.",
        status_code=201,
    )



#  Login  — returns raw PyJWT token

@auth_bp.post("/login")
def login():
    data        = request.get_json(silent=True) or {}
    email       = (data.get("email")    or "").strip().lower()
    password    = data.get("password")  or ""
    remember_me = bool(data.get("remember_me", False))

    GENERIC = "Invalid email or password."
    if not email or not password:
        return error_response(GENERIC, 401)

    admin = Admin.query.filter_by(email=email).first()
    if not admin or not admin.check_password(password):
        return error_response(GENERIC, 401)

    secret = current_app.config["JWT_SECRET_KEY"]
    hours  = current_app.config["JWT_REMEMBER_ME_DAYS"] * 24 if remember_me \
             else current_app.config["JWT_EXPIRY_HOURS"]

    token = generate_jwt(admin.id, secret, hours=hours)

    logger.info(f"Login: {email}")
    return success_response(
        data={"access_token": token, "token_type": "Bearer", "admin": admin.to_dict()},
        message="Login successful.",
    )



#  Forgot Password

@auth_bp.post("/forgot-password")
def forgot_password():
    data  = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    ALWAYS_OK = "If an account with that email exists, a reset link has been sent."

    if not email or not validate_email_format(email):
        return success_response(message=ALWAYS_OK)

    admin = Admin.query.filter_by(email=email).first()
    if admin:
        ResetToken.query.filter_by(admin_id=admin.id, used=False).update({"used": True})
        db.session.flush()

        raw_token  = generate_reset_token()
        expires_at = reset_token_expiry(current_app.config["RESET_TOKEN_EXPIRES_HOURS"])

        db.session.add(ResetToken(admin_id=admin.id, token=raw_token, expires_at=expires_at))
        db.session.commit()

        send_reset_email(admin.email, raw_token, admin.full_name)

    return success_response(message=ALWAYS_OK)



#  Validate reset token

@auth_bp.get("/reset-password/<string:token>")
def validate_reset_token(token):
    record = ResetToken.query.filter_by(token=token).first()
    if not record:
        return error_response("Reset link is invalid.", 404)
    if not record.is_valid:
        return error_response("Reset link has expired or already been used.", 410)
    return success_response(
        data={"token": token, "expires_at": record.expires_at.isoformat()},
        message="Token is valid.",
    )



#  Consume reset token

@auth_bp.post("/reset-password/<string:token>")
def reset_password(token):
    data     = request.get_json(silent=True) or {}
    password = data.get("password") or ""
    confirm  = data.get("confirm_password") or ""

    if not password or len(password) < 8:
        return error_response("Password must be at least 8 characters.", 422)
    if password != confirm:
        return error_response("Passwords do not match.", 422)

    record = ResetToken.query.filter_by(token=token).first()
    if not record or not record.is_valid:
        return error_response("Reset link is invalid or has expired.", 410)

    record.admin.set_password(password)
    record.used = True
    db.session.commit()
    return success_response(message="Password updated. You can now log in.")



#  Me  (protected)

@auth_bp.get("/me")
@token_required
def me(current_user):
    return success_response(data={"admin": current_user.to_dict()})

#  Logout  — NO auth required (safest approach)

@auth_bp.post("/logout")
def logout():
    # JWT is stateless — client drops the token. No server state to clear.
    logger.info("[LOGOUT] Admin logged out")
    return success_response(message="Logged out successfully.")