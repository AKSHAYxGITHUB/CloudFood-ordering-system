from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies

from app.extensions import db, limiter
from app.models import User
from app.auth.forms import LoginForm, SignupForm

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if existing:
            flash("An account with that email already exists.", "error")
            return render_template("auth/signup.html", form=form)

        user = User(name=form.name.data.strip(), email=form.email.data.lower().strip(), role="customer")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/signup.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if user and user.is_locked():
            flash("Account temporarily locked due to repeated failed logins. Try again later.", "error")
            return render_template("auth/login.html", form=form)

        if not user or not user.check_password(form.password.data):
            if user:
                user.register_failed_login(
                    current_app.config["MAX_FAILED_LOGIN_ATTEMPTS"],
                    current_app.config["ACCOUNT_LOCKOUT_MINUTES"],
                )
                db.session.commit()
            flash("Invalid email or password.", "error")
            return render_template("auth/login.html", form=form)

        user.register_successful_login()
        db.session.commit()

        claims = {"role": user.role, "name": user.name}
        access_token = create_access_token(identity=str(user.id), additional_claims=claims)

        destination = url_for("admin.dashboard") if user.is_admin else url_for("customer.restaurants")
        response = redirect(destination)
        set_access_cookies(response, access_token)
        flash(f"Welcome back, {user.name}!", "success")
        return response

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
def logout():
    response = redirect(url_for("auth.login"))
    unset_jwt_cookies(response)
    flash("You have been logged out.", "success")
    return response
