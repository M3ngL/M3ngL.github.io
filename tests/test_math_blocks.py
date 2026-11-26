import unittest
from pathlib import Path

from convert_papers import normalize_display_math, render_markdown_to_html


class DisplayMathTests(unittest.TestCase):
    def test_adjacent_prose_becomes_separate_blocks(self):
        source = "before\n$$\nx+y\n$$\nafter\n"
        expected = "before\n\n$$\nx+y\n$$\n\nafter\n"
        self.assertEqual(normalize_display_math(source), expected)
        self.assertIn(
            "</p>\n<p>$$\nx+y\n$$</p>\n<p>",
            render_markdown_to_html(normalize_display_math(source)),
        )

    def test_existing_spacing_and_inline_math_remain_unchanged(self):
        source = "before $x$\n\n$$\nx+y\n$$\n\nafter $y$\n"
        self.assertEqual(normalize_display_math(source), source)

    def test_fenced_code_is_untouched(self):
        source = "````md\n$$\nx+y\n$$\n```\n````\nbefore\n$$\nz\n$$\nafter\n"
        self.assertEqual(
            normalize_display_math(source),
            "````md\n$$\nx+y\n$$\n```\n````\nbefore\n\n$$\nz\n$$\n\nafter\n",
        )

    def test_indented_code_and_unpaired_delimiter_are_untouched(self):
        self.assertEqual(normalize_display_math("    $$\n"), "    $$\n")
        self.assertEqual(normalize_display_math("before\n$$\n"), "before\n$$\n")

    def test_idempotent_and_existing_posts_normalized(self):
        for post in Path("_posts").glob("*.md"):
            with self.subTest(post=post):
                source = post.read_text(encoding="utf-8")
                self.assertEqual(normalize_display_math(source), source)


if __name__ == "__main__":
    unittest.main()
