"""Make sure the example renderer keeps working with the current templates."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "examples" / "render_examples.py"


class RenderExamplesTests(unittest.TestCase):
    def test_all_examples_render(self):
        spec = importlib.util.spec_from_file_location("render_examples", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            written = module.render_all(Path(tmp))
            self.assertEqual(len(written), len(module.SCENARIOS))
            for path in written:
                self.assertTrue(path.read_text().startswith("<!DOCTYPE html>"))
            index = Path(tmp, "index.html").read_text()
            for name in module.SCENARIOS:
                self.assertIn(f'href="{name}.html"', index)


if __name__ == "__main__":
    unittest.main()
