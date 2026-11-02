#!/usr/bin/env python3
"""PFP kr1.2: pinned public kr1.1 artifact -> 2 anchored INFO.NAME edits -> Nexus API checks.
Never touches game files, other mods, or private translation sources.
"""
import argparse, copy, hashlib, json, os, re, struct, sys, urllib.error, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "translations/openmw-kr/pfp/kr1.2.json"
MEMBER = "Patch for Purists.esm"
OUTNAME = "PFP_5.0.7-kr1.2_OpenMW-KR12.6.zip"

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def records(blob, header):
    offset = 0
    while offset < len(blob):
        if offset + header > len(blob):
            raise ValueError("truncated record")
        tag, size = struct.unpack_from("<4sI", blob, offset)
        end = offset + header + size
        if end > len(blob):
            raise ValueError("out of bounds record")
        yield tag, blob[offset:offset+header], blob[offset+header:end]
        offset = end

def fields(blob):
    return [(name, value) for name, _, value in records(blob, 8)]

def text(blob):
    return blob.rstrip(b"\0").decode("utf-8")

def untoken(s):
    return re.sub(r"@([^@#]*)#", lambda m:m[1].rstrip("\x7f"), s)

def patch_esm(source, plan):
    cases = {(c["record_index"], c["subrecord_index"]):c for c in plan["cases"]}
    assert len(cases)==2
    out = []; findings = []; count = 0
    for index, (kind, header, body) in enumerate(records(source, 16)):
        count += 1
        old_fields = fields(body)
        info_id = next((text(v) for t,v in old_fields if t==b"INAM"), "")
        changed = False; next_fields = []
        for sub, (tag, data) in enumerate(old_fields):
            target = cases.get((index,sub))
            if target is None:
                next_fields.append((tag,data)); continue
            assert kind==b"INFO" and tag==b"NAME" and info_id==target["info_id"], (index,sub)
            assert sha(data)==target["field_sha256"], (index,sub,"source drift")
            old = text(data)
            assert old.count(target["original_markup"])==1, (index,sub,"markup mismatch")
            assert target["replacement"]==untoken(target["original_markup"])
            new = old.replace(target["original_markup"],target["replacement"])
            assert untoken(old)==untoken(new)
            new_bytes = new.encode("utf-8")+data[len(data.rstrip(b"\0")):]
            assert sha(new_bytes)==target["expected_field_sha256"], (index,sub,"result drift")
            findings.append({"record_index":index,"subrecord_index":sub,"info_id":info_id,
                "removed_markup":target["original_markup"],
                "old_field_sha256":sha(data),"new_field_sha256":sha(new_bytes)})
            next_fields.append((tag,new_bytes))
            changed = True
        if changed:
            new_body = b"".join(struct.pack("<4sI",t,len(b))+b for t,b in next_fields)
            out.append(kind+struct.pack("<I",len(new_body))+header[8:]+new_body)
        else:out.append(header+body)
    assert {tuple((c["record_index"],c["subrecord_index"])) for c in findings}==set(cases)
    new_esm = b"".join(out)
    assert sha(new_esm)==plan["expected_esm_sha256"]
    # Independent full readback validates that every unrelated subrecord stayed byte-identical.
    unmodified = 0; changed_count = 0
    for idx, (before,after) in enumerate(zip(records(source,16),records(new_esm,16),strict=True)):
        k,head,payload=before; nk,nhead,new_payload=after
        assert k==nk and head[8:]==nhead[8:]
        for j,((tag,raw),(ntag,newraw)) in enumerate(zip(fields(payload),fields(new_payload),strict=True)):
            assert tag==ntag
            if (idx,j) in cases:
                assert raw!=newraw and k==b"INFO" and tag==b"NAME"
                changed_count += 1
            else:
                assert raw==newraw,(idx,j)
                unmodified += 1
    assert changed_count==2 and count==10202 and unmodified==91498,(changed_count,count,unmodified)
    return new_esm, {"records_checked":count,"unchanged_subrecords":unmodified,"changed_info_fields":changed_count,"changes":findings}

