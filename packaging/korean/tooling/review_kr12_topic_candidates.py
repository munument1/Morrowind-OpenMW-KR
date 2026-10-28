"""Select reviewed, semantically distinct English homonyms/substrings.

Do not treat all lexical audit flags as bugs. Inflections such as enchanted,
talking and escaped are intentionally excluded from these removal rules.
"""
import argparse,json,re
from pathlib import Path
from collections import Counter

REVIEWED_WORDS={
 '쥐':{'rather','rational'}, '샬':{'shall'}, '수드':{'sudden','suddenly','sudanit'},
 '레트테':{'letter','letters'},
 '저자':{'authority','authorities','authoritarian','authorize','authorization'},
 '계획':{'plant','plants','plantation','plantations','planting','planted'},
 '벌금':{'finest','finesse','finesht'}, '마라':{'marauding','marayn','marandus'},
 '바스':{'vast','vasesius'},'단검':{'daggerfall'}, '핸드':{'handsome','handsomely'},
 '선물':{'presently'}, '영장':{'write','writes','written','writing','writings','writer','writers'},
 '필요한 것':{'needle','needles'}, '나를 섬기다':{'serve members'}, '당신을 안다':{'know your'},
}
def containing_words(row):
    out=set()
    for name in row['English_topic_candidates']:
        for m in re.finditer(re.escape(name),row['original'] or '',re.I):
            left=re.search(r'[A-Za-z]*$',row['original'][:m.start()])[0]
            right=re.match(r'[A-Za-z]*',row['original'][m.end():])[0]
            out.add((left+m[0]+right).lower())
    return out
def select(audit):
    approved=[]
    for row in audit['findings']:
        words=containing_words(row)
        reason=None
        if 'source_only_inside_English_word' in row['categories']:
            allowed=REVIEWED_WORDS.get(row['target'],set())
            if words and words<=allowed:reason='reviewed_English_substring_or_homonym'
        if row['target']=='곰' and re.search(r'\bbears?\s+responsibilit',row['original'] or '',re.I):
            reason='bear_responsibility_is_not_animal'
        if row['target']=='힘' and row['tag'] in ('모르지.','정원이 찼다고'):
            reason='unit_manning_is_not_strength_attribute'
        if row['target']=='눈' and '스노' in row['tag']:
            reason='Snow_name_or_Snow_Elves_is_not_weather'
        if row['target']=='팁' and row['tag'] in ('곶에 있는','아헤무사'):
            reason='geographic_tip_is_not_gratuity'
        if row['target']=='은' and row['INFO']=='1950436122867025594':
            reason='silver_tongued_is_not_silver_material'
        if row['target']=='꽃' and '황금' in row['context'] and '코너클럽' in row['text']:
            reason='Flowers_of_Gold_is_a_cornerclub_name'
        if reason:
            approved.append({'INFO':row['INFO'],'tag':row['tag'],'target':row['target'],
                'reason':reason,'context':row['context'],'original':row['original'],'containing_words':sorted(words)})
    return {'status':'REVIEWED_REMOVALS_ONLY','count':len(approved),
      'by_target':dict(Counter(r['target'] for r in approved)),
      'unapproved_flags_retained':True,'removals':approved}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=select(json.loads(a.audit.read_text(encoding='utf8')))
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in r.items() if k!='removals'},ensure_ascii=False,indent=2))
