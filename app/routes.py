import io
import re
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, send_file, session
from werkzeug.utils import secure_filename

from app.services.pdf_service import PDFValidationError, combine_pdfs, validate_pdf
from app.utils.file_utils import allowed_file


main_bp = Blueprint("main", __name__)
WORKSPACE_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def _workspace_dir():
    """Return the isolated upload directory for the current browser session."""
    root = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    workspace_id = session.get("workspace_id")
    if not isinstance(workspace_id, str) or not WORKSPACE_ID_PATTERN.fullmatch(workspace_id):
        workspace_id = uuid.uuid4().hex
        session["workspace_id"] = workspace_id

    workspace = (root / workspace_id).resolve()
    if workspace.parent != root:
        raise RuntimeError("Invalid workspace path")
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _stored_path(file_id):
    """Resolve a server-issued file id without allowing path traversal."""
    if not isinstance(file_id, str) or Path(file_id).name != file_id:
        return None
    if not file_id.lower().endswith(".pdf") or file_id.startswith("combined-"):
        return None

    workspace = _workspace_dir()
    path = (workspace / file_id).resolve()
    if path.parent != workspace or not path.is_file():
        return None
    return path


def _file_details(path):
    """Serialize an internal filename for the browser without exposing its id format."""
    stored_name = path.name
    original_name = stored_name.split("_", 1)[1] if "_" in stored_name else stored_name
    return {
        "id": stored_name,
        "name": original_name,
        "size": path.stat().st_size,
    }


def _workspace_files():
    workspace = _workspace_dir()
    return sorted(
        (path for path in workspace.glob("*.pdf") if not path.name.startswith("combined-")),
        key=lambda path: path.stat().st_mtime,
    )


def _error(message, status=400):
    return jsonify({"error": message}), status


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/files", methods=["GET"])
def list_files():
    return jsonify({"files": [_file_details(path) for path in _workspace_files()]})


@main_bp.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("pdfs")
    if not files or all(not file.filename for file in files):
        return _error("Choose at least one PDF file to upload.")

    existing_count = len(_workspace_files())
    if existing_count + len(files) > current_app.config["MAX_FILES"]:
        return _error(f"You can upload up to {current_app.config['MAX_FILES']} files at a time.")

    workspace = _workspace_dir()
    accepted = []
    rejected = []

    for uploaded_file in files:
        original_name = secure_filename(uploaded_file.filename or "")
        if not original_name or not allowed_file(original_name):
            rejected.append({"name": uploaded_file.filename or "Unnamed file", "reason": "PDF files only"})
            continue

        stored_name = f"{uuid.uuid4().hex}_{original_name}"
        path = workspace / stored_name
        try:
            uploaded_file.save(path)
            if path.stat().st_size > current_app.config["MAX_FILE_SIZE"]:
                limit_mb = current_app.config["MAX_FILE_SIZE"] // (1024 * 1024)
                raise PDFValidationError(f"File exceeds the {limit_mb} MB size limit.")
            validate_pdf(path)
            accepted.append(_file_details(path))
        except PDFValidationError as error:
            path.unlink(missing_ok=True)
            rejected.append({"name": original_name, "reason": str(error)})
        except OSError:
            path.unlink(missing_ok=True)
            current_app.logger.exception("Unable to save uploaded file")
            rejected.append({"name": original_name, "reason": "The file could not be saved."})

    if not accepted:
        return jsonify({"error": "No valid PDFs were uploaded.", "rejected": rejected}), 422

    return jsonify({"files": accepted, "rejected": rejected}), 201


@main_bp.route("/remove-file", methods=["POST"])
def remove_file():
    data = request.get_json(silent=True) or {}
    file_id = data.get("file_id", data.get("filename"))
    path = _stored_path(file_id)
    if path is None:
        return _error("That file is no longer available.", 404)

    path.unlink()
    return jsonify({"message": "File removed.", "file_id": file_id})


@main_bp.route("/combine-and-download", methods=["POST"])
def combine_and_download():
    data = request.get_json(silent=True) or {}
    file_ids = data.get("file_ids", data.get("filenames", []))
    if not isinstance(file_ids, list) or len(file_ids) < 2:
        return _error("Select at least two PDF files to combine.")
    if len(file_ids) > current_app.config["MAX_FILES"] or len(set(file_ids)) != len(file_ids):
        return _error("The selected file list is invalid.")

    paths = [_stored_path(file_id) for file_id in file_ids]
    if any(path is None for path in paths):
        return _error("One or more selected files are no longer available.", 404)

    workspace = _workspace_dir()
    output_path = workspace / f"combined-{uuid.uuid4().hex}.pdf"
    try:
        combine_pdfs(paths, output_path)
    except PDFValidationError as error:
        output_path.unlink(missing_ok=True)
        return _error(str(error), 422)
    except Exception:
        output_path.unlink(missing_ok=True)
        current_app.logger.exception("Unable to combine PDFs")
        return _error("The PDFs could not be combined. Please try again.", 500)

    try:
        output_bytes = output_path.read_bytes()
    except OSError:
        output_path.unlink(missing_ok=True)
        current_app.logger.exception("Unable to read combined PDF")
        return _error("The combined PDF could not be downloaded. Please try again.", 500)
    finally:
        output_path.unlink(missing_ok=True)

    return send_file(
        io.BytesIO(output_bytes),
        as_attachment=True,
        download_name="combined.pdf",
        mimetype="application/pdf",
    )


@main_bp.route("/clear-files", methods=["POST"])
def clear_files():
    removed = 0
    for path in _workspace_files():
        path.unlink(missing_ok=True)
        removed += 1
    return jsonify({"message": "Files cleared.", "removed": removed})
