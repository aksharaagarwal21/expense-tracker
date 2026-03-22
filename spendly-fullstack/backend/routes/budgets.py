from datetime import date
from flask import Blueprint, request
from sqlalchemy import func
from config.database import db
from models import Budget, Transaction
from middleware.auth import jwt_required
from utils.helpers import success, error, get_month_range

budgets_bp = Blueprint("budgets", __name__)


def calc_spent(user_id, category, period):
    today = date.today()
    if period == "monthly":
        s, e = get_month_range(today.year, today.month)
    elif period == "weekly":
        from datetime import timedelta
        s = today - date.timedelta(days=today.weekday()) if False else today.replace(day=today.day - today.weekday())
        from datetime import timedelta
        s = today - timedelta(days=today.weekday())
        e = s + timedelta(days=6)
    else:
        s, e = date(today.year,1,1), date(today.year,12,31)
    row = (db.session.query(func.sum(Transaction.amount))
           .filter(Transaction.user_id==user_id, Transaction.type=="expense",
                   Transaction.status=="completed",
                   Transaction.category.ilike(f"%{category}%"),
                   Transaction.date.between(s,e)).scalar())
    return float(row or 0)


@budgets_bp.route("", methods=["GET"])
@jwt_required
def list_budgets():
    u  = request.current_user
    bs = Budget.query.filter_by(user_id=u.id, is_active=True).all()
    result = [b.to_dict(spent=calc_spent(u.id, b.category, b.period)) for b in bs]
    return success({"budgets": result,
                    "total_limit": sum(float(b.limit) for b in bs),
                    "total_spent": sum(r["spent"] for r in result)})


@budgets_bp.route("", methods=["POST"])
@jwt_required
def create_budget():
    u = request.current_user
    d = request.get_json(silent=True) or {}
    cat = (d.get("category") or "").strip()
    if not cat: return error("category is required")
    try:
        lim = float(d.get("limit"))
        if lim <= 0: raise ValueError
    except: return error("limit must be a positive number")
    period = d.get("period","monthly")
    if period not in ("monthly","weekly","yearly"): return error("invalid period")
    if Budget.query.filter_by(user_id=u.id, category=cat, is_active=True).first():
        return error(f"Budget for '{cat}' already exists", 409)
    b = Budget(user_id=u.id, category=cat, limit=lim, period=period,
               icon=d.get("icon","💰"), color=d.get("color","#7c6aff"))
    db.session.add(b)
    db.session.commit()
    return success({"budget": b.to_dict(spent=calc_spent(u.id,cat,period))}, "Budget created", 201)


@budgets_bp.route("/<int:bid>", methods=["PUT"])
@jwt_required
def update_budget(bid):
    b = _get(bid, request.current_user.id)
    d = request.get_json(silent=True) or {}
    if "limit" in d:
        try:
            v = float(d["limit"])
            if v<=0: raise ValueError
            b.limit = v
        except: return error("limit must be positive")
    for f in ("period","icon","color","category"):
        if f in d: setattr(b, f, d[f])
    db.session.commit()
    return success({"budget": b.to_dict(spent=calc_spent(request.current_user.id, b.category, b.period))}, "Updated")


@budgets_bp.route("/<int:bid>", methods=["DELETE"])
@jwt_required
def delete_budget(bid):
    b = _get(bid, request.current_user.id)
    b.is_active = False
    db.session.commit()
    return success(message="Budget deleted")


@budgets_bp.route("/overview", methods=["GET"])
@jwt_required
def overview():
    u  = request.current_user
    bs = Budget.query.filter_by(user_id=u.id, is_active=True).all()
    result = []
    for b in bs:
        spent = calc_spent(u.id, b.category, b.period)
        row   = b.to_dict(spent=spent)
        row["alert"] = row["percent"] >= 80
        result.append(row)
    return success({"budgets": result})


def _get(bid, uid):
    b = Budget.query.filter_by(id=bid, user_id=uid).first()
    if not b:
        from flask import abort; abort(404)
    return b
