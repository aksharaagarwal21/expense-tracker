import hmac, hashlib
from flask import Blueprint, request, current_app
from config.database import db
from models import PaymentCard, PaymentOrder, Transaction
from middleware.auth import jwt_required
from utils.helpers import success, error
from datetime import date

payments_bp = Blueprint("payments", __name__)


# ── Razorpay ──────────────────────────────────────────────────────────
@payments_bp.route("/razorpay/create-order", methods=["POST"])
@jwt_required
def rz_create():
    try: import razorpay
    except: return error("razorpay not installed")
    d = request.get_json(silent=True) or {}
    try:
        amt = float(d.get("amount")); assert amt>0
    except: return error("amount required")
    cfg    = current_app.config
    client = razorpay.Client(auth=(cfg["RAZORPAY_KEY_ID"], cfg["RAZORPAY_KEY_SECRET"]))
    try:
        rz = client.order.create({"amount": int(amt*100), "currency": d.get("currency","INR"),
                                   "notes": {"user_id": request.current_user.id}})
    except Exception as e:
        return error(str(e), 502)
    o = PaymentOrder(user_id=request.current_user.id, gateway="razorpay",
                     gateway_order_id=rz["id"], amount=amt,
                     currency=d.get("currency","INR"),
                     description=d.get("description","Payment"), status="created")
    db.session.add(o); db.session.commit()
    return success({"order_id": rz["id"], "amount": int(amt*100),
                    "currency": d.get("currency","INR"), "key_id": cfg["RAZORPAY_KEY_ID"]}, status=201)


@payments_bp.route("/razorpay/verify", methods=["POST"])
@jwt_required
def rz_verify():
    d = request.get_json(silent=True) or {}
    for f in ("razorpay_order_id","razorpay_payment_id","razorpay_signature"):
        if not d.get(f): return error(f"{f} required")
    secret   = current_app.config["RAZORPAY_KEY_SECRET"].encode()
    body     = f"{d['razorpay_order_id']}|{d['razorpay_payment_id']}".encode()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, d["razorpay_signature"]):
        return error("Signature verification failed", 400)
    o = PaymentOrder.query.filter_by(gateway_order_id=d["razorpay_order_id"],
                                     user_id=request.current_user.id).first()
    if not o: return error("Order not found", 404)
    o.gateway_payment_id = d["razorpay_payment_id"]; o.status = "paid"
    tx = Transaction(user_id=request.current_user.id, type="expense", amount=o.amount,
                     description=o.description or "Razorpay payment", category="Payment",
                     payment_method="razorpay", status="completed", date=date.today())
    db.session.add(tx); db.session.commit()
    return success({"order": o.to_dict(), "transaction": tx.to_dict()}, "Payment verified")


# ── Stripe ────────────────────────────────────────────────────────────
@payments_bp.route("/stripe/create-intent", methods=["POST"])
@jwt_required
def stripe_intent():
    try: import stripe
    except: return error("stripe not installed")
    d = request.get_json(silent=True) or {}
    try:
        amt = float(d.get("amount")); assert amt>0
    except: return error("amount required")
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    try:
        intent = stripe.PaymentIntent.create(amount=int(amt*100),
                                             currency=d.get("currency","inr"),
                                             description=d.get("description","Payment"),
                                             metadata={"user_id": request.current_user.id})
    except Exception as e:
        return error(str(e), 502)
    o = PaymentOrder(user_id=request.current_user.id, gateway="stripe",
                     gateway_order_id=intent["id"], amount=amt,
                     currency=d.get("currency","INR").upper(),
                     description=d.get("description"), status="created")
    db.session.add(o); db.session.commit()
    return success({"client_secret": intent["client_secret"],
                    "publishable_key": current_app.config["STRIPE_PUB_KEY"],
                    "intent_id": intent["id"]}, status=201)


