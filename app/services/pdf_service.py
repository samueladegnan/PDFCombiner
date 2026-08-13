from pathlib import Path

from pypdf import PdfReader, PdfWriter


class PDFValidationError(ValueError):
    """Raised when an uploaded file is not a usable PDF."""


def validate_pdf(path):
    """Validate that *path* contains a readable, non-empty PDF."""
    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            raise PDFValidationError("Password-protected PDFs are not supported.")
        if len(reader.pages) == 0:
            raise PDFValidationError("The PDF does not contain any pages.")
    except PDFValidationError:
        raise
    except Exception as error:
        raise PDFValidationError("The file is damaged or is not a valid PDF.") from error


def combine_pdfs(input_paths, output_path):
    """Combine PDF files in the supplied order and write one output PDF."""
    paths = [Path(path) for path in input_paths]
    if len(paths) < 2:
        raise ValueError("At least two PDF files are required.")

    writer = PdfWriter()
    try:
        for path in paths:
            validate_pdf(path)
            writer.append(str(path))
        writer.write(str(output_path))
    except PDFValidationError:
        raise
    except Exception as error:
        raise RuntimeError("The selected PDFs could not be combined.") from error
