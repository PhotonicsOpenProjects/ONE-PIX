from flask import Blueprint

bp = Blueprint(
    "data_manager",
    __name__,
    url_prefix="/data_manager",
    template_folder="templates",
    static_folder="static"
)

from . import routes