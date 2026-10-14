from flask import Blueprint

bp = Blueprint(
    "logs",
    __name__,
    url_prefix="/logs",
    template_folder="templates",
)

from . import routes
