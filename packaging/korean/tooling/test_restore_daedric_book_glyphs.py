"""Regression tests for translated Daedric glyphs in magic scroll BOOK/TEXT."""

import unittest

from restore_daedric_book_glyphs import DAEDRIC, restore


class DaedricBookTextTest(unittest.TestCase):
    def setUp(self):
        self.original = (
            b'<DIV ALIGN="center"><FONT COLOR="000000" SIZE="2" FACE="Daedric">'
            b'SANCTIFY WITH BLOOD AND FIRE</FONT><BR>'
        )
        self.korean = (
            b'<DIV ALIGN="center"><FONT COLOR="000000" SIZE="2" FACE="Daedric">'
            + "피와 불로 거룩하게 하라".encode("utf-8")
            + b'</FONT><BR>'
        )

    def test_opened_scroll_shows_original_daedric_and_korean(self):
        updated, count, error = restore(self.original, self.korean)
        self.assertIsNone(error)
        self.assertEqual(count, 1)
        self.assertEqual(
            updated,
            self.original.replace(b"</FONT><BR>",
                                  b"</FONT><BR>" + "피와 불로 거룩하게 하라".encode("utf-8") + b"<BR>")
        )
        self.assertEqual(DAEDRIC.search(updated).group(2), b"SANCTIFY WITH BLOOD AND FIRE")
        self.assertNotIn("피와".encode("utf-8"), DAEDRIC.search(updated).group(0))

    def test_cp949_korean_is_preserved(self):
        cp949 = self.korean.replace("피와 불로 거룩하게 하라".encode("utf-8"),
                                     "피와 불로 거룩하게 하라".encode("cp949"))
        updated, count, error = restore(self.original, cp949)
        self.assertIsNone(error)
        self.assertEqual(count, 1)
        self.assertIn("피와 불로 거룩하게 하라".encode("cp949"), updated)

    def test_repaired_scroll_is_idempotent(self):
        once, count, error = restore(self.original, self.korean)
        self.assertIsNone(error)
        self.assertEqual(count, 1)
        twice, count, error = restore(self.original, once)
        self.assertIsNone(error)
        self.assertEqual(count, 0)
        self.assertEqual(once, twice)

    def test_non_daedric_markup_is_not_changed(self):
        text = b'<FONT FACE="Mystic Cards">No Daedric tag</FONT><BR>'
        fixed, count, error = restore(self.original, text)
        self.assertEqual((fixed, count, error), (text, 0, None))

    def test_mismatched_span_count_is_flagged(self):
        repeated = self.korean + self.korean
        fixed, count, error = restore(self.original, repeated)
        self.assertEqual(fixed, repeated)
        self.assertEqual(count, 0)
        self.assertIn("count mismatch", error)


if __name__ == "__main__":
    unittest.main()
