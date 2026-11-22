"""Regression fixtures for broken targets, anchors and reference resolution."""

from pathlib import Path
import tempfile
import unittest

from check_docs import check


class DocumentationChecks(unittest.TestCase):
    def validate(self, documents, assets=()):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in documents.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            for name in assets:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"asset")
            return check(root, [root / name for name in documents])

    def test_realistic_relative_links_images_and_unicode_headings(self):
        self.assertEqual(self.validate({
            "README.md": "[rules](rules.md#clé--state)\n![diagram](images/a.svg)\n",
            "rules.md": "# Clé & `State`\n[home](/README.md)\n",
        }, assets=["images/a.svg"]), [])

    def test_duplicate_and_setext_heading_anchors(self):
        self.assertEqual(self.validate({"a.md":
            "# Rules\n# Rules\nOther rules\n---\n[second](#rules-1) [other](#other-rules)\n"}), [])

    def test_explicit_html_anchor_and_html_link(self):
        self.assertEqual(self.validate({"a.md":
            '<a id="stable"></a>\n<a href="#stable">rule</a>\n<img src="a.svg">\n'
        }, assets=["a.svg"]), [])

    def test_reference_styles_and_nested_labels(self):
        self.assertEqual(self.validate({
            "a.md": '[rule][r] [r][] [r] ![image][p] [[nested] label](b.md#target)\n'
                    '[r]: b.md#target "title"\n[p]: pic.svg\n',
            "b.md": "# Target\n",
        }, assets=["pic.svg"]), [])

    def test_code_examples_and_remote_urls_are_not_local_links(self):
        self.assertEqual(self.validate({"a.md":
            "```md\n[not a link](missing.md)\n```\n"
            "`[code](missing.md)` ``[more](missing.md)``\n"
            "[web](https://example.invalid/no.md#not-local) [mail](mailto:a@example.invalid)\n"}), [])

    def test_missing_file_and_anchor_are_rejected_with_locations(self):
        errors = self.validate({"a.md": "# A\n[bad](missing.md)\n[bad](#absent)\n"})
        self.assertEqual(len(errors), 2)
        self.assertIn("a.md:2: missing target: missing.md", errors)
        self.assertIn("a.md:3: missing anchor: #absent", errors)

    def test_undefined_reference_and_image_are_rejected(self):
        errors = self.validate({"a.md": "[rule][absent]\n![image](missing.svg)\n"})
        self.assertEqual(len(errors), 2)
        self.assertIn("a.md:1: undefined reference [absent]", errors)
        self.assertIn("a.md:2: missing target: missing.svg", errors)

    def test_parentheses_spaces_percent_encoding_and_titles(self):
        self.assertEqual(self.validate({
            "a.md": '[one](b(one).md#heading "title")\n[two](<b two.md#heading>)\n'
                    '[three](b%20two.md#heading)\n',
            "b(one).md": "# Heading\n", "b two.md": "# Heading\n",
        }), [])

    def test_repository_escape_is_rejected(self):
        errors = self.validate({"a.md": "[escape](../outside.md)\n"})
        self.assertEqual(len(errors), 1)
        self.assertIn("target escapes repository", errors[0])

    def test_heading_inside_fenced_example_is_not_a_real_anchor(self):
        errors = self.validate({"a.md": "```md\n# Example\n```\n[bad](#example)\n"})
        self.assertEqual(len(errors), 1)
        self.assertIn("missing anchor", errors[0])


if __name__ == "__main__":
    unittest.main()
