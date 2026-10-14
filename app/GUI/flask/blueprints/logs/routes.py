import os

from flask import render_template, jsonify, request

from . import bp
from onepix.logging_config import log_dir

LOG_FILE_PATH = os.path.join(log_dir, "app.log")


def tail_lines(path, max_lines=300, max_bytes=512 * 1024):
    """Return the last `max_lines` lines of `path` without reading the
    whole (potentially multi-MB) file - only the last `max_bytes` are
    read from disk."""
    if not os.path.exists(path):
        return []

    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        read_size = min(size, max_bytes)
        f.seek(size - read_size)
        data = f.read()

    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()

    # The first line is likely a partial line since we seeked into the
    # middle of the file - drop it rather than show a truncated line.
    if read_size < size and lines:
        lines = lines[1:]

    return lines[-max_lines:]


@bp.route("/")
def logs_page():
    return render_template("logs.html")


@bp.route("/api/tail")
def logs_tail():
    try:
        lines = int(request.args.get("lines", 400))
    except (TypeError, ValueError):
        lines = 400

    lines = max(1, min(lines, 2000))

    return jsonify({"lines": tail_lines(LOG_FILE_PATH, max_lines=lines)})
