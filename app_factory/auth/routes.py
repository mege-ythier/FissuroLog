"""Routes for user authentication."""

from typing import Optional


from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user

from email_validator import validate_email, EmailNotValidError

from app_factory import login_manager
from .forms import LoginForm, SignupForm, ChangePasswordForm, SignupGuestForm
from app_factory.models import User, db
from . import bp


@bp.route("/signup_guest", methods=["GET", "POST"])
def signup():
    """
    User sign-up page.

    GET requests serve sign-up page.
    POST requests validate form & user creation.
    """
    form = SignupGuestForm()

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user is None:
            user = User(email=form.email.data, role="guest")
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()  # Create new user
            login_user(user)  # Log in as newly created user
            return redirect(url_for("main_blueprint.welcome"))
        flash("A user already exists with that email address.")
    return render_template(
        "signup_guest.jinja2",
        title="Create an Account.",
        form=form,
        template="signup-page",
        body="Sign up for a user account."
    )

@bp.route("/signup_owner", methods=["GET", "POST"])
def signup_owner():
    """
    User sign-up page.

    GET requests serve sign-up page.
    POST requests validate form & user creation.
    """
    form = SignupForm()

    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user is None:
            user = User(email=form.email.data,role=form.role.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()  # Create new user
            login_user(user)  # Log in as newly created user
            return redirect(url_for("main_blueprint.welcome"))
        flash("A user already exists with that email address.")
        existing_user.set_password(form.password.data)
        existing_user.set_role(form.role.data)
        db.session.commit()  # Create new user
        login_user(existing_user)  # Log in as newly created user
        return redirect(url_for("main_blueprint.welcome"))

    return render_template(
        "signup_owner.jinja2",
        title="Create an Account.",
        form=form,
        template="signup-page",
        body="Sign up for a user account.",
    )



@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Log-in page for registered users.

    GET requests serve Log-in page.
    POST requests validate and redirect user to dashboard.
    """

    # Bypass if user is logged in
    if current_user.is_authenticated:
        return redirect(url_for("main_blueprint.welcome"))
    form = LoginForm()
    # Validate login attempt
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(password=form.password.data):
            login_user(user)
            return redirect(url_for(f"{user.role}_blueprint.dash_app"))

        flash("Invalid username/password combination")
        return redirect(url_for("auth_blueprint.login"))
    return render_template(
        "login.jinja2",
        form=form,
        title="Log in.",
        template="login-page",
        body="Log in with your User account.",
    )


@login_manager.user_loader
def load_user(user_id: int) -> Optional[User]:
    """
    Check if user is logged-in upon page load.

    :param int user_id: User ID from session cookie.

    :returns: bool
    """
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash("You must be logged in to view that page.")
    return redirect(url_for("auth_blueprint.login"))

