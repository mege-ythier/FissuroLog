from flask import render_template
from flask_login import current_user, login_required, logout_user
from . import bp

@bp.route("/fissurolog/")
@login_required
def dash_app():
    return render_template('dashapp.jinja2', dash_url='/dash_fissurolog_guest', min_height=1500)
