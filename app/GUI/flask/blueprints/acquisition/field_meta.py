"""Presentation metadata for the generic settings forms
(templates/settings_page.html).

Labels and help text are translated in i18n.py under
settings_field.<key>.label / .help - this module only holds what isn't
language-specific. A key missing from here still renders, as a plain
field with a label derived from the key itself. Imaging method plugins
add the metadata of their own fields (gui_plugins.py's FIELD_META).

  unit      shown as a suffix next to number inputs
  advanced  moved into the collapsed "Advanced settings" section:
            calibration outputs, metadata-only flags and other values
            most users should never need to touch
  widget    "range": a two-number list ([min, max]) edited as two
            separate inputs instead of raw JSON
"""

FIELD_META = {
    # ---- software (acquisition_parameters.json) ----
    "imaging_method_name": {},
    "integration_time_ms": {"unit": "ms"},
    "spectro_scans2avg": {},
    "Normalisation": {"advanced": True},
    "dynamic_tint": {"advanced": True},

    # ---- hardware (hardware_config.json) ----
    "name_spectro": {},
    "name_camera": {},
    "height": {"unit": "px"},
    "width": {"unit": "px"},
    "wl_lim": {"unit": "nm", "widget": "range"},
    "proj_position": {"advanced": True},
    "corregistration_array": {"advanced": True},
    "normalisation_path": {"advanced": True},
    "max_width": {"unit": "px", "advanced": True},
    "max_height": {"unit": "px", "advanced": True},
}
