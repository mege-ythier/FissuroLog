from flask import Blueprint

# Blueprint Configuration
bp = Blueprint("auth_blueprint", __name__, template_folder="templates", static_folder="static")

from app_factory.auth import routes
