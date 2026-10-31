"""Synthetic, no-Bethesda-assets tests for the KR12.2 Fighters Guild audit."""
import importlib.util
import struct
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("audit_kr12_fighters_topic_candidates.py")
spec = importlib.util.spec_from_file_location("audit_kr12", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def sub(tag, data):
    return struct.pack("<4sI", tag, len(data)) + data


def rec(tag, body):
    return struct.pack("<4sIII", tag, len(body), 0, 0) + body


def make_data(text, target="바스"):
    esp = (rec(b"DIAL", sub(b"NAME", target.encode()) + sub(b"DATA", b"\0"))
           + rec(b"INFO", sub(b"INAM", b"1") + sub(b"ONAM", b"persius mercius")
                 + sub(b"NAME", text.encode())))
    return {"esp": esp, "mrk": b"", "top": b""}


class TopicAuditTest(unittest.TestCase):
    def test_quotative_candidate_in_fighters_guild(self):
        report = audit.scan(make_data("바스라는 강령술사 소굴"))
        self.assertEqual(report["fighters_candidate_count"], 1)
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["findings"][0]["topic"], "바스")

    def test_inside_word_and_explicit_are_not_missing(self):
        self.assertEqual(audit.scan(make_data("사바스라는 곳"))["candidate_count"], 0)
        self.assertEqual(audit.scan(make_data("@바스#라는 곳"))["candidate_count"], 0)

    def test_dial_without_topic_is_not_rewritten(self):
        report = audit.scan(make_data("울리네 헤님과 함께 싸운다", "함께 싸우기"))
        self.assertEqual(report["candidate_count"], 0)


if __name__ == "__main__":
    unittest.main()
