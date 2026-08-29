"""تست جدول موتور مارک‌آپ — D-118 GEO (ماتریس مقایسه در صفحه محصول)."""
from django.test import SimpleTestCase

from src.modules.pages.markup import render_page_markup


class MarkupTableTest(SimpleTestCase):
    def test_basic_table_with_header(self):
        out = render_page_markup(
            "| ویژگی | هوراند | بازار |\n"
            "| بافت | پولکی | آردی |\n"
            "| هسته | جدا شده | آسیاب‌شده |"
        )
        self.assertIn('<table class="pm-table">', out)
        self.assertIn('<thead>', out)
        self.assertIn('<th>ویژگی</th>', out)
        self.assertIn('<th>هوراند</th>', out)
        self.assertIn('<td>پولکی</td>', out)
        self.assertIn('<td>جدا شده</td>', out)
        self.assertIn('pm-table-wrap', out)

    def test_markdown_separator_row_skipped(self):
        out = render_page_markup(
            "| الف | ب |\n"
            "|---|---|\n"
            "| ۱ | ۲ |"
        )
        self.assertNotIn('<td>---</td>', out)
        self.assertIn('<td>۱</td>', out)
        self.assertIn('<tbody>', out)

    def test_cells_escaped(self):
        out = render_page_markup("| <b> | x |\n| <script> | y |")
        self.assertNotIn('<script>', out)
        self.assertIn('&lt;b&gt;', out)
        self.assertIn('&lt;script&gt;', out)

    def test_table_mixed_with_paragraph(self):
        out = render_page_markup(
            "پاراگراف معمولی.\n\n"
            "| سر | ستون |\n| داده | ۲ |"
        )
        self.assertIn('<p class="pm-p">پاراگراف معمولی.</p>', out)
        self.assertIn('<table class="pm-table">', out)

    def test_list_still_works(self):
        out = render_page_markup("- مورد اول\n- مورد دوم")
        self.assertIn('<ul class="pm-list">', out)
        self.assertNotIn('pm-table', out)

    def test_empty_table_only_separators_is_noop(self):
        out = render_page_markup("|---|---|")
        self.assertEqual(out, '')
