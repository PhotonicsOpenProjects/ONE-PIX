from flask import Blueprint

bp = Blueprint(
    "analysis",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/analysis"
)

from . import routes