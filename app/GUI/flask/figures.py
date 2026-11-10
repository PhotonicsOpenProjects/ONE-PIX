"""Result images (result2plot) rendered as the PNG the pages show.

Shared by the Acquisition and Analysis pages. A result image can be
anything from a few pixels (5x5) to a camera-sized frame, square or
much wider than tall. A fixed-size figure, scaled down by the browser
to fit the viewer, left a thin strip lost in blank space, graduations
piled on top of each other along its short side, and axis text whose
size depended on the image's shape - a few pixels high for a square
image in a short viewer.

Here the page says how much room its viewer has (``box``, in CSS
pixels, and the screen's pixel ratio), and the figure is drawn at
exactly that size: the image as large as fits with its proportions
kept, graduations spaced for the room each axis actually gets, axis
text at a fixed 11 CSS pixels, crisp pixels for small images, and a
transparent background so it sits on the page's own, light or dark.
"""

import io

import numpy as np

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


# Room assumed when the page doesn't say (CSS pixels).
DEFAULT_BOX = (960, 640)
# Bounds on what a page may ask for, so a bogus request can't make the
# server draw a gigantic image.
MIN_BOX, MAX_BOX = 120, 3000
MAX_SCALE = 3.0
MAX_OUTPUT_PIXELS = 12_000_000

# Mid gray: readable on the light and the dark theme alike.
AXIS_COLOR = "#7a8494"
FONT_PX = 11

# Room around the image for its graduations (CSS pixels): left, right,
# top, bottom.
AXES_MARGINS = (54, 14, 10, 42)

# One graduation per this many CSS pixels of axis, about.
TICK_SPACING_X = 90
TICK_SPACING_Y = 60


def displayable(img):
    """(array imshow can show, colormap or None).

    2-D (one value per pixel): shown with a colormap. RGB/RGBA: uint8
    as is; floats taken as 0-1 (scaled to 0-255) when they fit, else as
    0-255, clipped either way - a plain uint8 cast wrapped values
    around and turned a 0-1 image black."""

    img = np.squeeze(np.asarray(img))

    if img.ndim == 2:
        return img, "viridis"

    if img.ndim != 3 or img.shape[2] not in (3, 4):
        raise ValueError(f"Cannot display an image of shape {img.shape}")

    if img.dtype == np.uint8:
        return img, None

    values = np.nan_to_num(img.astype(float), nan=0.0, posinf=0.0, neginf=0.0)
    if values.size and values.max() <= 1.0:
        values = values * 255.0

    return np.clip(values, 0, 255).astype(np.uint8), None


def parse_box(args):
    """(box, scale) from a request's w, h (CSS pixels) and dpr query
    arguments, each falling back to the default when missing or not a
    number."""

    def number(name, default, low, high):
        try:
            value = float(args.get(name, default))
        except (TypeError, ValueError):
            return default
        if not np.isfinite(value):
            return default
        return min(max(value, low), high)

    box = (
        number("w", DEFAULT_BOX[0], MIN_BOX, MAX_BOX),
        number("h", DEFAULT_BOX[1], MIN_BOX, MAX_BOX),
    )
    return box, number("dpr", 1.0, 1.0, MAX_SCALE)


def render_png(img, axes=True, box=None, scale=1.0):
    """PNG bytes of ``img`` fitting ``box`` - (width, height) in CSS
    pixels - at ``scale`` device pixels per CSS pixel. axes: row/column
    pixel graduations around the image."""

    img, cmap = displayable(img)
    height, width = img.shape[:2]

    box_w, box_h = box or DEFAULT_BOX
    left, right, top, bottom = AXES_MARGINS if axes else (0, 0, 0, 0)

    # The image as large as fits, proportions kept.
    fit = min(
        max(box_w - left - right, 16) / width,
        max(box_h - top - bottom, 16) / height,
    )
    image_w, image_h = width * fit, height * fit
    fig_w, fig_h = image_w + left + right, image_h + top + bottom

    scale = min(scale, (MAX_OUTPUT_PIXELS / (fig_w * fig_h)) ** 0.5)
    scale = max(scale, 0.5)

    # Sizes in inches of 72 points, drawn at 72 * scale dpi: one point
    # is one CSS pixel, so FONT_PX points read as FONT_PX pixels.
    fig = plt.figure(figsize=(fig_w / 72, fig_h / 72), dpi=72 * scale)

    try:
        ax = fig.add_axes([left / fig_w, bottom / fig_h, image_w / fig_w, image_h / fig_h])

        # "antialiased": nearest neighbour when enlarging (a 5x5 image
        # keeps 25 sharp squares), smoothing when reducing. The axes
        # already have the image's proportions: aspect "auto" fills them.
        ax.imshow(img, cmap=cmap, interpolation="antialiased", aspect="auto")

        if axes:
            ax.xaxis.set_major_locator(
                MaxNLocator(nbins=max(2, round(image_w / TICK_SPACING_X)), integer=True)
            )
            ax.yaxis.set_major_locator(
                MaxNLocator(nbins=max(2, round(image_h / TICK_SPACING_Y)), integer=True)
            )

            ax.set_xlabel("Column", fontsize=FONT_PX, color=AXIS_COLOR, labelpad=3)
            ax.set_ylabel("Row", fontsize=FONT_PX, color=AXIS_COLOR, labelpad=3)
            ax.tick_params(colors=AXIS_COLOR, labelsize=FONT_PX, length=3, pad=2)

            for spine in ax.spines.values():
                spine.set_color(AXIS_COLOR)
                spine.set_alpha(0.6)
        else:
            ax.axis("off")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True)
        return buf.getvalue()

    finally:
        plt.close(fig)
