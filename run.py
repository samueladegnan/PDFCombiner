import os
import webbrowser

from app import create_app


app = create_app()


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))

    if os.getenv("OPEN_BROWSER", "1").lower() not in {"0", "false", "no"}:
        webbrowser.open(f"http://{host}:{port}")

    app.run(host=host, port=port, debug=app.config["DEBUG"])
