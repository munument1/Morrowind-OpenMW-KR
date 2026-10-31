"""Standalone synthetic tests: full KR12.2 corpus audit does not need game masters."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT))
from test_kr12_fighters_topic_candidates import make_data
import audit_kr12_gamewide_topics as audit

CPP = '''
constexpr std::string_view endings[] = { "이라는", "라는", "을", "들" };
constexpr std::string_view extendedSuffixes[] = { "입니다", "에서만" };
'''

class FullCorpusAuditTest(unittest.TestCase):
    def test_missing_suffix_vs_known_quotative(self):
        data=make_data("바스라는 소굴, 바스라서 유명하다.")
        result=audit.inspect(data,CPP)
        self.assertEqual(result["info_count"],1)
        self.assertEqual(result["topic_count"],1)
        self.assertEqual(result["additional_missing_suffix_candidates"],1)
        self.assertEqual(result["top_unhandled_suffixes"][0], ("라서", 1))

    def test_explicit_links_do_not_count(self):
        data=make_data("@바스#라서 간다.")
        result=audit.inspect(data,CPP)
        self.assertEqual(result["additional_missing_suffix_candidates"],0)

    def test_source_is_never_modified(self):
        data=make_data("바스라서 간다.")
        original=data["esp"]
        audit.inspect(data,CPP)
        self.assertEqual(data["esp"],original)

    def test_sidecar_alias_conflicts_are_visible(self):
        data=make_data("바스라서 간다.")
        data["top"]="바스\t바스\n바스\t다른 바스\n".encode()
        result=audit.inspect(data,CPP)
        self.assertEqual(len(result["sidecar_alias_conflicts"]),1)

if __name__=="__main__":
    unittest.main()
