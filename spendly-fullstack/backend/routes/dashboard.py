from datetime import date
from flask import Blueprint, request
from sqlalchemy import func
from config.database import db
from models import Transaction, Budget, Bill
from middleware.auth import jwt_required
from utils.helpers import success, get_month_range
from routes.budgets import calc_spent

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/summary", methods=["GET"])
@jwt_required
def summary():
    u     = request.current_user
    today = date.today()
    s, e  = get_month_range(today.year, today.month)

    rows = (db.session.query(Transaction.type, func.sum(Transaction.amount))
            .filter(Transaction.user_id==u.id, Transaction.status=="completed",
                    Transaction.date.between(s,e))
            .group_by(Transaction.type).all())
    totals  = {r[0]: float(r[1]) for r in rows}
    income  = totals.get("income",  0.0)
    expense = totals.get("expense", 0.0)
    savings = income - expense

    lm = today.month-1 or 12
    ly = today.year-(1 if today.month==1 else 0)
    ls, le = get_month_range(ly, lm)
    lm_rows = (db.session.query(Transaction.type, func.sum(Transaction.amount))
               .filter(Transaction.user_id==u.id, Transaction.status=="completed",
                       Transaction.date.between(ls,le))
               .group_by(Transaction.type).all())
    lm = {r[0]: float(r[1]) for r in lm_rows}

    def pct(c, p): return round((c-p)/p*100,1) if p else None

    recent = (Transaction.query.filter_by(user_id=u.id)
              .order_by(Transaction.created_at.desc()).limit(8).all())

    budgets = Budget.query.filter_by(user_id=u.id, is_active=True).all()
    budget_data = [b.to_dict(spent=calc_spent(u.id,b.category,b.period)) for b in budgets]

    upcoming = (Bill.query.filter(Bill.user_id==u.id,
                                  Bill.status.in_(["upcoming","due","overdue"]))
                .order_by(Bill.due_date.asc()).limit(5).all())

    cat_rows = (db.session.query(Transaction.category, func.sum(Transaction.amount))
                .filter(Transaction.user_id==u.id, Transaction.type=="expense",
                        Transaction.status=="completed", Transaction.date.between(s,e))
                .group_by(Transaction.category)
                .order_by(func.sum(Transaction.amount).desc()).limit(5).all())

    return success({
        "stats": {
            "income": income, "expense": expense, "savings": savings,
            "savings_rate": round(savings/income*100,1) if income else 0,
            "income_change": pct(income, lm.get("income",0)),
            "expense_change": pct(expense, lm.get("expense",0)),
        },
        "recent_transactions": [t.to_dict() for t in recent],
        "budgets":             budget_data,
        "upcoming_bills":      [b.to_dict() for b in upcoming],
        "top_categories":      [{"category":r[0],"amount":float(r[1])} for r in cat_rows],
        "month": f"{today.year:04d}-{today.month:02d}",
    })
