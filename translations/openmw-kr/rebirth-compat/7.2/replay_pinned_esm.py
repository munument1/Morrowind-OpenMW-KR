#!/usr/bin/env python3
"""Fail-closed replay of pinned TR-adjacent Rebirth 7.2 compatibility ESM Korean data.
This does NOT make Rebirth and Tamriel Rebuilt compatible. No game files are modified.
Usage: python replay_pinned_esm.py --mod cyr --input "Project Cyrodiil [For Rebirth].esm" --out cyr-ko.esm
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,mmap,struct
from pathlib import Path
HDR=struct.Struct("<4sIII");SUB=struct.Struct("<4sI")
HERE=Path(__file__).resolve().parent
METADATA={"cyr":("cyr_compatch_build_QA.json","cyr_compatch_translation_delta.jsonl.gz"),
          "sky":("sky_compatch_build_QA.json","sky_compatch_translation_delta.jsonl.gz")}
def sha(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def read_deltas(path):
    with gzip.open(path,"rt",encoding="utf-8") as f:
        items=[json.loads(line) for line in f if line.strip()]
    d={(r["record_index"],r["subrecord_index"]):r for r in items}
    assert len(d)==len(items),("duplicate_record_subrecord",len(items))
    return d
def dump_records(path):
    with path.open("rb") as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
        p=0;i=0
        while p<len(mm):
            assert p+16<=len(mm)
            typ,n,u,flags=HDR.unpack_from(mm,p);e=p+16+n
            assert e<=len(mm)
            fields=[];q=p+16
            while q<e:
                tag,size=SUB.unpack_from(mm,q);a=q+8;b=a+size
                assert b<=e
                fields.append((tag,bytes(mm[a:b])));q=b
            assert q==e
            yield (i,typ,u,flags,fields,bytes(mm[p:e]))
            i+=1;p=e
        assert p==len(mm)
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mod",choices=sorted(METADATA),required=True)
    parser.add_argument("--input",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    manifest_name,deltas_name=METADATA[args.mod]
    manifest=json.loads((HERE/manifest_name).read_text(encoding="utf8"))
    assert args.input.is_file() and sha(args.input)==manifest["input_compatch_sha256"],"input sha mismatch"
    assert args.out.parent.is_dir() and not args.out.exists(),"output must not overwrite an existing file"
    delta=read_deltas(HERE/deltas_name)
    assert len(delta)==manifest["changed_subrecords"]
    seen=set();updated=0;header_changed=0;records=0
    with args.out.open("xb") as out:
        for ri,rt,u,flags,fields,raw in dump_records(args.input):
            records+=1
            newfields=list(fields);dirty=False
            if ri==0:
                assert rt==b"TES3"
                master=None
                for si,(tag,value) in enumerate(fields):
                    if tag==b"MAST":master=value.rstrip(b"\0").decode("ascii")
                    elif tag==b"DATA" and master:
                        if master.lower()=="tamriel_data.esm":
                            assert len(value)==8 and struct.unpack("<Q",value)[0]==14887395
                            newfields[si]=(tag,struct.pack("<Q",18536570))
                            header_changed+=1;dirty=True
                        master=None
            for si,(tag,old) in enumerate(fields):
                key=(ri,si)
                if key not in delta:continue
                assert ri!=0 and (rt,tag) not in ((b"SCPT",b"SCTX"),(b"INFO",b"BNAM"))
                r=delta[key]
                assert rt.decode("ascii")==r["record_type"] and tag.decode("ascii")==r["field"]
                assert hashlib.sha256(old).hexdigest()==r["original_field_sha256"],("original text drift",key)
                assert r["ko"] and "\x00" not in r["ko"]
                suffix=old[len(old.rstrip(b"\0")):]
                new=r["ko"].encode("utf-8")+suffix
                assert hashlib.sha256(new).hexdigest()==r["output_field_sha256"],("output text drift",key)
                assert old!=new
                newfields[si]=(tag,new);dirty=True;seen.add(key);updated+=1
            if dirty:
                payload=b"".join(SUB.pack(tag,len(value))+value for tag,value in newfields)
                out.write(HDR.pack(rt,len(payload),u,flags)+payload)
            else:out.write(raw)
    assert seen==set(delta) and updated==manifest["changed_subrecords"]
    assert header_changed==1
    assert records==manifest["records"],("record_count_mismatch",records)
    actual=sha(args.out)
    assert actual==manifest["output_compatch_sha256"],("final SHA mismatch",actual)
    print(json.dumps({"status":"PASS","mod":args.mod,"records":records,
                      "translated_fields":updated,"header_size_hints_updated":header_changed,
                      "output_sha256":actual,"path":str(args.out)},ensure_ascii=False))
if __name__=="__main__":main()
