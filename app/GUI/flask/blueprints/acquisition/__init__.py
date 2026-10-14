from flask import Blueprint

bp = Blueprint(
    "acquisition",
    __name__,
    url_prefix="/acquisition",
    template_folder="templates",
    static_folder="static"
)

from . import routes