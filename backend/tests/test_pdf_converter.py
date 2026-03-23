"""
Tests for Airco Insights — PDF Converter
==========================================
Covers input validation, LibreOffice discovery, error handling,
and mock-based conversion tests.

Note: Full integration tests require LibreOffice installed.
These tests use mocks for CI/CD compatibility.

Test groups:
    1.  Input validation
    2.  LibreOffice discovery
    3.  Conversion with mocks
    4.  Error handling
    5.  Lock file cleanup
"""

import os
import subprocess
import pytest
from unittest.mock import patch, MagicMock

from app.services.pdf_converter import (
    convert_excel_to_pdf,
    _find_libreoffice,
    _clean_lock_files,
    PDFConversionError,
    LibreOfficeNotFoundError,
)


# ---------------------------------------------------------------------------
# 1. Input Validation
# ---------------------------------------------------------------------------

class TestInputValidation:

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            convert_excel_to_pdf("/nonexistent/path/file.xlsx")

    def test_non_excel_file_raises(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("hello")
        with pytest.raises(PDFConversionError, match="Expected .xlsx"):
            convert_excel_to_pdf(str(txt_file))


# ---------------------------------------------------------------------------
# 2. LibreOffice Discovery
# ---------------------------------------------------------------------------

class TestLibreOfficeDiscovery:

    @patch("shutil.which", return_value="/usr/bin/libreoffice")
    def test_finds_on_path(self, mock_which):
        result = _find_libreoffice()
        assert result == "/usr/bin/libreoffice"

    @patch("shutil.which", return_value=None)
    @patch("os.path.isfile", return_value=False)
    def test_not_found_raises(self, mock_isfile, mock_which):
        with pytest.raises(LibreOfficeNotFoundError, match="not found"):
            _find_libreoffice()


# ---------------------------------------------------------------------------
# 3. Conversion with Mocks
# ---------------------------------------------------------------------------

class TestConversionMock:

    @patch("app.services.pdf_converter._find_libreoffice", return_value="soffice")
    @patch("subprocess.run")
    def test_successful_conversion(self, mock_run, mock_find, tmp_path):
        # Create a fake Excel file
        xlsx_file = tmp_path / "report.xlsx"
        xlsx_file.write_bytes(b"fake xlsx content")

        # Create the expected PDF output
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"fake pdf content")

        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")

        result = convert_excel_to_pdf(str(xlsx_file))
        assert result.endswith("report.pdf")
        mock_run.assert_called_once()

    @patch("app.services.pdf_converter._find_libreoffice", return_value="soffice")
    @patch("subprocess.run")
    def test_conversion_failure_raises(self, mock_run, mock_find, tmp_path):
        xlsx_file = tmp_path / "report.xlsx"
        xlsx_file.write_bytes(b"fake xlsx content")

        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error occurred")

        with pytest.raises(PDFConversionError, match="failed"):
            convert_excel_to_pdf(str(xlsx_file))

    @patch("app.services.pdf_converter._find_libreoffice", return_value="soffice")
    @patch("subprocess.run")
    def test_pdf_not_generated_raises(self, mock_run, mock_find, tmp_path):
        xlsx_file = tmp_path / "report.xlsx"
        xlsx_file.write_bytes(b"fake xlsx content")

        # Successful run but no PDF created
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        with pytest.raises(PDFConversionError, match="not generated"):
            convert_excel_to_pdf(str(xlsx_file))


# ---------------------------------------------------------------------------
# 4. Error Handling
# ---------------------------------------------------------------------------

class TestErrorHandling:

    @patch("app.services.pdf_converter._find_libreoffice", return_value="soffice")
    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=120))
    def test_timeout_raises(self, mock_run, mock_find, tmp_path):
        xlsx_file = tmp_path / "report.xlsx"
        xlsx_file.write_bytes(b"fake xlsx content")

        with pytest.raises(PDFConversionError, match="timed out"):
            convert_excel_to_pdf(str(xlsx_file))


# ---------------------------------------------------------------------------
# 5. Lock File Cleanup
# ---------------------------------------------------------------------------

class TestLockFileCleanup:

    def test_cleans_lock_files(self, tmp_path):
        lock_file = tmp_path / ".~lock.test.xlsx#"
        lock_file.write_text("lock")
        assert lock_file.exists()

        _clean_lock_files(str(tmp_path))
        assert not lock_file.exists()

    def test_no_lock_files_no_error(self, tmp_path):
        _clean_lock_files(str(tmp_path))
