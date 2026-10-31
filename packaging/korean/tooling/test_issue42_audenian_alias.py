"""Regression tests for narrowly targeted KR12.3.1 Audenian Valius alias candidate."""
import unittest

from patch_issue42_audenian_alias import DESTINATION, EXACT_ALIASES, patch_aliases


class AudenianAliasTest(unittest.TestCase):
    @staticmethod
    def fixture():
        return ("\ufeff" + "\r\n".join(
            f"{alias}\t마법부여" for alias in EXACT_ALIASES
        ) + "\r\n유지할 토픽\t마법부여\r\n").encode("utf-8")

    def test_exact_three_with_bom_and_crlf(self):
        original = self.fixture()
        patched, changed = patch_aliases(original, {DESTINATION})
        self.assertEqual(len(changed), 3)
        self.assertEqual(patched.count(("\t" + DESTINATION).encode()), 3)
        self.assertTrue(patched.startswith(b"\xef\xbb\xbf"))
        self.assertEqual(patched.count(b"\r\n"), original.count(b"\r\n"))
        self.assertIn("유지할 토픽\t마법부여".encode(), patched)
        for old in EXACT_ALIASES:
            self.assertIn((old + "\t" + DESTINATION).encode(), patched)

    def test_missing_destination_rejected(self):
        with self.assertRaises(ValueError):
            patch_aliases(self.fixture(), set())

    def test_wrong_prior_target_rejected(self):
        bad = self.fixture().replace((EXACT_ALIASES[0] + "\t마법부여").encode(),
                                     (EXACT_ALIASES[0] + "\t다른 토픽").encode())
        with self.assertRaises(ValueError):
            patch_aliases(bad, {DESTINATION})

    def test_duplicate_alias_rejected(self):
        bad = self.fixture() + (EXACT_ALIASES[0] + "\t마법부여\r\n").encode()
        with self.assertRaises(ValueError):
            patch_aliases(bad, {DESTINATION})


if __name__ == "__main__":
    unittest.main()
