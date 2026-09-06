from flask import Flask, render_template, redirect, url_for, flash

from app.config import Config
from app.extensions import db, jwt, bcrypt, csrf, limiter
from app.security import apply_security_headers


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @jwt.unauthorized_loader
    @jwt.invalid_token_loader
    @jwt.expired_token_loader
    def _redirect_to_login(*_args, **_kwargs):
        flash("Please log in to continue.", "error")
        return redirect(url_for("auth.login"))

    from app.auth.routes import auth_bp
    from app.customer.routes import customer_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(customer_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.context_processor
    def inject_current_user():
        from app.auth.utils import get_current_user

        return {"current_user": get_current_user()}

    @app.after_request
    def set_security_headers(response):
        return apply_security_headers(response)

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("errors/500.html"), 500

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    register_cli(app)

    return app


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create tables and seed sample restaurants/menu items + an admin account."""
        from seed import run_seed

        with app.app_context():
            db.create_all()
            run_seed()
        print("Database initialized and seeded.")
