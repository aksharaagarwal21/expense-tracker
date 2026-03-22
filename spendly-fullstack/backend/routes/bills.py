import calendar
from datetime import date, timedelta
from flask import Blueprint, request
from config.database import db
from models import Bill, Transaction
from middleware.auth import jwt_required
from utils.helpers import success, error

bills_bp = Blueprint("bills", __name__)


def _status(due):
    today = date.today()
    if due < today:              return "overdue"
    if (due-today).days <= 3:   return "due"
    return "upcoming"


def _next_due(d, freq):
    if freq=="monthly":
        m=d.month%12+1; y=d.year+(1 if d.month==12 else 0)
        return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))
    if freq=="weekly":    return d+timedelta(weeks=1)
    if freq=="quarterly":
        m=(d.month+2)%12+1; y=d.year+((d.month+2)//12)
        return date(y,m,min(d.day,calendar.monthrange(y,m)[1]))
    if freq=="yearly":    return date(d.year+1,d.month,d.day)
    return d


@bills_bp.route("", methods=["GET"])
@jwt_required
def list_bills():
    u  = request.current_user
    _refresh(u.id)
    q  = Bill.query.filter_by(user_id=u.id)
    st = request.args.get("status")
    if st: q = q.filter_by(status=st)
    bills = q.order_by(Bill.due_date.asc()).all()
    return success({"bills": [b.to_dict() for b in bills]})


@bills_bp.route("", methods=["POST"])
@jwt_required
def create_bill():
    u = request.current_user
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name: return error("name is required")
    try:
        amt = float(d.get("amount")); assert amt>0
    except: return error("amount must be positive")
    try:
        due = date.fromisoformat(d["due_date"])
    except: return error("due_date required as YYYY-MM-DD")
    freq = d.get("frequency","monthly")
    if freq not in ("monthly","weekly","quarterly","yearly","one-time"):
        return error("invalid frequency")
    b = Bill(user_id=u.id, name=name, amount=amt, due_date=due, frequency=freq,
             auto_pay=bool(d.get("auto_pay",False)), icon=d.get("icon","📋"),
             category=d.get("category","Utilities"), card_id=d.get("card_id"),
             notes=d.get("notes"), status=_status(due))
    db.session.add(b)
    db.session.commit()
    return success({"bill": b.to_dict()}, "Bill created", 201)


@bills_bp.route("/<int:bid>", methods=["GET"])
@jwt_required
def get_bill(bid):
    return success({"bill": _get(bid, request.current_user.id).to_dict()})


@bills_bp.route("/<int:bid>", methods=["PUT"])
@jwt_required
def update_bill(bid):
    b = _get(bid, request.current_user.id)
    d = request.get_json(silent=True) or {}
    for f in ("name","icon","category","auto_pay","card_id","notes"):
        if f in d: setattr(b, f, d[f])
    if "amount" in d:
        try:
            v=float(d["amount"]); assert v>0; b.amount=v
        except: return error("amount must be positive")
    if "due_date" in d:
        try: b.due_date=date.fromisoformat(d["due_date"]); b.status=_status(b.due_date)
        except: return error("due_date must be YYYY-MM-DD")
    if "frequency" in d: b.frequency=d["frequency"]
    db.session.commit()
    return success({"bill": b.to_dict()}, "Updated")


@bills_bp.route("/<int:bid>", methods=["DELETE"])
@jwt_required
def delete_bill(bid):
    b = _get(bid, request.current_user.id)
    db.session.delete(b)
    db.session.commit()
    return success(message="Bill deleted")


@bills_bp.route("/<int:bid>/pay", methods=["POST"])
@jwt_required
def pay_bill(bid):
    b  = _get(bid, request.current_user.id)
    u  = request.current_user
    tx = Transaction(user_id=u.id, type="expense", amount=b.amount,
                     description=f"Bill: {b.name}", category=b.category,
                     payment_method="auto_pay" if b.auto_pay else "manual",
                     status="completed", date=date.today(), card_id=b.card_id)
    db.session.add(tx)
    b.status   = "paid"
    b.due_date = _next_due(b.due_date, b.frequency)
    db.session.commit()
    return success({"bill": b.to_dict(), "transaction": tx.to_dict()}, f"{b.name} paid")


def _refresh(uid):
    for b in Bill.query.filter(Bill.user_id==uid, Bill.status.in_(["upcoming","due","overdue"])).all():
        ns = _status(b.due_date)
        if ns != b.status: b.status = ns
    db.session.commit()


def _get(bid, uid):
    b = Bill.query.filter_by(id=bid, user_id=uid).first()
    if not b:
        from flask import abort; abort(404)
    return b
