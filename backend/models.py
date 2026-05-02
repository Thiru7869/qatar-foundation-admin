from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

OPPORTUNITY_CATEGORIES = [
    "Technology",
    "Business",
    "Design",
    "Marketing",
    "Data Science",
    "Other",
]

#  Admin

class Admin(db.Model):
    __tablename__ = "admins"

    id         = db.Column(db.Integer, primary_key=True)
    full_name  = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password   = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    opportunities = db.relationship(
        "Opportunity", backref="admin", lazy=True, cascade="all, delete-orphan"
    )
    reset_tokens = db.relationship(
        "ResetToken", backref="admin", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, raw: str):
        self.password = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password, raw)

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "full_name":  self.full_name,
            "email":      self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<Admin {self.email}>"

#  Opportunity

class Opportunity(db.Model):
    __tablename__ = "opportunities"

    id                   = db.Column(db.Integer, primary_key=True)
    admin_id             = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=False, index=True)

    opportunity_name     = db.Column(db.String(255), nullable=False)
    category             = db.Column(db.String(50),  nullable=False)
    duration             = db.Column(db.String(100), nullable=False)
    start_date           = db.Column(db.String(50),  nullable=False)
    description          = db.Column(db.Text,        nullable=False)
    skills               = db.Column(db.Text,        nullable=True)   # comma-separated
    future_opportunities = db.Column(db.Text,         nullable=True)   # career paths text
    max_applicants       = db.Column(db.Integer,     nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id":                   self.id,
            "admin_id":             self.admin_id,
            "opportunity_name":     self.opportunity_name,
            "category":             self.category,
            "duration":             self.duration,
            "start_date":           self.start_date,
            "description":          self.description,
            "skills":               self.skills,
            "future_opportunities": self.future_opportunities,
            "max_applicants":       self.max_applicants,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
            "updated_at":           self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_list_dict(self) -> dict:
        """Lighter payload for list endpoint — matches US-2.1 fields."""
        return {
            "id":               self.id,
            "opportunity_name": self.opportunity_name,
            "category":         self.category,
            "duration":         self.duration,
            "start_date":       self.start_date,
            "description":      self.description,
        }

    def __repr__(self):
        return f"<Opportunity {self.opportunity_name}>"

#  ResetToken

class ResetToken(db.Model):
    __tablename__ = "reset_tokens"

    id         = db.Column(db.Integer, primary_key=True)
    admin_id   = db.Column(db.Integer, db.ForeignKey("admins.id"), nullable=False, index=True)
    token      = db.Column(db.String(255), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used       = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired

    def __repr__(self):
        return f"<ResetToken admin={self.admin_id} used={self.used}>"