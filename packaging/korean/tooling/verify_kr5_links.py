"""Compare every journal entry with the actual OpenMW parser adapter.

Tests both newly generated records and unchanged KR4 text using the new runtime.
The corpus is not a substitute for a reporter save; heard-topic fixtures are explicit.
"""
from pathlib import Path
import argparse, struct, subprocess, tempfile, json, re
from build_kr5_data import records, fields

def corpus(mod):
    topics=set();entries=[];kind=None
    for tag,body,_,_ in records((mod/'Morrowind_Korean_ReTranslation.esp').read_bytes()):
        fs=dict(fields(body))
        if tag==b'DIAL':
            kind=fs.get(b'DATA',b'\xff')[0]
            if kind==0:topics.add(fs[b'NAME'].rstrip(b'\0').decode('utf-8'))
        elif tag==b'INFO' and kind==4 and b'NAME' in fs:
            entries.append((fs[b'INAM'].rstrip(b'\0').decode('ascii'),fs[b'NAME'].rstrip(b'\0').decode('utf-8')))
    return sorted(topics),entries

def table(path):
    return dict(line.split('\t',1) for line in path.read_text('utf-8-sig').splitlines() if '\t' in line)

def inspect(runner,mod,entries,topics,patched,discovery=False):
    forms=table(mod/'Morrowind_Korean_ReTranslation.top')
    keywords=table(mod/'Morrowind_Korean_ReTranslation.mrk')
    with tempfile.TemporaryDirectory(prefix='kr5-engine-') as tmp:
        src,dst=Path(tmp)/'in.bin',Path(tmp)/'out.bin'
        def write_string(f,s):
            raw=s.encode('utf-8');f.write(struct.pack('<I',len(raw)));f.write(raw)
        with src.open('wb') as f:
            for pairs in [[(t,keywords.get(t,t)) for t in topics],list(forms.items())]:
                f.write(struct.pack('<I',len(pairs)))
                for a,b in pairs:write_string(f,a);write_string(f,b)
            f.write(struct.pack('<I',len(entries)))
            for _,s in entries:write_string(f,s)
        command=[str(runner),str(src),str(dst),str(mod),'patched' if patched else 'legacy']
        if discovery:command.append('discovery')
        subprocess.run(command,check=True)
        data=dst.read_bytes();p=0
        def count():
            nonlocal p
            n=struct.unpack_from('<I',data,p)[0];p+=4;return n
        def read_string():
            nonlocal p
            n=count();s=data[p:p+n].decode('utf-8');p+=n;return s
        assert count()==len(entries)
        out={}
        for info,_ in entries:
            n=count();text=read_string();targets=[read_string() for _ in range(n)]
            out[info]={'text':text,'targets':targets}
        assert p==len(data)
        return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--old-mod',type=Path,required=True)
    ap.add_argument('--new-mod',type=Path,required=True)
    ap.add_argument('--runner',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    old,new=a.old_mod.resolve(),a.new_mod.resolve();runner=a.runner.resolve()
    topics,entries=corpus(old);new_topics,new_entries=corpus(new)
    assert topics==new_topics
    before=inspect(runner,old,entries,topics,False)
    saved=inspect(runner,new,entries,topics,True)
    after=inspect(runner,new,new_entries,topics,True)
    assert before.keys()==saved.keys()==after.keys()
    for key in before:assert before[key]['text']==saved[key]['text']==after[key]['text'],key
    mine='칼데라 에보니 광산'
    cases=['10356287601274130444','2531617332095525831','610522350507519773']
    # Test the exact reported mine with only its topic heard. Do not assume all knowledge.
    mine_before=inspect(runner,old,entries,[mine],False)
    mine_saved=inspect(runner,new,entries,[mine],True)
    for info in cases:
        assert not mine_before[info]['targets']
        assert mine in mine_saved[info]['targets']
    unknown=inspect(runner,new,entries,[],True)
    assert all(not v['targets'] for v in unknown.values())
    forms=table(new/'Morrowind_Korean_ReTranslation.top')
    existing=set(topics);bad_tags=[]
    for info,text in new_entries:
        for raw in re.findall(r'@([^@#]*)#',text):
            shown=raw.rstrip('\x7f');key=shown+'*'*(len(raw)-len(shown))
            if forms.get(key,key) not in existing:bad_tags.append({'info':info,'phrase':shown,'target':forms.get(key,key)})
    assert not bad_tags
    report={
        'unique_topics_checked':len(topics),'journal_entries_checked':len(entries),
        'display_text_identical':True,'invalid_explicit_tag_targets':bad_tags,
        'old_text_legacy_links':sum(len(v['targets']) for v in before.values()),
        'old_text_patched_links':sum(len(v['targets']) for v in saved.values()),
        'new_text_patched_links':sum(len(v['targets']) for v in after.values()),
        'entries_changed_by_global_canonical_seeding':sum(before[k]['targets']!=saved[k]['targets'] for k in before),
        'reported_mine_old_saved_text_cases_repaired':cases,
        'unheard_topics_not_unlocked':True,
        'scope':'Real OpenMW parser, Storage, UTF-8 BOM sidecar loader and file collections. Heard-topic fixtures: all translated topics, only the reported mine, and no heard topics. These are controlled fixtures, not the reporter save.'
    }
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