def build(input_zip, outdir):
    plan=json.loads(PLAN.read_text(encoding="utf-8"))
    assert sha(input_zip.read_bytes())==plan["source_zip_sha256"],"kr1.1 reference artifact differs"
    with zipfile.ZipFile(input_zip) as src:
        assert src.testzip() is None
        original=src.read(MEMBER)
        assert sha(original)==plan["source_esm_sha256"]
        updated,report=patch_esm(original,plan)
        outdir.mkdir(parents=True,exist_ok=True)
        target=outdir/OUTNAME
        assert not target.exists()
        with zipfile.ZipFile(target,"x",compression=zipfile.ZIP_DEFLATED) as dst:
            for member in src.infolist():
                dst.writestr(copy.copy(member),updated if member.filename==MEMBER else src.read(member.filename))
            dst.writestr("KR1.2-CHANGES.txt",("PFP 5.0.7-kr1.2 for OpenMW KR12.6.\n"
                "Two unresolved explicit topic tags removed (INFO IDs 1946625247392230995 and 1262718877221279099).\n"
                "Visible text, other fields, original TOP/MRK and scripts unchanged. Static QA only.\n").encode("utf-8"))
            dst.writestr("KR1.2-verification.json",json.dumps(report,ensure_ascii=False,indent=2).encode("utf-8"))
        with zipfile.ZipFile(target) as z:
            assert z.testzip() is None
            assert z.read(MEMBER)==updated
            for name in src.namelist():
                if name!=MEMBER:assert z.read(name)==src.read(name)
    report.update({"baseline_kr11_zip_sha256":plan["source_zip_sha256"],"baseline_kr11_esm_sha256":plan["source_esm_sha256"],
        "output_esm_sha256":sha(updated),"output_zip_sha256":sha(target.read_bytes()),
        "gameplay_tested":False,"rebirth_modified":False,"other_package_members_unchanged":True})
    (outdir/(OUTNAME+".sha256")).write_text(report["output_zip_sha256"]+"  "+OUTNAME+"\n",encoding="ascii")
    (outdir/"PFP_kr1.2_verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PFP_KR12_BUILT",json.dumps({"filename":OUTNAME,"sha256":sha(target.read_bytes()),**{k:report[k] for k in ("changed_info_fields","unchanged_subrecords","records_checked")}},ensure_ascii=True))
    return report

def nexus_call(path, key, body=None):
    req=urllib.request.Request("https://api.nexusmods.com"+path,
        headers={"apikey":key,"Accept":"application/json","Content-Type":"application/json","User-Agent":"OpenMW-KR-PFP-KR12-Publisher"},
        data=json.dumps(body,ensure_ascii=False).encode("utf-8") if body is not None else None,
        method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def inspect_nexus(mode, outdir):
    plan=json.loads(PLAN.read_text(encoding="utf-8"))
    key=os.environ["NEXUS_KEY"]
    my_id=str(nexus_call("/v1/users/validate.json",key)["user_id"])
    mod=nexus_call("/v1/games/morrowind/mods/60826.json",key)
    assert str(mod["user"]["member_id"])==my_id,"Nexus ownership mismatch"
    assert str(mod["uid"])=="429496790426"
    group=nexus_call("/v3/mods/429496790426/files",key)["data"]["mod_files"]
    assert any(str(x["id"])==plan["nexus_existing_file_group"] and x["is_active"] for x in group)
    if mode=="preflight":
        assert str(mod["version"]).casefold()==plan["source_version"], "Nexus version already changed; refuse duplicate upload"
        status={"preflight":"PASS","owned":True,"nexus_version":mod["version"],"file_group":plan["nexus_existing_file_group"]}
    else:
        assert str(mod["version"]).casefold()==plan["target_version"],("Nexus version not yet updated",mod["version"])
        version_info=nexus_call("/v3/mod-files/8280147/versions",key)["data"]["versions"]
        matching=[x for x in version_info if str(x.get("version","")).casefold()==plan["target_version"] and str(x.get("category","")).casefold()!="removed"]
        assert len(matching)==1,matching
        status={"nexus_metadata":"PASS","owned":True,"nexus_version":mod["version"],"version_records":len(matching),
            "game_scoped_file_id":matching[0].get("game_scoped_id"),
            "CDN_sha256_verified":False,"CDN_reason":"Not checked; previous Nexus CDN 403 from Actions"}
        detail="kr1.2: 명시 링크 목표가 확인되지 않는 2개 대사의 잘못된 링크 태그를 제거. 한국어 표시문장, 그 밖의 번역 및 TOP/MRK·퀘스트 조건·스크립트 보존. OpenMW KR12.6 기준 정적 검증 통과, 실게임 미검증."
        changelogs=nexus_call("/v1/games/morrowind/mods/60826/changelogs.json",key)
        if not any(x.casefold()==plan["target_version"].casefold() for x in changelogs):
            nexus_call("/v3/mods/429496790426/changelogs",key,{"version":plan["target_version"],"changelog":detail})
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/("pfp_nexus_"+mode+".json")).write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PFP_NEXUS_"+mode.upper(),json.dumps(status,ensure_ascii=True))

def main():
    p=argparse.ArgumentParser(); p.add_argument("--archive",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--nexus-preflight",action="store_true")
    p.add_argument("--nexus-verify",action="store_true")
    opts=p.parse_args()
    if opts.nexus_preflight:inspect_nexus("preflight",opts.out)
    elif opts.nexus_verify:inspect_nexus("verify",opts.out)
    else:
        assert opts.archive is not None
        build(opts.archive,opts.out)
if __name__=="__main__":main()
