import io
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app import create_app


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    UPLOAD_FOLDER = ""
    ALLOWED_EXTENSIONS = {"pdf"}
    MAX_FILE_SIZE = 1024 * 1024
    MAX_FILES = 4
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SEND_FILE_MAX_AGE_DEFAULT = 0


def pdf_bytes(page_count=1):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


class PDFCombinerRoutesTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        TestConfig.UPLOAD_FOLDER = self.temp_dir.name
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def upload(self, *files):
        return self.client.post(
            "/upload",
            data={"pdfs": [(io.BytesIO(contents), name) for name, contents in files]},
            content_type="multipart/form-data",
        )

    def test_upload_validates_files_and_lists_session_workspace(self):
        response = self.upload(("first.pdf", pdf_bytes()), ("second.pdf", pdf_bytes(2)))

        self.assertEqual(response.status_code, 201)
        uploaded = response.get_json()["files"]
        self.assertEqual([file["name"] for file in uploaded], ["first.pdf", "second.pdf"])
        self.assertEqual(len(self.client.get("/files").get_json()["files"]), 2)

        stored_files = list(Path(self.temp_dir.name).glob("**/*.pdf"))
        self.assertEqual(len(stored_files), 2)
        self.assertNotIn("first.pdf", stored_files[0].name)

    def test_invalid_pdf_is_rejected_without_being_saved(self):
        response = self.upload(("not-a-pdf.pdf", b"this is not a PDF"))

        self.assertEqual(response.status_code, 422)
        self.assertIn("valid PDFs", response.get_json()["error"])
        self.assertEqual(self.client.get("/files").get_json()["files"], [])

    def test_combine_preserves_requested_order_and_removes_download_artifact(self):
        response = self.upload(("one.pdf", pdf_bytes()), ("two.pdf", pdf_bytes(2)))
        uploaded = response.get_json()["files"]

        combined = self.client.post(
            "/combine-and-download",
            json={"file_ids": [uploaded[1]["id"], uploaded[0]["id"]]},
        )

        self.assertEqual(combined.status_code, 200)
        self.assertEqual(combined.mimetype, "application/pdf")
        self.assertEqual(len(PdfReader(io.BytesIO(combined.data)).pages), 3)
        self.assertEqual(len(list(Path(self.temp_dir.name).glob("**/combined-*.pdf"))), 0)

    def test_remove_and_clear_only_touch_current_workspace(self):
        response = self.upload(("one.pdf", pdf_bytes()), ("two.pdf", pdf_bytes()))
        file_id = response.get_json()["files"][0]["id"]

        self.assertEqual(self.client.post("/remove-file", json={"file_id": file_id}).status_code, 200)
        self.assertEqual(len(self.client.get("/files").get_json()["files"]), 1)
        self.assertEqual(self.client.post("/clear-files").get_json()["removed"], 1)
        self.assertEqual(self.client.get("/files").get_json()["files"], [])

    def test_path_traversal_and_invalid_combine_requests_are_rejected(self):
        self.assertEqual(self.client.post("/remove-file", json={"file_id": "../../secret.pdf"}).status_code, 404)
        self.assertEqual(self.client.post("/combine-and-download", json={"file_ids": ["a.pdf"]}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
