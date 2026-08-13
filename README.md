# PDF Combiner

A focused local web app for validating, ordering, and merging PDF documents. The interface is intentionally small: upload files, drag them into the right order, and download one combined PDF.

## Highlights

- Drag-and-drop or file-picker uploads with keyboard support.
- Server-side PDF validation catches damaged, empty, and password-protected files before they enter the workspace.
- Drag rows to control the exact merge order.
- Session-isolated workspaces prevent different browser sessions from sharing filenames.
- Files are stored locally and the generated download is temporary.
- Clear upload limits and useful error messages instead of silent failures.
- Responsive dark interface with reduced-motion and focus-visible support.

## Local development

### Requirements

- Python 3.9+
- A virtual environment is recommended.

### Install and run

```bash
git clone https://github.com/yourusername/pdf-combiner.git
cd pdf-combiner
python -m venv .venv

# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
python run.py
```

The development server opens at <http://127.0.0.1:5000>. Set `OPEN_BROWSER=0` when you do not want the browser to open automatically.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Select `development` or `production` configuration. |
| `SECRET_KEY` | Development-only fallback | Flask session signing key; set a long random value outside local development. |
| `HOST` | `127.0.0.1` | Bind address for `python run.py`. |
| `PORT` | `5000` | Port for `python run.py`. |
| `OPEN_BROWSER` | `1` | Set to `0` to disable automatic browser launch. |

The default limits are 20 files per workspace and 25 MB per file. Update `Config` in `config.py` if your deployment needs different limits.

## Testing

The test suite uses Python's standard library test runner and does not require an additional test dependency:

```bash
python -m unittest discover -s tests -v
```

## Production notes

`run.py` is a convenient local entry point, not a production server. For deployment, use a WSGI server such as Gunicorn or Waitress, provide `APP_ENV=production` and a strong `SECRET_KEY`, and configure a scheduled cleanup for abandoned session directories under `uploads/`.

## Project structure

```text
app/
├── routes.py                 # HTTP API and session workspaces
├── services/pdf_service.py   # PDF validation and merging
├── utils/file_utils.py       # Shared upload validation
├── templates/index.html      # Accessible application shell
└── static/                   # CSS and browser behavior
config.py                    # Environment and upload limits
run.py                       # Local entry point
clean.py                     # Remove local build/upload artifacts
tests/                       # Service and route tests
```
