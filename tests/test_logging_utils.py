from __future__ import annotations

import logging
from pathlib import Path
import tempfile
import unittest

from src.logging_utils import configure_logging


class LoggingUtilsTests(unittest.TestCase):
    def test_configure_logging_writes_file_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "logs" / "execucao.log"

            configure_logging(log_path)
            logging.getLogger("tests.logging").debug("mensagem de teste")

            content = log_path.read_text(encoding="utf-8")
            self.assertIn("DEBUG", content)
            self.assertIn("tests.logging", content)
            self.assertIn("mensagem de teste", content)
            for handler in logging.getLogger().handlers:
                handler.close()
            logging.getLogger().handlers.clear()


if __name__ == "__main__":
    unittest.main()
