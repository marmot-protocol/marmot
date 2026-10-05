"""Regressions for specification tooling, not protocol behavior."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import spec_validate


class LayoutValidationTest(unittest.TestCase):
    def test_feature_listed_under_ideas_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in (
                "foundation/registries.md",
                "app-components/README.md",
                "features/README.md",
                "features/consensual-history-purge.md",
            ):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(spec_validate.ROOT / name, target)
            (root / "layout.md").write_text(
                "```text\nfeatures/\n  README.md\nideas/\n"
                "  consensual-history-purge.md\n```\n"
            )
            with patch.object(spec_validate, "ROOT", root):
                with self.assertRaisesRegex(spec_validate.ValidationError, "layout.md"):
                    spec_validate.check_registry_and_components(
                        [root / "features/consensual-history-purge.md"]
                    )


if __name__ == "__main__":
    unittest.main()
