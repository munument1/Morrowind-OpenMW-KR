# -*- coding: utf-8 -*-
"""Stage a 5-INFO-name-only KR12.6 guild-join candidate; never publish it."""
from __future__ import annotations
import hashlib,json,re,struct,zipfile
from pathlib import Path
def sha(raw): return hashlib.sha256(raw).hexdigest()
def decode(raw, encoding="utf-8"): return raw.rstrip(b"\x00").decode(encoding, errors="replace")
def records(raw):
    pos=0
    while pos<len(raw):
        if pos+16>len(raw): raise RuntimeError("short TES3 record")
        tag,n=struct.unpack_from("<4sI",raw,pos)
        end=pos+16+n
        if end>len(raw): raise RuntimeError("bad TES3 record length")
        yield tag, raw[pos+16:end]
        pos=end
def fields(raw):
    pos=0; out=[]
    while pos<len(raw):
        if pos+8>len(raw): raise RuntimeError("short TES3 subrecord")
        tag,n=struct.unpack_from("<4sI",raw,pos)
        end=pos+8+n
        if end>len(raw): raise RuntimeError("bad TES3 subrecord length")
        out.append((tag,raw[pos+8:end]))
        pos=end
    return out


ROOT=Path.cwd()
SOURCE=ROOT/"Morrowind-Korean-OpenMW-0.51.0-KR12.6-Full.zip"
OUTPUT=ROOT/"Morrowind-Korean-OpenMW-0.51.0-KR12.7-Full.zip"
REPORT=ROOT/"KR12.7-source-guarded-verification.json"
ESP_SHA="c52a5355752ef0be93fadeca9c95ca00d7cad808f713ce92a624a67d0cc277df"
ZIP_SHA="2f4bb6b9cfd5916fd9574b6207628e4bb16f8bdc4f1c68fc1ef7581c970989e9"
LINK=re.compile(r"@([^@#]+)#")
SPECS=[
 ("1341756011233729353","평신도 회원","제국 교단에 가입","제국 교단에 가입하시겠습니까?"),
 ("13288348632198840","전사 길드","전사 길드에 가입","전사 길드에 가입하려는 건가?"),
 ("2435795662798020478","전사 길드","전사 길드에 가입","전사 길드에 가입하려는 건가?"),
 ("22990247762784528944","승진","텔바니 가문에 가입","텔바니 가문에 가입하겠나?"),
 ("41295659805015760","임무","마법사 길드에 가입","마법사 길드에 가입하겠나?"),
]
def display(x):
    return LINK.sub(lambda m:m.group(1).replace("\x7f",""),x).replace("\x7f","")
def repack(tag,body):
    return tag+struct.pack("<I",len(body))
