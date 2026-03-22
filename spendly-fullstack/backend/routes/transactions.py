from datetime import date
from flask import Blueprint, request
from sqlalchemy import func, extract
from config.database import db
from models import Transaction
from middleware.auth import jwt_required
from utils.helpers import success, error, paginate, get_month_range

transactions_bp = Blueprint("transactions", __name__)


@transactions_bp.route("", methods=["GET"])
@jwt_required
def list_txs():
    u  = request.current_user
    q  = Transaction.query.filter_by(user_id=u.id)
    a  = request.args

    if a.get("type")           and a["type"] in ("income","expense","transfer"): q=q.filter_by(type=a["type"])
    if a.get("status")         and a["status"] in ("completed","pending","failed"): q=q.filter_by(status=a["status"])
    if a.get("payment_method"): q=q.filter_by(payment_method=a["payment_method"])
    if a.get("category"):       q=q.filter(Transaction.category.ilike(f"%{a['category']}%"))
    if a.get("search"):         q=q.filter(Transaction.description.ilike(f"%{a['search']}%"))

    if a.get("month"):
        try:
            y,m = int(a["month"][:4]), int(a["month"][5:7])
            s,e = get_month_range(y, m)
            q   = q.filter(Transaction.date.between(s, e))
        except: pass
    else:
        if a.get("date_from"):
            try: q=q.filter(Transaction.date >= date.fromisoformat(a["date_from"]))
            except: pass
        if a.get("date_to"):
            try: q=q.filter(Transaction.date <= date.fromisoformat(a["date_to"]))
            except: pass

    sort_col = getattr(Transaction, a.get("sort_by","date") if a.get("sort_by","date") in ("date","amount","created_at") else "date")
    q = q.order_by(sort_col.desc() if a.get("sort_dir","desc")=="desc" else sort_col.asc())

    page     = max(1, int(a.get("page",1)))
    per_page = min(100, max(1, int(a.get("per_page",20))))
    r        = paginate(q, page, per_page)
    return success({"transactions": [t.to_dict() for t in r["items"]],
                    "pagination": {k:r[k] for k in ("total","page","pages","per_page")}})


@transactions_bp.route("", methods=["POST"])
@jwt_required
def create_tx():
    u = request.current_user
    d = request.get_json(silent=True) or {}
    for f in ("type","amount","description","category"):
        if not d.get(f): return error(f"{f} is required")
    if d["type"] not in ("income","expense","transfer"):
        return error("type must be income, expense, or transfer")
    try:
        amt = float(d["amount"])
        if amt <= 0: raise ValueError
    except: return error("amount must be a positive number")
    tx_date = date.today()
    if d.get("date"):
        try: tx_date = date.fromisoformat(d["date"])
        except: return error("date must be YYYY-MM-DD")
    tx = Transaction(user_id=u.id, type=d["type"], amount=amt,
                     description=d["description"].strip(), category=d["category"].strip(),
                     payment_method=d.get("payment_method","cash"),
                     status=d.get("status","completed"), note=d.get("note"),
                     date=tx_date, card_id=d.get("card_id"))
    db.session.add(tx)
    db.session.commit()
    return success({"transaction": tx.to_dict()}, "Transaction created", 201)


@transactions_bp.route("/<int:tid>", methods=["GET"])
@jwt_required
def get_tx(tid):
    return success({"transaction": _get(tid, request.current_user.id).to_dict()})


@transactions_bp.route("/<int:tid>", methods=["PUT"])
@jwt_required
def update_tx(tid):
    tx = _get(tid, request.current_user.id)
    d  = request.get_json(silent=True) or {}
    for f in ("description","category","payment_method","status","note","card_id"):
        if f in d: setattr(tx, f, d[f])
    if "amount" in d:
        try:
            v = float(d["amount"])
            if v<=0: raise ValueError
            tx.amount = v
        except: return error("amount must be positive")
    if "date" in d:
        try: tx.date = date.fromisoformat(d["date"])
        except: return error("date must be YYYY-MM-DD")
    if "type" in d:
        if d["type"] not in ("income","expense","transfer"): return error("invalid type")
        tx.type = d["type"]
    db.session.commit()
    return success({"transaction": tx.to_dict()}, "Updated")


@transactions_bp.route("/<int:tid>", methods=["DELETE"])
@jwt_required
def delete_tx(tid):
    tx = _get(tid, request.current_user.id)
    db.session.delete(tx)
    db.session.commit()
    return success(message="Deleted")


@transactions_bp.route("/summary", methods=["GET"])
@jwt_required
def summary():
    u  = request.current_user
    rows = (db.session.query(
                extract("year",Transaction.date).label("y"),
                extract("month",Transaction.date).label("m"),
                Transaction.type, func.sum(Transaction.amount).label("total"))
            .filter(Transaction.user_id==u.id, Transaction.status=="completed")
            .group_by("y","m",Transaction.type).order_by("y","m").all())
    data = {}
    for r in rows:
        k = f"{int(r.y):04d}-{int(r.m):02d}"
        if k not in data: data[k] = {"month":k,"income":0.0,"expense":0.0}
        if r.type=="income":  data[k]["income"]  = float(r.total)
        if r.type=="expense": data[k]["expense"] = float(r.total)
    months = min(12, max(1, int(request.args.get("months",6))))
    return success({"summary": list(data.values())[-months:]})


@transactions_bp.route("/categories", methods=["GET"])
@jwt_required
def categories():
    u  = request.current_user
    today = date.today()
    try:
        m = request.args.get("month","")
        y,mo = int(m[:4]),int(m[5:7])
    except:
        y,mo = today.year, today.month
    s,e = get_month_range(y, mo)
    rows = (db.session.query(Transaction.category, func.sum(Transaction.amount).label("t"))
            .filter(Transaction.user_id==u.id, Transaction.type=="expense",
                    Transaction.status=="completed", Transaction.date.between(s,e))
            .group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc()).all())
    result = [{"category":r.category,"amount":float(r.t)} for r in rows]
    grand  = sum(r["amount"] for r in result)
    for r in result: r["percent"] = round(r["amount"]/grand*100,1) if grand else 0
    return success({"categories": result, "total": grand})


def _get(tid, user_id):
    tx = Transaction.query.filter_by(id=tid, user_id=user_id).first()
    if not tx:
        from flask import abort; abort(404)
    return tx
