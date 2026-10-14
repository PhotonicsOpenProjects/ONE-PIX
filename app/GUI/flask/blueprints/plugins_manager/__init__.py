from flask import Blueprint

bp = Blueprint(
    "plugins_manager",
    __name__,
    url_prefix="/plugins_manager",
    template_folder="templates",
    static_folder="static",
)

from . import routes
