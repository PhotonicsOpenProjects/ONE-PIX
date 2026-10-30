"""Linearisation of a projector's gray-level response.

A projector's light is not proportional to the gray level it is given (black crush, S-shaped curve):
a mid-gray pattern can give a quarter of the light of white instead of a half. Methods that project
gray levels (the Fourier ones) assume the light is proportional to the pattern, so a measured curve
is inverted here: each pattern level is replaced by the gray level that gives the light it asks for.
Binary patterns (Hadamard) are not changed, whatever the white level.

The curve (levels and the light received at each, see app/cli/probe_gray_response.py) is a JSON file
referenced by "gray_response_path" in hardware_config.json.
"""
import json
import logging

import numpy as np

logger = logging.getLogger(__name__)

# a level whose light is below this fraction of the white's is considered black
DARK_FRACTION = 0.002


def build_lut(levels, response, white_level=255):
    """256 gray levels (uint8) such that the light of lut[p] is p / 255 of the light of `white_level`.

    `levels` and `response` give the measured light at each gray level (any scale). Pattern 0 stays
    level 0 and pattern 255 becomes `white_level`."""
    levels = np.asarray(levels, np.float64)
    response = np.asarray(response, np.float64)
    order = np.argsort(levels)
    levels, response = levels[order], np.maximum.accumulate(np.clip(response[order], 0.0, None))
    top = float(np.interp(white_level, levels, response))
    if top <= 0:
        raise ValueError("the measured response gives no light at the white level")
    lit = response > DARK_FRACTION * top
    xs, ys = response[lit], levels[lit]
    keep = np.concatenate([[True], np.diff(xs) > 0])            # strictly increasing to be invertible
    xs, ys = xs[keep], ys[keep]
    last_dark = levels[~lit].max() if (~lit).any() else levels[0]
    lut = np.interp(np.arange(256) / 255.0 * top, np.concatenate([[0.0], xs]), np.concatenate([[last_dark], ys]))
    lut[0] = 0
    lut[255] = white_level
    return np.clip(np.round(lut), 0, 255).astype(np.uint8)


def suggest_white_level(levels, response, current_level, light_factor):
    """The gray level whose light is `light_factor` (< 1: dimmer) times that of `current_level`, from a
    measured curve. None if the curve gives no light at the current level or the target is in the dead
    zone."""
    levels = np.asarray(levels, np.float64)
    response = np.asarray(response, np.float64)
    order = np.argsort(levels)
    levels, response = levels[order], np.maximum.accumulate(np.clip(response[order], 0.0, None))
    current = float(np.interp(current_level, levels, response))
    if current <= 0 or light_factor <= 0:
        return None
    target = current * light_factor
    lit = response > DARK_FRACTION * current
    xs, ys = response[lit], levels[lit]
    keep = np.concatenate([[True], np.diff(xs) > 0])
    xs, ys = xs[keep], ys[keep]
    if target < xs[0]:
        return None
    return int(np.clip(round(float(np.interp(target, xs, ys))), 1, 255))


def load_lut(path, white_level=255):
    with open(path, encoding="utf-8") as f:
        curve = json.load(f)
    return build_lut(curve["levels"], curve["response"], white_level)


def apply_lut(image, lut):
    """Pattern -> gray levels to display. uint8 images use the table; floating point images (levels
    in 0-1) are interpolated in it; other types are returned unchanged."""
    if image.dtype == np.uint8:
        return lut[image]
    if np.issubdtype(image.dtype, np.floating):
        return np.interp(np.clip(image, 0.0, 1.0) * 255.0, np.arange(256), lut.astype(np.float64)) / 255.0
    return image
