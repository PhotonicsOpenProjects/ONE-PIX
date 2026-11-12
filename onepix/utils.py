import base64
import json
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
import orjson


# ==========================================================
# IMAGE DETECTION
# ==========================================================
def is_image_like(arr):
    """
    Detect if ndarray is probably an image.

    Rules:
    - RGB / RGBA ndarray
    - Large 2D array (mask / grayscale)
    """

    if not isinstance(arr, np.ndarray):

        return False

    # ------------------------------------------------------
    # RGB / RGBA
    # ------------------------------------------------------
    if (
        arr.ndim == 3
        and arr.shape[2] in [1, 3, 4]
    ):

        return True

    # ------------------------------------------------------
    # Large grayscale / mask
    # ------------------------------------------------------
    if (
        arr.ndim == 2
        and arr.shape[0] > 64
        and arr.shape[1] > 64
    ):

        return True

    return False


# ==========================================================
# ATOMIC WRITE OF A CONFIGURATION FILE
# ==========================================================
def write_json_atomic(path, data, indent=2, ensure_ascii=True):
    """Write `data` as JSON to `path` so that the file is never left half written.

    The text is produced first (an object that cannot be serialised fails before the disk is
    touched), written to a temporary file in the same folder, flushed to disk, then moved over the
    destination in one step: a crash or a full disk leaves the previous file as it was. The
    permissions of an existing file are kept. Meant for the configuration files, which the hardware
    cannot start without."""
    path = Path(os.path.realpath(path))
    text = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)

    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            tmp.write(text)
            tmp.flush()
            os.fsync(tmp.fileno())
        try:
            os.chmod(tmp_name, path.stat().st_mode & 0o7777)
        except FileNotFoundError:
            umask = os.umask(0)
            os.umask(umask)
            os.chmod(tmp_name, 0o666 & ~umask)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


# ==========================================================
# FOLDER DIALOG
# ==========================================================
def ask_directory(title, initialdir):
    """Folder chosen in a dialog window ("" when cancelled).

    tkinter is imported here, not at module level: a server without a screen, a minimal Python or a
    container has no tkinter, and the web interface and the command line never open this dialog."""
    try:
        from tkinter import Tk
        from tkinter.filedialog import askdirectory
    except ImportError as exc:
        raise RuntimeError(
            "A folder dialog needs tkinter, which is not installed (Debian and Raspberry Pi OS: "
            "sudo apt install python3-tk). Pass the folder explicitly instead."
        ) from exc

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", 1)
    try:
        return askdirectory(title=title, initialdir=initialdir)
    finally:
        root.destroy()


# ==========================================================
# SERIALIZATION
# ==========================================================
def serialize_for_json(obj):
    """
    Smart recursive serializer for ONE-PIX.

    Handles:
    - ndarray
    - images
    - masks
    - numpy scalars
    - dict/list recursion
    """

    # ======================================================
    # NUMPY ARRAY
    # ======================================================
    if isinstance(obj, np.ndarray):

        arr = obj

        # --------------------------------------------------
        # IMAGE-LIKE ARRAYS
        # --------------------------------------------------
        if is_image_like(arr):

            original_dtype = str(arr.dtype)

            # bool mask -> uint8
            if arr.dtype == bool:

                arr = (
                    arr.astype(np.uint8)
                    * 255
                )

            # image normalization
            elif arr.dtype != np.uint8:

                arr = arr.astype(np.uint8)

            success, buffer = cv2.imencode(
                ".png",
                arr
            )

            if not success:

                raise ValueError(
                    "PNG encoding failed"
                )

            return {
                "__type__": "image_png",
                "dtype": original_dtype,
                "shape": arr.shape,
                "data": base64.b64encode(
                    buffer
                ).decode("utf-8")
            }

        # --------------------------------------------------
        # NORMAL ARRAYS
        # --------------------------------------------------
        else:

            # float optimization
            if arr.dtype == np.float64:

                arr = arr.astype(
                    np.float32
                )

            # int optimization
            if arr.dtype == np.int64:

                arr = arr.astype(
                    np.int32
                )

            return {
                "__type__": "ndarray",
                "dtype": str(arr.dtype),
                "shape": arr.shape,
                "data": arr.tolist()
            }

    # ======================================================
    # NUMPY SCALARS
    # ======================================================
    if isinstance(obj, np.integer):

        return int(obj)

    if isinstance(obj, np.floating):

        return float(obj)

    if isinstance(obj, np.bool_):

        return bool(obj)

    # ======================================================
    # LIST
    # ======================================================
    if isinstance(obj, list):

        return [
            serialize_for_json(x)
            for x in obj
        ]

    # ======================================================
    # DICT
    # ======================================================
    if isinstance(obj, dict):

        return {
            k: serialize_for_json(v)
            for k, v in obj.items()
        }

    # ======================================================
    # PATH
    # ======================================================
    if isinstance(obj, Path):

        return str(obj)

    # ======================================================
    # FALLBACK
    # ======================================================
    return obj


# ==========================================================
# DESERIALIZATION
# ==========================================================
def deserialize_from_json(obj):
    """
    Restore recursively serialized ONE-PIX objects.
    """

    # ======================================================
    # IMAGE PNG
    # ======================================================
    if (
        isinstance(obj, dict)
        and obj.get("__type__")
        == "image_png"
    ):

        img_bytes = base64.b64decode(
            obj["data"]
        )

        img_array = np.frombuffer(
            img_bytes,
            dtype=np.uint8
        )

        img = cv2.imdecode(
            img_array,
            cv2.IMREAD_UNCHANGED
        )

        # restore bool masks
        if obj["dtype"] == "bool":

            img = img > 0

        return img

    # ======================================================
    # NORMAL NDARRAY
    # ======================================================
    if (
        isinstance(obj, dict)
        and obj.get("__type__")
        == "ndarray"
    ):

        return np.asarray(
            obj["data"],
            dtype=obj["dtype"]
        )

    # ======================================================
    # LIST
    # ======================================================
    if isinstance(obj, list):

        return [
            deserialize_from_json(x)
            for x in obj
        ]

    # ======================================================
    # DICT
    # ======================================================
    if isinstance(obj, dict):

        return {
            k: deserialize_from_json(v)
            for k, v in obj.items()
        }

    return obj


# ==========================================================
# GENERIC JSON SAVE
# ==========================================================
def save_dict_json(
    data_dict,
    filepath
):
    """
    Generic ONE-PIX JSON save.
    """

    filepath = Path(filepath)

    # ------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------
    serialized_data = (
        serialize_for_json(
            data_dict
        )
    )

    # ------------------------------------------------------
    # SAVE
    # ------------------------------------------------------
    # OPT_INDENT_2: multi-line, human-readable JSON instead of one long
    # line - these files are opened and inspected directly (metadata,
    # traceability), not just re-loaded by the app.
    with open(filepath, "wb") as f:

        f.write(
            orjson.dumps(
                serialized_data,
                option=orjson.OPT_INDENT_2,
            )
        )


# ==========================================================
# GENERIC JSON LOAD
# ==========================================================
def load_dict_json(filepath):
    """
    Generic ONE-PIX JSON load.
    """

    filepath = Path(filepath)

    # ------------------------------------------------------
    # LOAD
    # ------------------------------------------------------
    with open(filepath, "rb") as f:

        data = orjson.loads(
            f.read()
        )

    # ------------------------------------------------------
    # DESERIALIZATION
    # ------------------------------------------------------
    return deserialize_from_json(
        data
    )