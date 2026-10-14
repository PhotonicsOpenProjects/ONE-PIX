"""Zone maps for zone-based results.

Some imaging methods (HAS, for one) don't measure a spectrum per pixel
but one per zone of the scene: their result holds "spectra" (one row per
zone), "masks" (one per zone, same order), optionally "cluster_name" and
the "rgb" photo the zones were drawn on. Like the spectra charts, the
zone map is driven by that data shape alone, whatever method produced
it.

The browser composes the map itself (static/js/zone-map.js) from the
photo and a label map, so each zone gets exactly the color of its
spectrum in the chart and can be identified by hovering it.
"""

import io

import cv2
import numpy as np

from PIL import Image

# Label map pixels hold the zone index + 1 in one byte (0 = no zone).
MAX_ZONES = 254


def zone_data(result):
    """{"masks": (n, H, W) bool, "names": [...], "rgb": (H, W, 3) uint8
    or None} for a zone-based result, else None."""

    if not result or "masks" not in result or "spectra" not in result:
        return None

    masks = [np.asarray(mask) for mask in result["masks"]]
    spectra = np.asarray(result["spectra"])

    # Zone i must be spectrum i (and series i in the chart).
    if not masks or len(masks) != len(spectra) or len(masks) > MAX_ZONES:
        return None

    if any(mask.ndim != 2 for mask in masks):
        return None

    rgb = result.get("rgb")
    rgb = np.asarray(rgb) if rgb is not None else None

    if rgb is not None and rgb.ndim == 3 and rgb.shape[2] in (3, 4):
        rgb = rgb[:, :, :3].astype(np.uint8)
        height, width = rgb.shape[:2]
    else:
        rgb = None
        height, width = masks[0].shape

    stack = np.zeros((len(masks), height, width), dtype=bool)

    for i, mask in enumerate(masks):
        if mask.shape != (height, width):
            mask = cv2.resize(
                (mask > 0).astype(np.uint8), (width, height),
                interpolation=cv2.INTER_NEAREST,
            )
        stack[i] = mask > 0

    names = list(result.get("cluster_name") or [])
    names = [str(names[i]) if i < len(names) and names[i] else "" for i in range(len(masks))]

    return {"masks": stack, "names": names, "rgb": rgb}


def _label_anchors(mask, max_parts=3):
    """[[x, y], ...] where the zone's labels read best: the point
    deepest inside its largest connected part, then inside each other
    part covering at least 2 % of the image, up to max_parts (automatic
    segmentations often split a zone in pieces). [] for an empty
    zone."""

    if not mask.any():
        return []

    _, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8
    )
    areas = stats[1:, cv2.CC_STAT_AREA]
    order = np.argsort(areas)[::-1][:max_parts]
    min_area = mask.size * 0.02
    anchors = []

    for k in order:
        if anchors and areas[k] < min_area:
            break

        x0, y0, w, h = stats[k + 1, :4]
        part = (labels[y0:y0 + h, x0:x0 + w] == k + 1).astype(np.uint8)

        # Padded so the part's bounding box edge counts as its edge too.
        distance = cv2.distanceTransform(
            np.pad(part, 1), cv2.DIST_L2, 5
        )[1:-1, 1:-1]
        y, x = np.unravel_index(int(np.argmax(distance)), distance.shape)
        anchors.append([int(x0 + x), int(y0 + y)])

    return anchors


def summary(result):
    """JSON for GET .../zones: image size and, per zone, its name, label
    anchors and share of the image."""

    data = zone_data(result)

    if data is None:
        return {"available": False}

    masks = data["masks"]
    _, height, width = masks.shape

    return {
        "available": True,
        "width": width,
        "height": height,
        "has_rgb": data["rgb"] is not None,
        "zones": [
            {
                "name": data["names"][i],
                "anchors": _label_anchors(mask),
                "area": float(mask.mean()),
            }
            for i, mask in enumerate(masks)
        ],
    }


def label_map_png(result):
    """PNG whose pixel values are the zone index + 1 (0 = no zone), or
    None. Overlapping zones: the later one wins."""

    data = zone_data(result)

    if data is None:
        return None

    masks = data["masks"]
    labels = np.zeros(masks.shape[1:], dtype=np.uint8)

    for i, mask in enumerate(masks):
        labels[mask] = i + 1

    buf = io.BytesIO()
    Image.fromarray(labels).save(buf, format="PNG")
    return buf.getvalue()


def rgb_jpeg(result):
    """The photo the zones were drawn on, as JPEG, or None."""

    data = zone_data(result)

    if data is None or data["rgb"] is None:
        return None

    buf = io.BytesIO()
    Image.fromarray(data["rgb"]).save(buf, format="JPEG", quality=90)
    return buf.getvalue()
