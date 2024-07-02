from flask import Blueprint

bp = Blueprint("owner_blueprint", __name__, static_folder='static', template_folder='template')

from . import routes
