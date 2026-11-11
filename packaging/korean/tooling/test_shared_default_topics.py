import struct
import unittest

from audit_cross_mod_topic_gaps import subs
from repair_shared_default_topics import field, physical_records, plugin


def record(tag, body):
    return tag + struct.pack('<I', len(body)) + b'\x01\0\0\0\x02\0\0\0' + body


def fixture(*records):
    header = b'\0' * 296 + struct.pack('<I', len(records))
    return record(b'TES3', field(b'HEDR', header) + field(b'MAST', b'Morrowind.esm\0')) + b''.join(records)


def dial(name):
    return record(b'DIAL', field(b'NAME', name.encode() + b'\0') + field(b'DATA', b'\0'))


class SharedTopicsTest(unittest.TestCase):
    def test_preserves_saved_ids_scripts_conditions_and_side_effects(self):
        info = record(b'INFO', field(b'INAM', b'123\0') + field(b'ONAM', b'TR_test\0')
                      + field(b'NAME', '기존 @서비스# 대사'.encode() + b'\0')
                      + field(b'SCVR', b'04JX3quest') + field(b'INTV', struct.pack('<i', 50))
                      + field(b'BNAM', b'AddTopic "Services"\r\nSet value to 7\0'))
        original = fixture(dial('Services'), info, record(b'GLOB', field(b'NAME', b'untouched\0')))
        patched, ledger = plugin(original)
        old, new = list(physical_records(original)), list(physical_records(patched))
        self.assertEqual(new[1:len(old)], old[1:])
        self.assertEqual(new[-1], info)
        self.assertEqual(dict(subs(new[-2][16:]))[b'NAME'], '서비스\0'.encode())
        self.assertEqual(struct.unpack_from('<I', dict(subs(new[0][16:]))[b'HEDR'], 296)[0], 5)
        self.assertEqual(ledger[0]['copied_infos'], 1)
        self.assertEqual(new[-2][8:16], old[1][8:16])

    def test_no_matching_topic_is_byte_identical(self):
        original = fixture(dial('regional quest'))
        self.assertEqual(plugin(original), (original, []))

    def test_refuses_ambiguous_existing_korean_topic(self):
        with self.assertRaisesRegex(ValueError, 'already exists'):
            plugin(fixture(dial('Background'), dial('배경')))

    def test_refuses_bad_record_count(self):
        original = fixture(dial('Background'))
        records = list(physical_records(original))
        header = b'\0' * 296 + struct.pack('<I', 2)
        with self.assertRaisesRegex(ValueError, 'record count'):
            plugin(record(b'TES3', field(b'HEDR', header)) + records[1])

    def test_refuses_deleted_shared_topic(self):
        deleted = record(b'DIAL', field(b'NAME', b'Background\0') + field(b'DELE', b'\0' * 3))
        with self.assertRaisesRegex(ValueError, 'live shared topic'):
            plugin(fixture(deleted))

    def test_truncated_input_fails(self):
        with self.assertRaises(ValueError):
            plugin(fixture(dial('Background'))[:-1])


if __name__ == '__main__':
    unittest.main()
