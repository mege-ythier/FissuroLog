"""Initialize Flask app_factory."""

from functools import wraps
from dash import Dash
from flask import Flask, redirect, url_for, abort
from flask.helpers import get_root_path
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint

# Création d'un objet journal create logger
import logging.config
logging.config.fileConfig('logging.conf', disable_existing_loggers=True)
mylogger = logging.getLogger(__name__)

bp = Blueprint('main_blueprint', __name__, static_folder='static', template_folder='template')
from . import routes

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    """Construct core Flask application."""

    mylogger.info("Démarrage de l'application")

    app = Flask(__name__, instance_relative_config=False)

    # configure flask app et sql alchemy
    app.config.from_object('config.Config')

    login_manager.init_app(app)

    db.init_app(app)

    with app.app_context():

        app.register_blueprint(bp)

        from . import auth
        app.register_blueprint(auth.bp, url_prefix='/auth')
        # Create Database
        #db.drop_all()
        db.create_all()

        dash_debug = app.config["DASH_DEBUG"]
        dash_auto_reload = app.config["DASH_AUTO_RELOAD"]
        meta_viewport = {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}

        dash_app_fissurolog_owner = Dash(
            __name__,
            server=app,
            title="App Fissurolog owner",
            url_base_pathname='/dash_fissurolog_owner/',
            assets_folder=get_root_path(__name__) + '/assets/fissurolog/',
            meta_tags=[meta_viewport],
            serve_locally=True,
            prevent_initial_callbacks=True
        )
        from app_factory.layout import owner_layout
        dash_app_fissurolog_owner.layout = owner_layout

        from app_factory.callbacks import register_callbacks
        from app_factory.callbacks import register_owner_callbacks
        dash_app_fissurolog_owner.enable_dev_tools(debug=dash_debug, dev_tools_hot_reload=dash_auto_reload)

        for call_back_func in [register_callbacks, register_owner_callbacks]:
            call_back_func(dash_app_fissurolog_owner)

        dash_app_fissurolog_guest = Dash(
            __name__,
            server=app,
            title="App Fissurolog guest",
            url_base_pathname='/dash_fissurolog_guest/',
            assets_folder=get_root_path(__name__) + '/assets/fissurolog/',
            meta_tags=[meta_viewport],
            serve_locally=True,
            prevent_initial_callbacks=True
        )

        from app_factory.layout import guest_layout
        dash_app_fissurolog_guest.layout = guest_layout

        dash_app_fissurolog_guest.enable_dev_tools(debug=dash_debug, dev_tools_hot_reload=dash_auto_reload)
        from .callbacks import register_meteo_callbacks
        register_callbacks(dash_app_fissurolog_guest)

        dash_app_meteo = Dash(
            __name__,
            server=app,
            title="App meteo",
            url_base_pathname='/dash_meteo/',
            assets_folder=get_root_path(__name__) + '/assets/meteo/',
            meta_tags=[meta_viewport],
            serve_locally=True,
            prevent_initial_callbacks=True)

        from app_factory.layout import meteo_layout
        dash_app_meteo.layout = meteo_layout
        from app_factory.callbacks import register_meteo_callbacks
        register_meteo_callbacks(dash_app_meteo)
        dash_app_meteo.enable_dev_tools(debug=dash_debug, dev_tools_hot_reload=dash_auto_reload)

        def dash_login_required(funct, role):
            @wraps(funct)
            def decorated_view(*args, **kwargs):
                if not current_user.is_authenticated:
                    return redirect(url_for('auth_blueprint.login'))
                if current_user.role == 'guest' and current_user.role != role:
                    abort(403)
                return funct(*args, **kwargs)

            return decorated_view

        # ajout du décorateur pour sécuriser les callbacks Dash
        for view_func in app.view_functions:
            if view_func.startswith('/dash_fissurolog_owner/'):
                app.view_functions[view_func] = dash_login_required(app.view_functions[view_func], 'owner')
            elif view_func.startswith('/dash_fissurolog_guest/'):
                app.view_functions[view_func] = dash_login_required(app.view_functions[view_func], 'guest')

        return app
