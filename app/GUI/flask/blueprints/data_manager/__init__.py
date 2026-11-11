from flask import Blueprint

from i18n import register_translations

from .translations import TRANSLATIONS

bp = Blueprint(
    "data_manager",
    __name__,
    url_prefix="/data_manager",
    template_folder="templates",
    static_folder="static"
)

register_translations(TRANSLATIONS)

from . import routes