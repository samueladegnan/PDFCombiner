from flask import current_app


def allowed_file(filename):
    """Return whether a filename uses one of the configured extensions."""
    return (
        bool(filename)
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )
