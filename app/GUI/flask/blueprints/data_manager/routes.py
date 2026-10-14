from flask import (
    render_template,
    jsonify,
    request,
    send_file
)

from . import bp

from pathlib import Path

import io
import zipfile

from security import safe_path, secure_filename


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
# DOWNLOAD SELECTED
# ==========================================

@bp.route(
    "/download",
    methods=["POST"]
)
def download_files():

    payload = request.json

    filenames = payload.get(
        "files",
        []
    )

    if not filenames:

        return (
            jsonify({
                "error":
                "No files selected"
            }),
            400
        )

    # ======================================
    # BUILD ZIP
    # ======================================

    memory_file = io.BytesIO()

    with zipfile.ZipFile(
        memory_file,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zf:

        for filename in filenames:

            filepath = safe_path(
                SAVE_PATH,
                filename
            )

            if filepath is not None and filepath.exists():

                zf.write(
                    filepath,
                    arcname=filepath.name
                )

    memory_file.seek(0)

    # ======================================
    # RETURN ZIP
    # ======================================

    return send_file(

        memory_file,

        mimetype="application/zip",

        as_attachment=True,

        download_name=
        "onepix_data.zip"
    )


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