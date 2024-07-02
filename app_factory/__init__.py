"""Initialize Flask app_factory."""
import logging
import logging.config
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler

from datetime import datetime

from dash import Dash
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
#import pymysql
from flask import Blueprint



bp = Blueprint('main_blueprint', __name__, static_folder='static', template_folder='template')
from . import routes



db = SQLAlchemy()
login_manager = LoginManager()

def create_app(dash_debug, dash_auto_reload):
    """Construct core Flask application."""

    # Création d'un objet journal create logger
    logging.config.fileConfig('logging.conf', disable_existing_loggers=True)
    logger = logging.getLogger(__name__)

    logger.debug('debug message debut application')

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('config.Config')

    # Initialize Plugins
    login_manager.init_app(app)
    db.init_app(app)

    with app.app_context():
        # Import parts of our core Flask app_factory
        from . import auth, guest, owner

        # Register Blueprints

        app.register_blueprint(bp)
        app.register_blueprint(auth.bp, url_prefix='/auth')
        app.register_blueprint(guest.bp, url_prefix='/guest')
        app.register_blueprint(owner.bp, url_prefix='/owner')


        # Create Database Models
        db.create_all()

        meta_viewport = {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}

        from .guest.layout import layout as guest_layout
        from .guest.callbacks import register_callbacks as guest_callbacks
        dash_app_fissurolog_guest = Dash(
            __name__,
            server=app,
            url_base_pathname='/dash_fissurolog_guest/',
            # assets_folder=get_root_path(__name__) + '/static/',
            meta_tags=[meta_viewport],
            # external_stylesheets=[],
            # external_scripts=[],
            #suppress_callback_exceptions=False
        )

        dash_app_fissurolog_guest.title = "App Fissurolog guest"
        dash_app_fissurolog_guest.layout = guest_layout
        dash_app_fissurolog_guest.css.config.serve_locally = True
        dash_app_fissurolog_guest.enable_dev_tools(debug=dash_debug, dev_tools_hot_reload=dash_auto_reload)
        for call_back_func in [guest_callbacks]:
            call_back_func(dash_app_fissurolog_guest)


        from .owner.layout import layout as owner_layout
        from .owner.callbacks import register_callbacks as owner_callbacks
        dash_app_fissurolog_owner = Dash(
            __name__,
            server=app,
            url_base_pathname='/dash_fissurolog_owner/',
            # assets_folder=get_root_path(__name__) + '/static/',
            meta_tags=[meta_viewport],
            # external_stylesheets=[],
            # external_scripts=[],
            #suppress_callback_exceptions=False


        )

        dash_app_fissurolog_owner.title = "App Fissurolog owner"
        dash_app_fissurolog_owner.layout = owner_layout
        dash_app_fissurolog_owner.css.config.serve_locally = True
        dash_app_fissurolog_owner.enable_dev_tools(debug=dash_debug, dev_tools_hot_reload=dash_auto_reload)
        for call_back_func in [owner_callbacks]:
            call_back_func(dash_app_fissurolog_owner)



        return app
