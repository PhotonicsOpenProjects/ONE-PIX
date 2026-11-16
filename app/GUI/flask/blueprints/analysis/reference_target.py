"""Absolute reflectance of the reference target.

reflectance_normalization divides a spectrum by the reference spectrum: the result is a reflectance
*relative to the target*, so it is right only if the target reflects 100 % at every wavelength. A real
target (a Spectralon, a grey card...) reflects less, and not equally at every wavelength. Its true
reflectance R(lambda) is folded into the reference spectrum when this one is saved:

    stored reference = measured reference / R(lambda)
    signal / stored reference = signal * R(lambda) / measured reference

so the plugin, which stays unchanged, ends up with the absolute reflectance. R(lambda) comes from:

    a constant   the "Lambertian" target: the same percentage at every wavelength, typed by the user
    a table      wavelengths (nm) + reflectance, uploaded from the target's calibration certificate,
                 interpolated on the wavelengths of the measurement
"""
import json
import re

import numpy as np

MAX_TABLE_POINTS = 100_000
_SEPARATORS = re.compile(r"[;,\t ]+")


def parse_table(text):
    """(wavelengths_nm, reflectance) of an uploaded calibration table, reflectance as fractions (0-1).

    Accepted: a JSON {"wavelengths": [...], "reflectance": [...]} (or "spectrum" / "values"), or text
    with one "wavelength reflectance" pair per line separated by spaces, tabs, commas or semicolons
    (a CSV). Lines that are not two numbers (headers, comments, units) are skipped. A decimal comma
    ("0,95") is not supported, since the comma already separates the columns.
    Reflectance given in percent (some value above 1.5) is divided by 100.
    Raises ValueError, with a message fit for the user.
    """
    text = (text or "").lstrip("﻿")
    stripped = text.strip()
    if not stripped:
        raise ValueError("The file is empty.")

    if stripped[0] in "{[":
        try:
            wavelengths, reflectance = _from_json(json.loads(stripped))
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f"Unreadable JSON table: {exc}") from exc
    else:
        wavelengths, reflectance = _from_text(stripped)

    return _clean(wavelengths, reflectance)


def _from_json(data):
    if isinstance(data, dict):
        wl = data.get("wavelengths")
        for key in ("reflectance", "spectrum", "values"):
            if key in data:
                return wl, data[key]
        raise KeyError("no 'reflectance' list")
    # [[wl, r], [wl, r], ...]
    pairs = np.asarray(data, dtype=float)
    if pairs.ndim != 2 or pairs.shape[1] != 2:
        raise ValueError("expected a list of [wavelength, reflectance] pairs")
    return pairs[:, 0], pairs[:, 1]


def _from_text(text):
    wavelengths, reflectance = [], []
    for line in text.splitlines():
        fields = [f for f in _SEPARATORS.split(line.strip()) if f]
        if len(fields) < 2:
            continue
        try:
            wl, r = float(fields[0]), float(fields[1])
        except ValueError:
            continue  # header, unit line, comment
        wavelengths.append(wl)
        reflectance.append(r)
        if len(wavelengths) > MAX_TABLE_POINTS:
            raise ValueError("The file has too many lines.")
    return wavelengths, reflectance


def _clean(wavelengths, reflectance):
    try:
        wl = np.asarray(wavelengths, dtype=float)
        r = np.asarray(reflectance, dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError("The table must hold numbers only.") from exc
    if wl.ndim != 1 or wl.shape != r.shape:
        raise ValueError("Wavelengths and reflectance must be two lists of the same length.")
    if wl.size < 2:
        raise ValueError("At least two wavelengths are needed to interpolate the reflectance.")
    if wl.size > MAX_TABLE_POINTS:
        raise ValueError("The file has too many lines.")
    if not (np.all(np.isfinite(wl)) and np.all(np.isfinite(r))):
        raise ValueError("The table holds values that are not numbers (nan, inf).")

    order = np.argsort(wl, kind="stable")
    wl, r = wl[order], r[order]
    if np.any(np.diff(wl) <= 0):
        raise ValueError("The wavelengths must be all different.")

    if r.max() > 1.5:  # percent
        r = r / 100.0
    if r.min() <= 0 or r.max() > 1.5:
        raise ValueError(
            "The reflectance must be above 0 and at most 100 % at every wavelength."
        )
    return wl, r


def lambertian_reflectance(percent):
    """The constant reflectance (fraction) of a Lambertian target of `percent` %."""
    try:
        value = float(percent)
    except (TypeError, ValueError) as exc:
        raise ValueError("The reflectance percentage must be a number.") from exc
    if not np.isfinite(value) or not 0 < value <= 100:
        raise ValueError("The reflectance percentage must be above 0 and at most 100.")
    return value / 100.0


def target_reflectance(target, wavelengths):
    """R(lambda), as fractions, on `wavelengths` for the `target` description of a request.

    target: None -> None (relative reflectance, as before)
            {"mode": "lambertian", "percent": 99}
            {"mode": "table", "wavelengths": [...], "reflectance": [...]}   (parse_table() output)
    A table has to cover the whole measured range: nothing is extrapolated.
    """
    if not target or target.get("mode") in (None, "none"):
        return None
    wavelengths = np.asarray(wavelengths, dtype=float)

    mode = target.get("mode")
    if mode == "lambertian":
        return np.full(wavelengths.shape, lambertian_reflectance(target.get("percent")))

    if mode == "table":
        table_wl, table_r = _clean(target.get("wavelengths"), target.get("reflectance"))
        low, high = float(wavelengths.min()), float(wavelengths.max())
        if low < table_wl[0] - 1e-6 or high > table_wl[-1] + 1e-6:
            raise ValueError(
                f"The target's table covers {table_wl[0]:g}-{table_wl[-1]:g} nm but the measurement "
                f"spans {low:g}-{high:g} nm."
            )
        return np.interp(wavelengths, table_wl, table_r)

    raise ValueError(f"Unknown target mode: {mode!r}")


def apply_target(spectrum, wavelengths, target):
    """(reference spectrum to store, description of the target to store with it).

    The spectrum divided by R(lambda) - see the module docstring. Without a target, unchanged.
    """
    r = target_reflectance(target, wavelengths)
    if r is None:
        return np.asarray(spectrum, dtype=float), None
    description = {"mode": target["mode"]}
    if target["mode"] == "lambertian":
        description["percent"] = float(target["percent"])
    else:
        description["mean_reflectance"] = float(np.mean(r))
    return np.asarray(spectrum, dtype=float) / r, description