def patch(esp):
    idx=0;parent=None
    seen=set();entries=[];parts_out=[]
    pos=0
    while pos<len(esp):
        tag,n=struct.unpack_from("<4sI",esp,pos)
        stop=pos+16+n
        raw=esp[pos:stop]
        body=esp[pos+16:stop]
        if tag==b"DIAL":
            parent=decode(dict(fields(body)).get(b"NAME",b""),"utf-8")
        if tag==b"INFO":
            f=fields(body);data=dict(f)
            fid=decode(data.get(b"INAM",b""),"utf-8")
            matching=[(i,s) for i,s in enumerate(SPECS) if s[0]==fid and s[1]==parent]
            if len(matching)>1:raise RuntimeError("Ambiguous INFO target")
            if matching:
                spec_index,(_,_,topic,plain)=matching[0]
                if spec_index in seen:raise RuntimeError("INFO duplicated")
                seen.add(spec_index)
                before=decode(data.get(b"NAME",b""),"utf-8")
                if before.count(plain)!=1:
                    raise RuntimeError(f"Pinned Korean text changed: {fid} ({before[:130]!r})")
                link="@"+topic+"#"
                if link in before:raise RuntimeError("Already patched")
                after=before.replace(plain,plain.replace(topic,link,1))
                if display(before)!=display(after):
                    raise RuntimeError("UI visible text changed")
                original_name=data[b"NAME"]
                terminator=original_name[len(original_name.rstrip(b"\x00")):]
                replacement=after.encode("utf-8")+terminator
                newfields=[]
                seen_name=False
                for subtag,rawval in f:
                    if subtag==b"NAME":
                        if seen_name:raise RuntimeError("Multiple NAME fields")
                        seen_name=True
                        rawval=replacement
                    newfields.append(subtag+struct.pack("<I",len(rawval))+rawval)
                if not seen_name:raise RuntimeError("Missing NAME")
                newbody=b"".join(newfields)
                raw=tag+struct.pack("<I",len(newbody))+esp[pos+8:pos+16]+newbody
                entries.append({"INFO":fid,"DIAL":parent,"target":topic,
                    "source_text":before,"candidate_text":after,
                    "original_NAME_sha256":sha(original_name),"candidate_NAME_sha256":sha(replacement),
                    "visible_text_unchanged":True,"source_condition_bytes_preserved":True,
                    "source_result_script_bytes_preserved":True})
        parts_out.append(raw)
        pos=stop;idx+=1
    if len(seen)!=len(SPECS):raise RuntimeError(f"Not all records found: {seen}")
    if idx!=48146:raise RuntimeError(f"Unexpected record total {idx}")
    target=b"".join(parts_out)
    # Independently verify only exactly these five INFO.NAME subrecords changed.
    num=0;record_count=0;parent=None
    for (oldtag,oldbody),(newtag,newbody) in zip(records(esp),records(target)):
        record_count+=1
        if oldtag!=newtag:raise RuntimeError("Changed record type")
        if oldbody==newbody:continue
        if oldtag!=b"INFO":raise RuntimeError("Changed non-INFO")
        oldfields=fields(oldbody);newfields=fields(newbody)
        if len(oldfields)!=len(newfields):raise RuntimeError("Subrecord count drift")
        changed=[]
        for (a,x),(b,y) in zip(oldfields,newfields):
            if a!=b:raise RuntimeError("Subrecord order drift")
            if x!=y:
                if a!=b"NAME" or display(decode(x,"utf-8"))!=display(decode(y,"utf-8")):
                    raise RuntimeError("Unexpected changed field or display")
                changed.append(a)
        if changed!=[b"NAME"]:raise RuntimeError("Unexpected multiple changes")
        num+=1
    if num!=5 or record_count!=48146:
        raise RuntimeError("Independent TES3 QA failed")
    return target,entries,idx,num
def main():
    if OUTPUT.exists() or REPORT.exists():raise RuntimeError("Refuse overwriting earlier result")
    if sha(SOURCE.read_bytes())!=ZIP_SHA:raise RuntimeError("ZIP source integrity mismatch")
    with zipfile.ZipFile(SOURCE) as src:
        member=next(n for n in src.namelist() if n.endswith("/Morrowind_Korean_ReTranslation.esp"))
        raw=src.read(member)
        if sha(raw)!=ESP_SHA:raise RuntimeError("ESP source integrity mismatch")
        target,entries,total,changed=patch(raw)
        with zipfile.ZipFile(OUTPUT,"w") as dest:
            for info in src.infolist():
                dest.writestr(info,target if info.filename==member else src.read(info.filename))
    with zipfile.ZipFile(SOURCE) as orig,zipfile.ZipFile(OUTPUT) as candidate:
        if candidate.testzip() or orig.namelist()!=candidate.namelist():
            raise RuntimeError("Result archive invalid")
        changed_members=[name for name in orig.namelist() if orig.read(name)!=candidate.read(name)]
        if changed_members!=[member]:raise RuntimeError(f"Unexpected ZIP entries: {changed_members}")
    report={"status":"KR12_7_STATIC_VERIFIED","source_zip_sha256":ZIP_SHA,
         "source_ESP_sha256":ESP_SHA,"candidate_ESP_sha256":sha(target),
         "candidate_zip_sha256":sha(OUTPUT.read_bytes()),
         "changed_INFO_NAME":changed,"total_TES3_records":total,
         "all_other_fields_and_ZIP_members_unmodified":True,
         "player_NPC_quest_state_tested":False,
         "native_C++_parser_success_from_GitHub_Action":"https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/41644351838",
         "cases":entries}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("UNRELEASED_GUILD_JOIN_CANDIDATE="+json.dumps({
         "changes":changed,"esp_sha256":report["candidate_ESP_sha256"],
         "zip_sha256":report["candidate_zip_sha256"],
         "zip_size":OUTPUT.stat().st_size,
         "display_text_preserved":True,"release_published":False},ensure_ascii=True))
if __name__=="__main__":main()

[executed on device: Deck_Seung (a3b70f16-4906-418e-a5c0-ee1efec6a325)]