"""
Spendly Backend — Flask + MySQL
Run: python app.py
"""
from flask import Flask
from flask_cors import CORS
from config.settings import Config
from config.database import db, migrate
from routes.auth import auth_bp
from routes.transactions import transactions_bp
from routes.budgets import budgets_bp
from routes.bills import bills_bp
from routes.payments import payments_bp
from routes.dashboard import dashboard_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, resources={r"/api/*": {"origins": "*"}},
         supports_credentials=True)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(auth_bp,          url_prefix="/api/auth")
    app.register_blueprint(transactions_bp,  url_prefix="/api/transactions")
    app.register_blueprint(budgets_bp,       url_prefix="/api/budgets")
    app.register_blueprint(bills_bp,         url_prefix="/api/bills")
    app.register_blueprint(payments_bp,      url_prefix="/api/payments")
    app.register_blueprint(dashboard_bp,     url_prefix="/api/dashboard")

    @app.route("/api/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.errorhandler(404)
    def not_found(e):
        return {"success": False, "error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"success": False, "error": "Internal server error"}, 500

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        print("✅ Tables created / verified")
    print("🚀 Spendly API running at http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
