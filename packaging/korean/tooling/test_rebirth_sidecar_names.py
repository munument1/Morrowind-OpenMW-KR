import unittest

from repair_rebirth_sidecar_names import cell_names
from test_shared_default_topics import fixture, record
from repair_shared_default_topics import field


class RebirthSidecarNamesTest(unittest.TestCase):
    def test_cell_references_do_not_replace_first_name(self):
        source = fixture(record(b'CELL', field(b'NAME', b'Anvil\0') + field(b'DATA', bytes(12))
                                + field(b'FRMR', bytes(4)) + field(b'NAME', b'NPC_ref\0')),
                         record(b'REGN', field(b'NAME', b'Gold Coast\0') + field(b'FNAM', b'Gold Coast Region\0')))
        self.assertEqual(cell_names(source), {'anvil', 'gold coast', 'gold coast region'})


if __name__ == '__main__':
    unittest.main()
