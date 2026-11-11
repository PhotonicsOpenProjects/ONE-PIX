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
  min, max, step
            bounds of a number input (the browser refuses values outside)
  group     title key (settings_group.<group> in i18n.py) of the section
            a non-advanced field is shown under. Forms where no field
            has a group render as one flat grid.
"""

FIELD_META = {
    # ---- software (acquisition_parameters.json) ----
    "imaging_method_name": {},
    "integration_time_ms": {"unit": "ms"},
    "spectro_scans2avg": {},
    "dynamic_tint": {},

    # ---- hardware (hardware_config.json) ----
    "name_spectro": {"group": "devices"},
    "name_camera": {"group": "devices"},
    "height": {"unit": "px", "group": "image"},
    "width": {"unit": "px", "group": "image"},
    "wl_lim": {"unit": "nm", "widget": "range", "group": "image"},
    "periode_pattern": {"unit": "ms", "min": 0, "group": "projection"},
    "latency_hiding_ms": {"unit": "ms", "min": 0, "group": "projection"},
    "max_gray_level": {"min": 1, "max": 255, "step": 1, "group": "projection"},
    "gray_response_path": {"group": "projection"},
    "proj_position": {"advanced": True},
    "corregistration_array": {"advanced": True},
    "max_width": {"unit": "px", "advanced": True},
    "max_height": {"unit": "px", "advanced": True},
}
