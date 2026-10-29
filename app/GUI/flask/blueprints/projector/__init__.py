from flask import Blueprint

from i18n import register_translations

from .translations import TRANSLATIONS

bp = Blueprint(
    "projector",
    __name__,
    url_prefix="/projector",
    template_folder="templates",
)

register_translations(TRANSLATIONS)

from . import routes
