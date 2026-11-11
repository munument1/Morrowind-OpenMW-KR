"""Canonical shared-topic discovery, keyword variants and English-only history."""
from pathlib import Path
import sys
import tempfile
from verify_kr5_links import inspect

runner = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as temp:
    folder = Path(temp)
    for ext, text in {'top': 'mages guild\t마법사 길드\n메이지 길드\t마법사 길드\n마법사 길드\t지역 동음이의어\n',
                      'mrk': 'Mages Guild\t메이지 길드\n', 'jrn': '', 'cel': ''}.items():
        (folder / ('Morrowind_Korean_ReTranslation.' + ext)).write_text(text, encoding='utf-8-sig')
    cases = [('canonical', '마법사 길드에 갑니다.'), ('variant', '메이지 길드에 갑니다.'),
             ('english', 'Mages Guild'), ('explicit', '@메이지 길드#에 갑니다.')]
    topics = ['Mages Guild', '마법사 길드']
    found = inspect(runner, folder, cases, topics, False, True)
    for key in ('canonical', 'variant', 'explicit'):
        assert found[key]['targets'] == ['마법사 길드'], (key, found)
    for journal in (False, True):
        found = inspect(runner, folder, cases, topics, journal, False)
        for key in ('canonical', 'variant', 'explicit'):
            assert found[key]['targets'] == ['마법사 길드'], (key, found)
        found = inspect(runner, folder, [('old', '메이지 길드에 갑니다.')], ['Mages Guild'], journal, False)
        assert found['old']['targets'] == ['mages guild'], found
    found = inspect(runner, folder, cases, ['마법사 길드'], False, False)
    assert found['variant']['targets'] == ['마법사 길드'], found
    (folder / 'Morrowind_Korean_ReTranslation.mrk').write_text('', encoding='utf-8-sig')
    found = inspect(runner, folder, [('english', 'Mages Guild')], topics, False, True)
    assert found['english']['targets'] == ['마법사 길드'], found
print('PASS: canonical discovery, regional spelling, known-topic priority and English-only saved history')
