import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add parent dir and client dir to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "client"))

from client.services.ocr_addon_manager import EasyOCREngine


class TestEasyOCR(unittest.TestCase):
    def setUp(self):
        self.engine = EasyOCREngine()

    def test_paths(self):
        path = self.engine._get_addon_path()
        print(f"Addon path: {path}")
        self.assertTrue(path.endswith("easyocr"))

    @patch("subprocess.run")
    @patch("requests.get")
    # Patch zipfile to avoid actual unzip error on mock object
    @patch("zipfile.ZipFile")
    def test_install_flow(self, mock_zip, mock_get, mock_run):
        # Setup mocks
        mock_run.return_value.returncode = 0

        mock_response = MagicMock()
        mock_response.headers.get.return_value = "1024"  # 1KB
        mock_response.iter_content.return_value = [b"data"]
        mock_get.return_value = mock_response

        # Mock callback
        cb = MagicMock()

        # Run install
        success = self.engine.install(progress_callback=cb)

        # Verify
        self.assertTrue(success)
        # Should call pip install
        mock_run.assert_called()
        # Should download 3 models
        self.assertEqual(mock_get.call_count, 3)
        # Should report progress
        cb.assert_called()


if __name__ == "__main__":
    unittest.main()
