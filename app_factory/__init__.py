"""Initialize Flask app_factory."""
import logging
import logging.config
from functools import wraps
# from logging.handlers import RotatingFileHandler
# from logging.handlers import TimedRotatingFileHandler

from dash import Dash
from flask import Flask, render_template, redirect, url_for, request, abort
from flask.helpers import get_root_path
from flask_login import LoginManager, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint



bp = Blueprint('main_blueprint', __name__, static_folder='static', template_folder='template')
from . import routes

db = SQLAlchemy()
login_manager = LoginManager()


def dash_login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)

    return decorated_function


def create_app():
    """Construct core Flask application."""

    # Création d'un objet journal create logger
    logging.config.fileConfig('logging.conf', disable_existing_loggers=True)
    logger = logging.getLogger(__name__)

    logger.debug('debug message debut application')

    app = Flask(__name__, instance_relative_config=False)

    # fonfigure flask app et sql alchemy
    app.config.from_object('config.Config')

    login_manager.init_app(app)

    db.init_app(app)

    with app.app_context():

        app.register_blueprint(bp)

        from . import auth, guest, owner
        app.register_blueprint(auth.bp, url_prefix='/auth')
        app.register_blueprint(guest.bp, url_prefix='/guest')
        app.register_blueprint(owner.bp, url_prefix='/owner')

        # Create Database Models
        db.create_all()


        dash_debug = app.config["DASH_DEBUG"]
        dash_auto_reload = app.config["DASH_AUTO_RELOAD"]
        meta_viewport = {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}

        dash_app_fissurolog_owner = Dash(
            __name__,
            server=app,
            title="App Fissurolog owner",
            url_base_pathname='/dash_fissurolog_owner/',
            assets_folder=get_root_path(__name__) + '/static/',
            meta_tags=[meta_viewport],
            serve_locally=True
        )
        from .owner.layout import layout as owner_layout
        dash_app_fissurolog_owner.layout = owner_layout

        from .owner.callbacks import register_callbacks
        from .owner.callbacks import register_owner_callbacks
        dash_app_fissurolog_owner.enable_dev_tools(debug=dash_debug, dev_tools_hot_reload=dash_auto_reload)

        for call_back_func in [register_callbacks, register_owner_callbacks]:
            call_back_func(dash_app_fissurolog_owner)



        dash_app_fissurolog_guest = Dash(
            __name__,
            server=app,
            title="App Fissurolog guest",
            url_base_pathname='/dash_fissurolog_guest/',
            assets_folder=get_root_path(__name__) + '/static/',
            meta_tags=[meta_viewport],
            serve_locally=True
        )

        from .guest.layout import layout as guest_layout
        dash_app_fissurolog_guest.layout = guest_layout

        dash_app_fissurolog_guest.enable_dev_tools(debug=dash_debug, dev_tools_hot_reload=dash_auto_reload)

        register_callbacks(dash_app_fissurolog_guest)


        def dash_login_required(funct, role):
            @wraps(funct)
            def decorated_view(*args, **kwargs):
                if not current_user.is_authenticated:
                    return redirect(url_for('auth_blueprint.login'))
                if current_user.role != role:
                    abort(403)
                return funct(*args, **kwargs)

            return decorated_view


        # ajout du décorateur pour sécuriser les callbacks Dash
        for view_func in app.view_functions:
            if view_func.startswith('/dash_fissurolog_owner/'):
                app.view_functions[view_func] = dash_login_required(app.view_functions[view_func],'owner')
            if view_func.startswith('/dash_fissurolog_guest/'):
                app.view_functions[view_func] = dash_login_required(app.view_functions[view_func],'guest')

        return app
