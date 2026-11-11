import unittest

from repair_shared_default_topics import field, physical_records
from repair_shared_core_topics import extend, info_keys, make_mapping
from test_shared_default_topics import dial, fixture, record


def info(iid, actor=b'NPC', text=b'Original', deleted=False):
    return record(b'INFO', field(b'INAM', iid) + field(b'ONAM', actor) + field(b'NAME', text)
                  + field(b'BNAM', b'AddTopic "Talos"\r\nSet quest to 7\0')
                  + (field(b'DELE', b'\0' * 3) if deleted else b''))


class SharedCoreTopicsTest(unittest.TestCase):
    def test_predicates_disambiguate_reused_info_ids(self):
        master = fixture(dial('Talos'), info(b'1', b'A'), dial('unrelated'), info(b'1', b'B'))
        core = fixture(dial('탈로스'), info(b'1', b'A', '번역'.encode()))
        self.assertEqual([(r['english'], r['korean']) for r in make_mapping([master], core)], [('talos', '탈로스')])

    def test_rejects_ambiguous_parent_and_many_to_one_mapping(self):
        master = fixture(dial('A'), info(b'1'), dial('B'), info(b'1'))
        core = fixture(dial('번역'), info(b'1'))
        self.assertEqual(make_mapping([master], core), [])
        master = fixture(dial('A'), info(b'1'), dial('B'), info(b'2'))
        core = fixture(dial('번역'), info(b'1'), info(b'2'))
        self.assertEqual(make_mapping([master], core), [])

    def test_only_new_live_responses_copied_with_scripts_exact(self):
        source = fixture(dial('Talos'), info(b'1'), info(b'2'), info(b'3', deleted=True),
                         dial('탈로스'), info(b'4', text='기존 번역'.encode()))
        mapping = [{'english': 'talos', 'korean': '탈로스'}]
        protected = {('탈로스', '2')}
        output, ledger = extend(source, mapping, protected)
        old, new = list(physical_records(source)), list(physical_records(output))
        self.assertEqual(new[1:len(old)], old[1:])
        self.assertEqual(new[-1], old[2])
        self.assertEqual(ledger[0]['copied_infos'], 1)
        self.assertEqual(extend(output, mapping, protected)[0], output)
        self.assertTrue(info_keys(source) <= info_keys(output))

    def test_reviewed_synonyms_cannot_silently_drop_conflicting_regional_info(self):
        mapping = [{'english': 'bounty', 'korean': '현상금'}, {'english': 'price on your head', 'korean': '현상금'}]
        original = fixture(dial('Bounty'), info(b'1'), dial('price on your head'), info(b'1', b'Other NPC'))
        with self.assertRaisesRegex(ValueError, 'Conflicting regional INFOs'):
            extend(original, mapping, set())
        original = fixture(dial('Bounty'), info(b'1'), dial('price on your head'), info(b'2'))
        _, ledger = extend(original, mapping, set())
        self.assertEqual(sum(r['copied_infos'] for r in ledger), 2)


if __name__ == '__main__':
    unittest.main()
