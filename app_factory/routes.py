from flask import render_template, redirect, url_for
from flask_login import current_user, login_required, logout_user
from . import bp


@bp.route("/", methods=["GET"])
@login_required
def welcome():
    return render_template(
        "welcome.jinja2",
        title="status",
        template="welcome-template",
        current_user=current_user,
        body="You are now logged in!",
    )


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth_blueprint.login"))
