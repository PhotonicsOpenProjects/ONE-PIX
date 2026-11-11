from flask import Blueprint

bp = Blueprint(
    "acquisition",
    __name__,
    url_prefix="/acquisition",
    template_folder="templates",
    static_folder="static"
)

from . import routes
from . import normalisation  # noqa: E402,F401  (registers the Normalisation tab routes)