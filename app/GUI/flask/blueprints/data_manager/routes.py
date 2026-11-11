from flask import (
    render_template,
    jsonify,
    request,
    send_file
)

from . import bp

from pathlib import Path

import io
import json
import logging
import tempfile
import zipfile

from security import safe_path, secure_filename

from onepix import export as fair_export
from onepix import fair

logger = logging.getLogger(__name__)


# ==========================================
# STORAGE PATH
# ==========================================

SAVE_PATH = (
    Path(__file__)
    .resolve()
    .parent.parent.parent.parent.parent.parent
    / "measure"
)

SAVE_PATH.mkdir(
    exist_ok=True
)


# ==========================================
# PAGE
# ==========================================

@bp.route("/")
def data_manager_page():

    return render_template(
        "data_manager.html"
    )


# ==========================================
# LIST FILES
# ==========================================

@bp.route("/files")
def list_files():

    # Newest first by modification time - the filenames embed dates as
    # dd_mm_yyyy, which doesn't sort chronologically by name.
    files = sorted(
        SAVE_PATH.glob("*.json"),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )

    results = []

    for f in files:

        file_type = "analysis"

        if f.name.startswith(
            "reconstruction_"
        ):

            file_type = "reconstruction"

        results.append({

            "name": f.name,

            "size":
                round(
                    f.stat().st_size
                    / 1024,
                    2
                ),

            "type":
                file_type,

            "modified":
                f.stat().st_mtime
        })

    return jsonify(results)


# ==========================================
# UPLOAD FILES
# ==========================================

@bp.route(
    "/upload",
    methods=["POST"]
)
def upload_files():

    uploaded_files = request.files.getlist(
        "files"
    )

    if not uploaded_files:

        return (
            jsonify({
                "error":
                "No files uploaded"
            }),
            400
        )

    uploaded_names = []

    for file in uploaded_files:

        if (
            file.filename
            and
            file.filename.endswith(
                ".json"
            )
        ):

            clean_name = secure_filename(
                file.filename
            )

            filepath = safe_path(
                SAVE_PATH,
                clean_name
            )

            if filepath is None:
                continue

            file.save(filepath)

            uploaded_names.append(
                filepath.name
            )

    return jsonify({

        "success": True,

        "uploaded":
            uploaded_names
    })

# ==========================================
# DELETE FILES
# ==========================================

@bp.route(
    "/delete",
    methods=["POST"]
)
def delete_files():

    payload = request.json

    filenames = payload.get(
        "files",
        []
    )

    deleted = []

    for filename in filenames:

        filepath = safe_path(
            SAVE_PATH,
            filename
        )

        if filepath is not None and filepath.exists():

            filepath.unlink()

            deleted.append(
                filepath.name
            )

    return jsonify({

        "success": True,

        "deleted":
            deleted
    })


# ==========================================
# FAIR EXPORT
# Open formats (HDF5, NumPy, MATLAB, ENVI, TIFF...) in a package with
# machine-readable metadata - see onepix/export.py and onepix/fair.py.
# ==========================================

@bp.route("/fair/formats")
def fair_formats():

    return jsonify(fair_export.available_formats())


@bp.route("/fair/config", methods=["GET"])
def fair_config():

    return jsonify({
        "config": fair.load_fair_config(),
        "licenses": fair.LICENSES,
    })


@bp.route("/fair/config", methods=["POST"])
def fair_config_save():

    try:

        config = fair.save_fair_config(request.get_json(silent=True) or {})

    except ValueError as exc:

        # "orcid" | "email" | "license": the page words the message itself
        return jsonify({"error": str(exc)}), 400

    return jsonify({"config": config})


@bp.route("/export", methods=["POST"])
def export_files():

    payload = request.get_json(silent=True) or {}

    filenames = payload.get("files", [])
    formats = payload.get("formats", [])

    if not filenames or not formats:

        return jsonify({"error": "No files or formats selected"}), 400

    unknown = [f for f in formats if f not in fair_export.FORMATS]

    if unknown:

        return jsonify({"error": f"Unknown format: {unknown[0]}"}), 400

    sources = []

    for filename in filenames:

        filepath = safe_path(SAVE_PATH, filename)

        if filepath is not None and filepath.is_file() and filepath.suffix == ".json":

            sources.append(filepath)

    if not sources:

        return jsonify({"error": "File not found"}), 404

    config = fair.load_fair_config()

    skipped = {}

    archive = io.BytesIO()

    with tempfile.TemporaryDirectory() as tmp:

        for source in sources:

            try:

                result = fair_export.export_dataset(source, formats, tmp, config)

            except Exception as exc:

                logger.exception("FAIR export of %s failed", source.name)
                skipped[source.name] = f"failed: {exc}"
                continue

            if result["skipped"]:

                skipped[source.name] = result["skipped"]

        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:

            for path in sorted(Path(tmp).rglob("*")):

                if path.is_file():

                    zf.write(path, arcname=path.relative_to(tmp))

    if not archive.getbuffer().nbytes or len(archive.getvalue()) < 100:

        return jsonify({"error": "Nothing exported", "skipped": skipped}), 500

    archive.seek(0)

    response = send_file(
        archive,
        mimetype="application/zip",
        as_attachment=True,
        download_name="onepix_fair_export.zip"
    )

    # Which formats could not be produced (missing library, no datacube...),
    # read by the page to tell the user.
    response.headers["X-Export-Skipped"] = json.dumps(skipped)

    return response
