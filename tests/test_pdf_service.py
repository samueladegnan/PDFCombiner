import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.services.pdf_service import combine_pdfs


class PDFServiceTest(unittest.TestCase):
    def test_combine_pdfs_writes_pages_in_input_order(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            paths = []
            for page_count in (1, 3):
                path = directory / f"{page_count}.pdf"
                writer = PdfWriter()
                for _ in range(page_count):
                    writer.add_blank_page(width=612, height=792)
                writer.write(path)
                paths.append(path)

            output = directory / "combined.pdf"
            combine_pdfs([paths[0], paths[1]], output)

            self.assertEqual(len(PdfReader(output).pages), 4)

    def test_combine_requires_two_inputs(self):
        with self.assertRaises(ValueError):
            combine_pdfs([], "combined.pdf")


if __name__ == "__main__":
    unittest.main()