@payments_bp.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    try: import stripe
    except: return error("stripe not installed")
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    try:
        event = stripe.Webhook.construct_event(
            request.get_data(), request.headers.get("Stripe-Signature",""),
            current_app.config["STRIPE_WEBHOOK_SEC"])
    except Exception as e:
        return error(str(e), 400)
    if event["type"] == "payment_intent.succeeded":
        intent = event["data"]["object"]
        o = PaymentOrder.query.filter_by(gateway_order_id=intent["id"]).first()
        if o and o.status != "paid":
            o.status = "paid"
            db.session.add(Transaction(user_id=o.user_id, type="expense", amount=o.amount,
                                       description=o.description or "Stripe payment",
                                       category="Payment", payment_method="stripe",
                                       status="completed", date=date.today()))
            db.session.commit()
    return {"received": True}, 200


# ── Transfer ──────────────────────────────────────────────────────────
@payments_bp.route("/transfer", methods=["POST"])
@jwt_required
def transfer():
    d = request.get_json(silent=True) or {}
    recipient = (d.get("recipient") or "").strip()
    if not recipient: return error("recipient required")
    try:
        amt = float(d.get("amount")); assert amt>0
    except: return error("amount must be positive")
    method = d.get("method","upi")
    tx = Transaction(user_id=request.current_user.id, type="expense", amount=amt,
                     description=f"Transfer to {recipient}", category="Transfer",
                     payment_method=method, status="pending",
                     note=d.get("note"), date=date.today())
    db.session.add(tx); db.session.commit()
    return success({"transaction": tx.to_dict()}, f"Transfer of ₹{amt:,.2f} initiated")


# ── Cards ─────────────────────────────────────────────────────────────
@payments_bp.route("/cards", methods=["GET"])
@jwt_required
def list_cards():
    cards = PaymentCard.query.filter_by(user_id=request.current_user.id, is_active=True).all()
    return success({"cards": [c.to_dict() for c in cards]})


@payments_bp.route("/cards", methods=["POST"])
@jwt_required
def add_card():
    u = request.current_user
    d = request.get_json(silent=True) or {}
    last4 = str(d.get("last_four") or "")
    if len(last4)!=4 or not last4.isdigit(): return error("last_four must be 4 digits")
    try:
        em=int(d["expiry_month"]); ey=int(d["expiry_year"])
        assert 1<=em<=12 and ey>=2024
    except: return error("expiry_month (1-12) and expiry_year required")
    ch = (d.get("cardholder") or "").strip()
    if not ch: return error("cardholder required")
    ct = d.get("card_type","visa")
    if ct not in ("visa","mastercard","amex","rupay","other"): return error("invalid card_type")
    is_first = PaymentCard.query.filter_by(user_id=u.id, is_active=True).count() == 0
    c = PaymentCard(user_id=u.id, card_type=ct, last_four=last4, cardholder=ch,
                    expiry_month=em, expiry_year=ey, bank_name=d.get("bank_name"),
                    credit_limit=d.get("credit_limit"), is_default=is_first)
    db.session.add(c); db.session.commit()
    return success({"card": c.to_dict()}, "Card added", 201)


@payments_bp.route("/cards/<int:cid>", methods=["PUT"])
@jwt_required
def update_card(cid):
    c = _card(cid, request.current_user.id)
    d = request.get_json(silent=True) or {}
    for f in ("bank_name","cardholder"):
        if f in d: setattr(c, f, d[f])
    if "credit_limit" in d:
        try: c.credit_limit = float(d["credit_limit"])
        except: return error("credit_limit must be a number")
    db.session.commit()
    return success({"card": c.to_dict()}, "Updated")


@payments_bp.route("/cards/<int:cid>", methods=["DELETE"])
@jwt_required
def delete_card(cid):
    c = _card(cid, request.current_user.id)
    c.is_active = False; db.session.commit()
    return success(message="Card removed")


@payments_bp.route("/cards/<int:cid>/default", methods=["PUT"])
@jwt_required
def set_default(cid):
    u = request.current_user
    c = _card(cid, u.id)
    PaymentCard.query.filter_by(user_id=u.id).update({"is_default": False})
    c.is_default = True; db.session.commit()
    return success({"card": c.to_dict()}, "Default card updated")


def _card(cid, uid):
    c = PaymentCard.query.filter_by(id=cid, user_id=uid, is_active=True).first()
    if not c:
        from flask import abort; abort(404)
    return c
