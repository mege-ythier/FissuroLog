
from flask import render_template, abort
from . import bp

@bp.route("/fissurolog")
def dash_app():
    return render_template('dashapp.jinja2', dash_url='/dash_fissurolog_owner', min_height=1500)



