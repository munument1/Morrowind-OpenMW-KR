"""Rebuild a pinned, isolated Cyr_Main test ESM from the bilingual dataset."""
import argparse,collections,gzip,hashlib,json,re,struct
from pathlib import Path
BASE=Path(__file__).resolve().parent/'26.09a'
H=struct.Struct('<4sIII');S=struct.Struct('<4sI')
def digest(data):return hashlib.sha256(data).hexdigest()
def records(data):
    pos=0;index=0
    while pos<len(data):
        assert pos+H.size<=len(data)
        typ,size,unknown,flags=H.unpack_from(data,pos);end=pos+H.size+size
        assert end<=len(data);p=pos+H.size;subs=[]
        while p<end:
            assert p+S.size<=end
            tag,n=S.unpack_from(data,p);a=p+S.size;b=a+n;assert b<=end
            subs.append((tag,a,b));p=b
        assert p==end
        yield index,typ,unknown,flags,subs
        pos=end;index+=1
    assert pos==len(data) and index>0
def load():
    m=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
    raw=(BASE/'Cyr_Main.en_ko.jsonl.gz').read_bytes();assert digest(raw)==m['bilingual_gzip_sha256']
    rows=[json.loads(l) for l in gzip.decompress(raw).decode('utf8').splitlines()]
    assert len(rows)==m['rows']==len({r['row_key'] for r in rows})
    for r in rows:
        en,ko=r['en'],r['ko'];assert r['source_sha256']==m['source_sha256']
        assert ko and not any(c in ko for c in '\0\ufffd\ufeff')
        for pat in [r'<[^>]*>|@[^\r\n#]+#|\r\n|\r|\n',r'%[A-Za-z_][A-Za-z0-9_]*',r'(?<![A-Za-z0-9_])(?:Sky|sky|T|TR|Cyr)_[A-Za-z0-9_]+(?![A-Za-z0-9_])']:
            a=re.findall(pat,en);b=re.findall(pat,ko)
            assert (a==b if pat.startswith('<') else collections.Counter(a)==collections.Counter(b)),r['row_key']
    assert dict(collections.Counter(r['review_status'] for r in rows))==m['review_counts']
    return m,rows
def main():
    p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');p.add_argument('--source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    m,rows=load()
    if a.check_only:print(json.dumps({'rows':len(rows),'dataset_qa':'PASS','review_counts':m['review_counts']}));return
    if not a.source or not a.output:p.error('--source and --output are required')
    assert a.source.resolve()!=a.output.resolve(),'Never overwrite the original plugin'
    assert not a.output.exists(),'Choose a fresh output path'
    source=a.source.read_bytes();assert digest(source)==m['source_sha256'],'Wrong original mod version'
    wanted={(r['record_index'],r['subrecord_index']):r for r in rows};built=bytearray();used=set()
    for ri,typ,unknown,flags,subs in records(source):
        payload=bytearray()
        for si,(tag,start,end) in enumerate(subs):
            raw=source[start:end];r=wanted.get((ri,si))
            if r:
                assert typ.decode()==r['record_type'] and tag.decode()==r['field']
                assert start==r['source_offset'] and digest(raw)==r['source_subrecord_sha256']
                assert raw.rstrip(b'\0').decode('cp1252')==r['en']
                raw=r['ko'].encode('utf8')+b'\0'*(len(raw)-len(raw.rstrip(b'\0')));used.add((ri,si))
            payload+=S.pack(tag,len(raw))+raw
        built+=H.pack(typ,len(payload),unknown,flags)+payload
    assert used==set(wanted)
    assert digest(built)==m['test_ESM_sha256'],'Rebuild does not match verified test ESM'
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(built)
    print(json.dumps({'output':str(a.output),'sha256':digest(built),'test_only':True,'game_applied':False}))
if __name__=='__main__':main()
