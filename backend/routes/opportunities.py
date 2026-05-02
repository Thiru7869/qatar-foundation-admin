"""
OPPORTUNITY ROUTES
GET    /api/opportunities/
POST   /api/opportunities/
GET    /api/opportunities/categories
GET    /api/opportunities/<id>
PUT    /api/opportunities/<id>
DELETE /api/opportunities/<id>
"""

import logging
from flask import Blueprint, request

from models import db, Opportunity, OPPORTUNITY_CATEGORIES
from utils.helpers import (
    success_response, error_response,
    validate_opportunity_payload,
    token_required,
)

logger  = logging.getLogger("qatar_foundation.opportunities")
opps_bp = Blueprint("opportunities", __name__, url_prefix="/api/opportunities")


def _owned(opp_id, admin_id):
    return Opportunity.query.filter_by(id=opp_id, admin_id=admin_id).first()


def _apply(opp, data):
    opp.opportunity_name     = data["opportunity_name"].strip()
    opp.category             = data["category"].strip()
    opp.duration             = data["duration"].strip()
    opp.start_date           = data["start_date"].strip()
    opp.description          = data["description"].strip()
    opp.skills               = (data.get("skills") or "").strip() or None
    opp.future_opportunities = (data.get("future_opportunities") or "").strip() or None
    max_app = data.get("max_applicants")
    opp.max_applicants = int(max_app) if max_app not in (None, "", "null") else None


# ── List 
@opps_bp.get("/")
@token_required
def list_opportunities(current_user):
    items = (
        Opportunity.query
        .filter_by(admin_id=current_user.id)
        .order_by(Opportunity.created_at.desc())
        .all()
    )
    return success_response(data={
        "opportunities": [o.to_list_dict() for o in items],
        "total":         len(items),
    })


# ── Create 
@opps_bp.post("/")
@token_required
def create_opportunity(current_user):
    data   = request.get_json(silent=True) or {}
    errors = validate_opportunity_payload(data)
    if errors:
        return error_response("Validation failed.", 422, {"fields": errors})

    opp = Opportunity(admin_id=current_user.id)
    _apply(opp, data)
    db.session.add(opp)
    db.session.commit()

    logger.info(f"Opportunity created: {opp.opportunity_name} by {current_user.email}")
    return success_response(
        data={"opportunity": opp.to_dict()},
        message="Opportunity created successfully.",
        status_code=201,
    )


# ── Categories (public) 
@opps_bp.get("/categories")
def get_categories():
    return success_response(data={"categories": OPPORTUNITY_CATEGORIES})


# ── Detail 
@opps_bp.get("/<int:opp_id>")
@token_required
def get_opportunity(current_user, opp_id):
    opp = _owned(opp_id, current_user.id)
    if not opp:
        return error_response("Opportunity not found.", 404)
    return success_response(data={"opportunity": opp.to_dict()})


# ── Update 
@opps_bp.put("/<int:opp_id>")
@token_required
def update_opportunity(current_user, opp_id):
    opp = _owned(opp_id, current_user.id)
    if not opp:
        return error_response("Opportunity not found.", 404)

    data   = request.get_json(silent=True) or {}
    errors = validate_opportunity_payload(data)
    if errors:
        return error_response("Validation failed.", 422, {"fields": errors})

    _apply(opp, data)
    db.session.commit()
    return success_response(
        data={"opportunity": opp.to_dict()},
        message="Opportunity updated successfully.",
    )


# ── Delete 
@opps_bp.delete("/<int:opp_id>")
@token_required
def delete_opportunity(current_user, opp_id):
    opp = _owned(opp_id, current_user.id)
    if not opp:
        return error_response("Opportunity not found.", 404)

    db.session.delete(opp)
    db.session.commit()
    return success_response(
        data={"deleted_id": opp_id},
        message="Opportunity deleted successfully.",
    )