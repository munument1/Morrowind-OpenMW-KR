"""Repair reported Korean topic tags into a NEW mod directory."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,struct

STEM='Morrowind_Korean_ReTranslation'
def chunks(data,header):
    pos=0
    while pos<len(data):
        assert pos+header<=len(data)
        tag,size=struct.unpack_from('<4sI',data,pos);end=pos+header+size
        assert end<=len(data)
        yield tag,data[pos+header:end],data[pos:pos+header]
        pos=end
    assert pos==len(data)
def read_forms(path):
    return [line.split('\t',1) for line in path.read_text(encoding='utf-8-sig').splitlines() if '\t' in line]
def patch(source,out,reviewed=None):
    assert not out.exists(),'Output must be a new directory'
    esp=source/(STEM+'.esp');raw=esp.read_bytes()
    pairs=read_forms(source/(STEM+'.top'));forms={}
    for k,v in pairs:forms.setdefault(k,v)
    changes=[];result=[];removed=0;expanded=0;names=0;broad_removed=0
    reviewed_keys={(r['INFO'],r['tag'],r['target']) for r in (reviewed or {}).get('removals',[])}
    reviewed_non_job={'1976331762827310505','30356158691410032642','29424225121377211373'}
    for tag,body,header in chunks(raw,16):
        new_body=body
        if tag==b'INFO':
            fields=list(chunks(body,8));iid=next((v.rstrip(b'\0').decode('ascii') for t,v,h in fields if t==b'INAM'),'')
            packed=[]
            for field,value,subheader in fields:
                new=value
                if field==b'NAME':
                    old=value.rstrip(b'\0').decode('utf8');text=old
                    for bad in ['@하지#-@에이#','하지-@에이#']:
                        names+=text.count(bad);text=text.replace(bad,'@하즈-에이#')
                    expanded+=text.count('@일#거리');text=text.replace('@일#거리','@일거리#')
                    def clean(m):
                        nonlocal removed,broad_removed
                        phrase=m[1];target=forms.get(phrase,phrase)
                        if (iid,phrase,target) in reviewed_keys:
                            broad_removed+=1;return phrase
                        if target=='일' and phrase not in ('일','일거리'):
                            removed+=1;return phrase
                        if iid in reviewed_non_job and phrase=='일':
                            removed+=1;return phrase
                        return m[0]
                    text=re.sub(r'@([^@#]+)#',clean,text)
                    if text!=old:
                        new=text.encode('utf8')+value[len(value.rstrip(b'\0')):]
                        changes.append({'INFO':iid,'before':old,'after':text})
                packed.append(struct.pack('<4sI',field,len(new))+new)
            new_body=b''.join(packed)
        result.append(header[:4]+struct.pack('<I',len(new_body))+header[8:]+new_body)
    patched=b''.join(result)
    # Verify all records, headers and every field outside INFO.NAME byte-for-byte.
    original_records=list(chunks(raw,16));new_records=list(chunks(patched,16))
    assert len(original_records)==len(new_records)
    for (a,av,ah),(b,bv,bh) in zip(original_records,new_records):
        assert a==b and ah[8:]==bh[8:]
        aa=list(chunks(av,8));bb=list(chunks(bv,8));assert len(aa)==len(bb)
        for (x,xv,_),(y,yv,_) in zip(aa,bb):
            assert x==y
            if a!=b'INFO' or x!=b'NAME':assert xv==yv
    shutil.copytree(source,out)
    (out/(STEM+'.esp')).write_bytes(patched)
    for ext in ('top','mrk','jrn'):
        path=out/(STEM+'.'+ext);rows=read_forms(path)
        if ext=='top':
            # Keep legacy forms so the runtime can identify and suppress old
            # saved @작동# and similar tags; newly generated text is cleaned above.
            additions={'일거리':'일','하즈-에이':'하즈-에이','하지-에이':'하즈-에이'}
        elif ext=='mrk':
            rows=[(k,v) for k,v in rows if k!='일'];additions={'일':'일거리'}
        else:additions={'일거리':'일','하지-에이':'하즈-에이'}
        existing={}
        for k,v in rows:existing.setdefault(k,v)
        for k,v in additions.items():
            assert k not in existing or existing[k]==v,(ext,k,existing.get(k),v)
            if k not in existing:rows.append((k,v))
        path.write_text(''.join(k+'\t'+v+'\r\n' for k,v in rows),encoding='utf-8-sig',newline='')
    assert esp.read_bytes()==raw
    report={'input_sha256':hashlib.sha256(raw).hexdigest(),'output_sha256':hashlib.sha256(patched).hexdigest(),
      'INFO_NAME_changes':len(changes),'invalid_work_tags_removed':removed,'full_work_keywords':expanded,
      'additional_reviewed_wrong_tags_removed':broad_removed,
      'proper_name_tags_repaired':names,'other_subrecords':'IDENTICAL','Daedric_BOOK_records':'IDENTICAL',
      'changes':changes,'scope':'New translation data. Historical saved journal text is not rewritten.'}
    return report
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-mod',required=True,type=Path)
    ap.add_argument('--output-mod',required=True,type=Path);ap.add_argument('--report',required=True,type=Path)
    ap.add_argument('--reviewed-tags',type=Path)
    a=ap.parse_args();reviewed=json.loads(a.reviewed_tags.read_text(encoding='utf8')) if a.reviewed_tags else None
    report=patch(a.source_mod,a.output_mod,reviewed)
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='changes'},ensure_ascii=False,indent=2))
