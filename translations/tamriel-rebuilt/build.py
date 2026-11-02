"""Rebuild kr0.1 from user-owned originals. Standard library; no downloads."""
import argparse,collections,gzip,hashlib,json,re,struct
from pathlib import Path
DATA=Path(__file__).resolve().parent/'26.11.2-kr0.1'
def sha(blob):return hashlib.sha256(blob).hexdigest()
def rows(name):
    with gzip.open(DATA/name,'rt',encoding='utf8') as f:return [json.loads(l) for l in f if l.strip()]
def records(blob):
    cursor=0;ri=0
    while cursor<len(blob):
        assert cursor+16<=len(blob)
        tag,n,unknown,flags=struct.unpack_from('<4sIII',blob,cursor)
        end=cursor+16+n;assert end<=len(blob)
        parts=[];p=cursor+16
        while p<end:
            assert p+8<=end
            kind,size=struct.unpack_from('<4sI',blob,p);a=p+8;z=a+size;assert z<=end
            parts.append((kind,a,z));p=z
        assert p==end
        yield ri,tag,unknown,flags,parts
        cursor=end;ri+=1
    assert cursor==len(blob)
def load():
    manifest=json.loads((DATA/'manifest.json').read_text(encoding='utf8'))
    for name,digest in manifest['files_sha256'].items():assert sha((DATA/name).read_bytes())==digest,name
    data=[rows('TR_Mainland.en_ko.jsonl.gz'),rows('TR_Factions.en_ko.jsonl.gz')]
    assert [len(rs) for rs in data]==[90106,318]
    assert [sum(r['applied'] for r in rs) for rs in data]==[88521,315]
    layout=re.compile(r'<[^>]*>|@[^\r\n#]+#|\r\n|\n|\r');variables=re.compile(r'%[A-Za-z_][A-Za-z_0-9]*')
    for rs in data:
        seen=set()
        for r in rs:
            key=(r['record_index'],r['subrecord_index']);assert key not in seen;seen.add(key)
            if r['applied']:
                assert r['ko'] and '\0' not in r['ko'] and '\ufffd' not in r['ko']
                assert layout.findall(r['en'])==layout.findall(r['ko']),r['row_key']
                assert collections.Counter(variables.findall(r['en']))==collections.Counter(variables.findall(r['ko']))
            else:assert r['ko'] is None
    scripts=rows('TR_Factions.script_display.jsonl.gz');assert sum(r['count'] for r in scripts)==19
    for ext in ('cel','top','mrk','jrn'):
        raw=(DATA/f'TR_Mainland.{ext}').read_bytes();assert raw.startswith(b'\xef\xbb\xbf')
        pairs=[s.split('\t') for s in raw.decode('utf-8-sig').splitlines()]
        assert all(len(p)==2 and all(p) for p in pairs)
        assert len({p[0].casefold() for p in pairs})==len(pairs)
    return manifest,data,scripts
def rebuild(source,target,metadata,rs,scripts,mainland_size=None):
    assert source.resolve()!=target.resolve() and not target.exists()
    raw=source.read_bytes();assert sha(raw)==metadata['source_sha256'],'Wrong original source version'
    db={(r['record_index'],r['subrecord_index']):r for r in rs}
    scriptdb=collections.defaultdict(list)
    for r in scripts:scriptdb[(r['record_index'],r['subrecord_index'])].append(r)
    output=bytearray();used=set();scriptused=set();changed=set()
    for ri,rt,unknown,flags,parts in records(raw):
        body=bytearray();master=None
        for si,(tag,a,z) in enumerate(parts):
            key=(ri,si);old=raw[a:z];new=old;r=db.get(key)
            if r:
                assert r['source_sha256']==metadata['source_sha256']
                assert r['field']==tag.decode('ascii') and r['record_type']==rt.decode('ascii')
                assert sha(old)==r['source_subrecord_sha256']
                assert old.rstrip(b'\0').decode('cp1252')==r['en'];used.add(key)
                if r['applied']:
                    ko=r['ko'].encode('utf8')
                    if rt==b'FACT' and tag==b'RNAM':
                        assert len(old)==32 and len(ko)<32;new=ko.ljust(32,b'\0')
                    else:new=ko+b'\0'*(len(old)-len(old.rstrip(b'\0')))
            if key in scriptdb:
                assert tag==b'SCTX' or (rt==b'INFO' and tag==b'BNAM')
                assert all(sha(old)==s['source_subrecord_sha256'] for s in scriptdb[key])
                restore=[]
                for s in scriptdb[key]:
                    en=b'"'+s['en'].encode('cp1252')+b'"';ko=b'"'+s['ko'].encode('utf8')+b'"'
                    assert new.count(en)==s['count'];new=new.replace(en,ko);restore.append((en,ko))
                restored=new
                for en,ko in restore:restored=restored.replace(ko,en)
                assert restored==old;scriptused.add(key)
            if ri==0:
                if tag==b'MAST':master=old.rstrip(b'\0').decode('ascii')
                elif tag==b'DATA' and master=='TR_Mainland.esm' and mainland_size is not None:
                    assert len(old)==8;new=struct.pack('<Q',mainland_size)
            if new!=old:changed.add(key)
            body+=struct.pack('<4sI',tag,len(new))+new
        output+=struct.pack('<4sIII',rt,len(body),unknown,flags)+body
    assert used==set(db) and scriptused==set(scriptdb)
    assert sha(output)==metadata['output_sha256'],'Output differs from the tested build'
    assert len(output)==metadata['output_bytes']
    original=list(records(raw));built=list(records(output));assert len(original)==len(built)==metadata['records']
    for a,b in zip(original,built):
        assert a[:4]==b[:4] and len(a[4])==len(b[4])
        for si,((t,x,y),(nt,nx,ny)) in enumerate(zip(a[4],b[4])):
            assert t==nt
            if (a[0],si) not in changed:assert raw[x:y]==output[nx:ny]
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(output)
    assert sha(source.read_bytes())==metadata['source_sha256']
    print(json.dumps({'plugin':target.name,'sha256':sha(output),'records':len(built),'result':'PASS'}))
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check-only',action='store_true');ap.add_argument('--mainland-source',type=Path)
    ap.add_argument('--factions-source',type=Path);ap.add_argument('--output-dir',type=Path)
    args=ap.parse_args();manifest,data,scripts=load()
    if args.check_only:print('Translation data, hashes, markup and sidecars: PASS');return
    assert args.mainland_source and args.factions_source and args.output_dir,'Both original sources and a new output directory are required'
    assert not args.output_dir.exists(),'Refuse an existing output directory'
    rebuild(args.mainland_source,args.output_dir/'TR_Mainland.esm',manifest['mainland'],data[0],[])
    rebuild(args.factions_source,args.output_dir/'TR_Factions.esp',manifest['factions'],data[1],scripts,manifest['mainland']['output_bytes'])
    for ext in ('cel','top','mrk','jrn'):
        (args.output_dir/f'TR_Mainland.{ext}').write_bytes((DATA/f'TR_Mainland.{ext}').read_bytes())
if __name__=='__main__':main()
