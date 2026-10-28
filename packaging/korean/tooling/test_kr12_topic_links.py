"""Reported false links, exercising both display and real discovery mode."""
from pathlib import Path
import sys,tempfile
from verify_kr5_links import inspect

runner=Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory() as tmp:
    mod=Path(tmp)
    for ext,text in {'top':'일\t일\n일거리\t일\n작동\t일\n하지\t대화\n에이\t하즈-에이\n하지-에이\t하즈-에이\n하즈-에이\t하즈-에이\n',
                     'mrk':'일\t일거리\n','jrn':'','cel':''}.items():
        (mod/('Morrowind_Korean_ReTranslation.'+ext)).write_text(text,encoding='utf-8-sig')
    cases=[
      ('inside','싫은 것일 수도 있다. 은근한 표정과 일요일. 하지-에이의 행방.'),
      ('generic','이런 일이 있었다. 일이 생겼다. 모든 일을 기억한다.'),
      ('silver','은을 찾고 은광석을 보았다.'),
      ('work','일거리를 찾고 있다.'),
      ('explicit','할 @일#이 있다. @하즈-에이#의 행방을 물었다.'),
      ('overlap','블레이드 교관들에 관해 물었다.'),
      ('old_work','만@일#을 대비하자. 그의 소행@일# 수도 있다. 정상 @작동#한다.'),
      ('old_name','@하지#-@에이#의 행방을 물었다.'),
    ]
    for journal in [False,True]:
        for discovery in [False,True]:
            result=inspect(runner,mod,cases,['은','일','에이','하즈-에이','블레이드','블레이드 교관'],journal,discovery)
            assert result['inside']['targets']==[],result
            assert result['generic']['targets']==[],result
            assert result['silver']['targets']==['은'],result
            assert result['work']['targets']==['일'],result
            assert result['explicit']['targets']==['일','하즈-에이'],result
            assert result['old_work']['targets']==[],result
            if journal and not discovery:
                assert result['old_name']['targets']==['하즈-에이'],result
                assert result['old_name']['text']=='하지-에이의 행방을 물었다.'
            expected=['블레이드','블레이드 교관'] if discovery else ['블레이드 교관']
            assert result['overlap']['targets']==expected,result
print('PASS: KR12 display/discovery boundaries, ambiguous work noun, explicit work links, silver, compound names and overlap policy')
