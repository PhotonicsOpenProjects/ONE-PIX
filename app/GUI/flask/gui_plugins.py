"""GUI extensions contributed by installed plugins.

The core app only knows its own pages. Anything that belongs to one
plugin - its pages, settings panels, form fields, pre-flight checks -
ships with that plugin and is discovered here at startup, so installing
or removing a plugin is all it takes to add or remove its interface.
A plugin that fails to load is logged and skipped, never fatal.

Analysis pages
    Entry point group "onepix.analysis_pages". The entry point loads an
    object (usually a module) with:

        create_blueprint(get_current_result, url_prefix) -> Blueprint
        NAV_LABEL   optional translation key for its nav link (default:
                    the entry point name)
        NAV_ICON    optional SVG markup (24x24 viewBox) for that link

    Mounted at /analysis/<entry point name>, with a nav link to it.

Imaging method extensions
    An optional AcquisitionGUI submodule in an imaging method plugin,
    resolved through ImagingMethodBridge like SpecificAnalysis. Every
    attribute is optional:

        TRANSLATIONS      {lang: {key: text}}, merged into i18n
        FIELD_META        settings form metadata for the method's own
                          config fields (see blueprints/acquisition/
                          field_meta.py)
        settings_choices()  {field: [options]} for fields shown as a
                          dropdown on the Imaging method page
        SETTINGS_PANELS   template names included below that page's form
        create_blueprint(url_prefix, hardware_lock) -> Blueprint
                          mounted at /acquisition/method/<method>; the
                          SETTINGS_PANELS templates live in its
                          template folder
        acquisition_overview(software, hardware, t) -> dict with
                          "summary": text describing the method's
                              current setup, or None
                          "warnings": [{"message": text,
                              "fix": "hardware" | "imaging"}], problems
                              that would make the next acquisition fail
"""

import logging

from importlib.metadata import entry_points

from onepix.ImagingMethodBridge import ImagingMethodBridge

from i18n import register_translations

logger = logging.getLogger(__name__)

ANALYSIS_PAGES_GROUP = "onepix.analysis_pages"

# Generic "page" icon for an analysis page that doesn't bring its own.
DEFAULT_NAV_ICON = (
    '<rect x="4" y="3" width="16" height="18" rx="2"></rect>'
    '<path d="M8 8h8M8 12h8M8 16h5"></path>'
)

# [{"name", "blueprint", "url", "label", "icon"}], in nav order.
ANALYSIS_PAGES = []

# Imaging method name (lowercase) -> its AcquisitionGUI module.
METHOD_EXTENSIONS = {}


def _select_entry_points(group):

    eps = entry_points()

    if hasattr(eps, "select"):
        return list(eps.select(group=group))

    return list(eps.get(group, []))


def register_analysis_pages(app, get_current_result):

    ANALYSIS_PAGES.clear()

    for ep in sorted(_select_entry_points(ANALYSIS_PAGES_GROUP), key=lambda ep: ep.name):

        url_prefix = f"/analysis/{ep.name}"

        try:
            plugin = ep.load()
            blueprint = plugin.create_blueprint(
                get_current_result=get_current_result,
                url_prefix=url_prefix,
            )
            app.register_blueprint(blueprint)

        except Exception:
            logger.exception("Analysis page plugin '%s' could not be loaded", ep.name)
            continue

        ANALYSIS_PAGES.append({
            "name": ep.name,
            "blueprint": blueprint.name,
            "url": url_prefix + "/",
            "label": getattr(plugin, "NAV_LABEL", ep.name),
            "icon": getattr(plugin, "NAV_ICON", DEFAULT_NAV_ICON),
        })

        logger.info("Registered analysis page '%s' at %s", ep.name, url_prefix)


def register_method_extensions(app, hardware_lock):

    METHOD_EXTENSIONS.clear()

    for method in ImagingMethodBridge.list_available_methods():

        method_key = method.lower()

        try:
            module = ImagingMethodBridge(method_key)._import_submodule("AcquisitionGUI")
        except ImportError as exc:
            logger.info("No acquisition GUI extension for %s: %s", method_key, exc)
            continue
        except Exception:
            logger.exception("Acquisition GUI extension for %s could not be loaded", method_key)
            continue

        try:
            register_translations(getattr(module, "TRANSLATIONS", {}))

            create_blueprint = getattr(module, "create_blueprint", None)
            if create_blueprint is not None:
                app.register_blueprint(create_blueprint(
                    url_prefix=f"/acquisition/method/{method_key}",
                    hardware_lock=hardware_lock,
                ))

        except Exception:
            logger.exception("Acquisition GUI extension for %s could not be registered", method_key)
            continue

        METHOD_EXTENSIONS[method_key] = module
        logger.info("Registered acquisition GUI extension for %s", method_key)


def method_extension(method_name):
    """The AcquisitionGUI module of ``method_name``, or None."""

    if not method_name:
        return None

    return METHOD_EXTENSIONS.get(str(method_name).lower())


def method_settings(method_name):
    """(field_meta, choices, panels) a method's extension adds to the
    Imaging method settings page - all empty without one."""

    extension = method_extension(method_name)

    if extension is None:
        return {}, {}, []

    choices = {}
    settings_choices = getattr(extension, "settings_choices", None)

    if settings_choices is not None:
        try:
            choices = dict(settings_choices())
        except Exception:
            logger.exception("Could not list the settings choices of %s", method_name)

    return (
        dict(getattr(extension, "FIELD_META", {})),
        choices,
        list(getattr(extension, "SETTINGS_PANELS", [])),
    )


def method_overview(method_name, software, hardware, t):
    """(summary, warnings) from a method's acquisition_overview hook -
    (None, []) without one, or if it fails."""

    hook = getattr(method_extension(method_name), "acquisition_overview", None)

    if hook is None:
        return None, []

    try:
        result = hook(software, hardware, t) or {}
    except Exception:
        logger.exception("Acquisition overview of %s failed", method_name)
        return None, []

    return result.get("summary"), list(result.get("warnings") or [])
