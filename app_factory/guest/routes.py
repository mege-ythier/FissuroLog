from flask import render_template
from . import bp

@bp.route("/fissurolog/")
def dash_app():
    return render_template('dashapp.jinja2', dash_url='/dash_fissurolog_guest', min_height=1500)
