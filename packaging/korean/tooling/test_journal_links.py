"""Portable regression fixtures for the actual OpenMW parser and sidecar loader."""
from pathlib import Path
import sys,tempfile
from verify_kr5_links import inspect

runner=Path(sys.argv[1]).resolve()
mine='칼데라 에보니 광산'
guild='마법사 길드'
ore='에보니'
with tempfile.TemporaryDirectory(prefix='openmw-journal-test-') as tmp:
    mod=Path(tmp)
    for newline in ['\n','\r\n']:
        for extension,text in {
            'cel':'',
            'top':f'칼데라의 에보니 광산\t{mine}{newline}',
            'mrk':f'{guild}\t마법사 길드에서{newline}',
            'jrn':f'칼데라의 에보니 광산\t{mine}{newline}에보니 광산\t{mine}{newline}',
        }.items():
            (mod/f'Morrowind_Korean_ReTranslation.{extension}').write_bytes(b'\xef\xbb\xbf'+text.encode('utf-8'))
        entries=[('mine','칼데라의 에보니 광산을 방문했다.'),('guild','마법사 길드에 들렀다.'),('explicit','@칼데라의 에보니 광산#을 방문했다.')]
        before=inspect(runner,mod,entries,[mine,guild],False)
        after=inspect(runner,mod,entries,[mine,guild],True)
        assert before['mine']['targets']==[]
        assert before['guild']['targets']==[]
        assert after['mine']['targets']==[mine]
        assert after['guild']['targets']==[guild]
        assert after['explicit']['targets']==[mine]
        assert before['explicit']['text']==after['explicit']['text']=='칼데라의 에보니 광산을 방문했다.'
        unknown=inspect(runner,mod,entries,[],True)
        assert all(not x['targets'] for x in unknown.values())
        overlapping=inspect(runner,mod,entries,[mine,ore,guild],True)
        assert overlapping['mine']['targets']==[mine]
        only_ore=inspect(runner,mod,entries,[ore],True)
        assert mine not in only_ore['mine']['targets']
        assert only_ore['explicit']['targets']==[]
        # The actual runtime parser must keep legitimate one-syllable topics without
        # coloring syllables embedded in unrelated Korean words.
        one_syllable = [
            ('noise', '싫은 것일 수도 있다. 노예들은 모른다. 일요일과 은근한 표정.'),
            ('valid', '은을 찾고 할 일이 있다.'),
            ('explicit', '@은#과 @일#을 찾는다.'),
        ]
        highlighted = inspect(runner, mod, one_syllable, ['은', '일'], True)
        assert highlighted['noise']['targets'] == []
        assert highlighted['valid']['targets'] == ['은', '일']
        assert highlighted['explicit']['targets'] == ['은', '일']
        discovered = inspect(runner, mod, one_syllable, ['은', '일'], False)
        assert discovered['noise']['targets'] == []
        compounds = [
            ('hyphen', '하지-에이의 행방과 하이-엘프를 물었다.'),
            ('verb', '빛나는 밤에 빛을 보았다.'),
            ('particles', '마법사 길드에서만 광산으로부터 돌아왔다.'),
        ]
        compound_results = inspect(runner, mod, compounds, ['에이', '엘프', '빛', '마법사 길드', '광산'], True)
        assert compound_results['hyphen']['targets'] == []
        assert compound_results['verb']['targets'] == ['빛']
        assert compound_results['particles']['targets'] == ['마법사 길드', '광산']
print('PASS: Korean topic boundaries, single-syllable topics, explicit links, canonical names, legacy saved text, reviewed aliases, overlap resolution, unknown-topic gating, UTF-8 BOM, LF and CRLF')
