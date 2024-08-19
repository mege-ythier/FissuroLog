"""Flask app configuration."""
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from os import environ, path

from dotenv import load_dotenv

BASE_DIR = path.abspath(path.dirname(__file__))
load_dotenv(path.join(BASE_DIR, ".env"))


class Config:
    """Set Flask configuration from environment variables."""

    # General Config
    #ENVIRONMENT = environ.get("ENVIRONMENT")

    # Flask Config
    FLASK_ENV = environ.get("FLASK_ENV")
    FLASK_APP = "wsgi.py"
    DEBUG = True if environ.get("FLASK_DEBUG") == 'True' else False
    SECRET_KEY = environ.get("SECRET_KEY")


    # Flask-SQLAlchemy
    SQLALCHEMY_DATABASE_URI = environ.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'isolation_level': 'SERIALIZABLE'}

    # Static Assets
    STATIC_FOLDER = "static"
    TEMPLATES_FOLDER = "templates"
    COMPRESSOR_DEBUG = False

    # dash
    DASH_DEBUG = True if environ.get("DASH_DEBUG") == 'True' else False
    DASH_AUTO_RELOAD = True if environ.get("DASH_AUTO_RELOAD") == 'True' else False