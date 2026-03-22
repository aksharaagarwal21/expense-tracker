from datetime import datetime, timezone
from config.database import db


class User(db.Model):
    __tablename__ = "users"
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password   = db.Column(db.String(255), nullable=False)
    currency   = db.Column(db.String(10), default="INR")
    plan       = db.Column(db.String(20), default="free")
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    transactions = db.relationship("Transaction", backref="user", lazy="dynamic", cascade="all,delete-orphan")
    budgets      = db.relationship("Budget",      backref="user", lazy="dynamic", cascade="all,delete-orphan")
    bills        = db.relationship("Bill",        backref="user", lazy="dynamic", cascade="all,delete-orphan")
    cards        = db.relationship("PaymentCard", backref="user", lazy="dynamic", cascade="all,delete-orphan")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email,
                "currency": self.currency, "plan": self.plan,
                "created_at": self.created_at.isoformat()}


class RefreshToken(db.Model):
    __tablename__ = "refresh_tokens"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token      = db.Column(db.String(512), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class Transaction(db.Model):
    __tablename__ = "transactions"
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type           = db.Column(db.Enum("income","expense","transfer"), nullable=False)
    amount         = db.Column(db.Numeric(12,2), nullable=False)
    description    = db.Column(db.String(255), nullable=False)
    category       = db.Column(db.String(80), nullable=False)
    payment_method = db.Column(db.String(80), default="cash")
    status         = db.Column(db.Enum("completed","pending","failed"), default="completed")
    note           = db.Column(db.Text, nullable=True)
    date           = db.Column(db.Date, nullable=False, default=lambda: datetime.now(timezone.utc).date())
    card_id        = db.Column(db.Integer, db.ForeignKey("payment_cards.id", ondelete="SET NULL"), nullable=True)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {"id": self.id, "type": self.type, "amount": float(self.amount),
                "description": self.description, "category": self.category,
                "payment_method": self.payment_method, "status": self.status,
                "note": self.note, "date": self.date.isoformat(),
                "card_id": self.card_id, "created_at": self.created_at.isoformat()}


class Budget(db.Model):
    __tablename__ = "budgets"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category   = db.Column(db.String(80), nullable=False)
    limit      = db.Column(db.Numeric(12,2), nullable=False)
    period     = db.Column(db.Enum("monthly","weekly","yearly"), default="monthly")
    icon       = db.Column(db.String(10), default="💰")
    color      = db.Column(db.String(20), default="#7c6aff")
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self, spent=0.0):
        lim = float(self.limit)
        return {"id": self.id, "category": self.category, "limit": lim,
                "spent": spent, "remaining": max(0.0, lim - spent),
                "percent": round(min(100, spent/lim*100) if lim else 0, 1),
                "period": self.period, "icon": self.icon, "color": self.color,
                "is_active": self.is_active, "created_at": self.created_at.isoformat()}


class Bill(db.Model):
    __tablename__ = "bills"
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name       = db.Column(db.String(120), nullable=False)
    amount     = db.Column(db.Numeric(12,2), nullable=False)
    due_date   = db.Column(db.Date, nullable=False)
    frequency  = db.Column(db.Enum("monthly","weekly","quarterly","yearly","one-time"), default="monthly")
    auto_pay   = db.Column(db.Boolean, default=False)
    status     = db.Column(db.Enum("upcoming","due","paid","overdue"), default="upcoming")
    icon       = db.Column(db.String(10), default="📋")
    category   = db.Column(db.String(80), default="Utilities")
    card_id    = db.Column(db.Integer, db.ForeignKey("payment_cards.id", ondelete="SET NULL"), nullable=True)
    notes      = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {"id": self.id, "name": self.name, "amount": float(self.amount),
                "due_date": self.due_date.isoformat(), "frequency": self.frequency,
                "auto_pay": self.auto_pay, "status": self.status,
                "icon": self.icon, "category": self.category,
                "card_id": self.card_id, "notes": self.notes,
                "created_at": self.created_at.isoformat()}


class PaymentCard(db.Model):
    __tablename__ = "payment_cards"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    card_type    = db.Column(db.Enum("visa","mastercard","amex","rupay","other"), default="visa")
    last_four    = db.Column(db.String(4), nullable=False)
    cardholder   = db.Column(db.String(120), nullable=False)
    expiry_month = db.Column(db.SmallInteger, nullable=False)
    expiry_year  = db.Column(db.SmallInteger, nullable=False)
    bank_name    = db.Column(db.String(80), nullable=True)
    credit_limit = db.Column(db.Numeric(12,2), nullable=True)
    is_default   = db.Column(db.Boolean, default=False)
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {"id": self.id, "card_type": self.card_type, "last_four": self.last_four,
                "cardholder": self.cardholder,
                "expiry": f"{self.expiry_month:02d}/{str(self.expiry_year)[-2:]}",
                "bank_name": self.bank_name,
                "credit_limit": float(self.credit_limit) if self.credit_limit else None,
                "is_default": self.is_default, "is_active": self.is_active,
                "created_at": self.created_at.isoformat()}


class PaymentOrder(db.Model):
    __tablename__ = "payment_orders"
    id                 = db.Column(db.Integer, primary_key=True)
    user_id            = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gateway            = db.Column(db.Enum("razorpay","stripe"), nullable=False)
    gateway_order_id   = db.Column(db.String(255), unique=True, nullable=False)
    gateway_payment_id = db.Column(db.String(255), nullable=True)
    amount             = db.Column(db.Numeric(12,2), nullable=False)
    currency           = db.Column(db.String(10), default="INR")
    status             = db.Column(db.Enum("created","attempted","paid","failed","refunded"), default="created")
    description        = db.Column(db.String(255), nullable=True)
    created_at         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {"id": self.id, "gateway": self.gateway,
                "gateway_order_id": self.gateway_order_id,
                "gateway_payment_id": self.gateway_payment_id,
                "amount": float(self.amount), "currency": self.currency,
                "status": self.status, "description": self.description,
                "created_at": self.created_at.isoformat()}
