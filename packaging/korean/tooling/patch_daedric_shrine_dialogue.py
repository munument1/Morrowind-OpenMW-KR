"""Translate Daedric shrine spoken subtitles embedded in TES3 script sources.

The shrine voices are Player->Say calls in SCPT/SCTX, not DIAL/INFO records.
All quest decisions, journal progression, voices and other records are preserved.
Works with the installed pre-KR5 translation and the full KR5 release payload.
Never writes into either input directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
from pathlib import Path


# The exact Vo/Misc basename uniquely identifies each spoken subtitle.
# Names follow the existing Korean ESP journals and item translations.
SUBTITLES = {
    "DA_AzuraIntro1.wav": (
        "너는 이유가 있어 이곳에 왔다. 아직 그 이유를 모를 수도 있겠지. "
        "셰오고라스와 나는 내기를 했다. 그는 고독이 광기를 낳는다고 주장하지만, "
        "나는 고독이 위안과 명상의 기회를 준다고 믿는다. 이를 시험하려고 사제 한 명을 "
        "다곤 펠 북쪽의 섬에서 홀로 살게 했다. 그녀가 백 년 동안 기도를 이어 가며 "
        "그곳에서 살아간다면 내 주장이 옳다는 것이 증명된다. 그렇지 못하면 셰오고라스가 내기에서 이긴다."
    ),
    "DA_AzuraIntro2.wav": (
        "이제 기한이 거의 다 되었고, 그녀는 흔들림 없이 버티고 있다. 하지만 셰오고라스가 "
        "결과를 자기에게 유리하게 바꾸려 하고 있지. 그 섬으로 가서 그의 수하들을 몰아내고 "
        "그가 내기에 개입했다는 증거를 가져와라. 단, 그 현명한 여인을 방해해서는 안 된다. "
        "그러면 내기 자체가 무효가 된다. 나를 위해 일하면 후하게 보상하겠다."
    ),
    "DA_AzuraComplete.wav": (
        "잘했다, 필멸자여. 네 덕분에 셰오고라스와의 내기가 공정하게 지켜졌다. "
        "이제 결말은 데이드라 군주의 간섭이 아닌 운명에 따라 정해질 것이다. "
        "이것을 받아 현명하게 사용하여라."
    ),
    "DA_AzuraFail.wav": (
        "필멸자여, 너 때문에 내가 내기에서 졌다. 이제 셰오고라스가 결과에 개입했다는 "
        "사실도 아무 의미가 없다. 너는 실패했다. 어쩌면 그 또한 네 운명이겠지."
    ),
    "DA_BoethiahIntro1.wav": (
        "필멸자여, 내게 무엇을 원하는가? 내 성소는 폐허가 되었고 사제들은 나를 잊었다. "
        "네가 내 성소를 다시 세우겠느냐? 예전의 영광을 되찾아 주겠느냐? "
        "이 일을 해내면 보상하겠다. 내 전설적인 검 골드브랜드를 네게 주지. "
        "이 일을 도와줄 자가 하나 있다. 잘 들어라..."
    ),
    "DA_BoethiahIntro2.wav": (
        "거친 손으로 돌을 매끄럽게, 뼈 대신 바위를 새기네. "
        "칼데라에서 예술가가 기다리니, 걸작을 만들 차례라네. "
        "돌에 형태를 새길 자를 찾아라. 이제 가라."
    ),
    "DA_BoethiahComplete.wav": (
        "잘했다. 이 성소는 내게 걸맞은 곳이다. 이제 이 땅에 다시 내 힘이 퍼지리라. "
        "필멸자여, 이것을 받아라. 골드브랜드를 굳센 손으로 휘둘러 "
        "내 성소가 다시 일어났음을 모두에게 알려라!"
    ),
    "DA_MalacathIntro1.wav": (
        "오크여, 나를 불렀느냐? 동족의 명예를 되찾으러 왔느냐? "
        "내게는 다크 엘프의 '영웅' 오레인 베어클로의 투구가 있다. "
        "그는 수많은 업적을 남겼다고 하지만 거짓 영웅이다. "
        "그 모든 업적은 그의 오크 친구 카라그 그로-카르가 세운 것이지. "
        "이제 거짓 영웅의 전설에 종지부를 찍어야 한다. "
        "그 혈통의 마지막 후손을 찾아 죽여라. 그러면 투구를 주겠다. "
        "인간 신이 사는 도시에서 그자를 찾아라."
    ),
    "DA_MalacathIntro2.wav": (
        "나를 불렀느냐? 흥, 너희는 모두 똑같군. 하지만 내게 쓸모가 있을지도 모르지. "
        "내게는 다크 엘프의 '영웅' 오레인 베어클로의 투구가 있다. "
        "그는 많은 업적을 남겼다지만 거짓 영웅이다. "
        "그 모든 업적은 그의 오크 친구 카라그 그로-카르가 세운 것이지. "
        "이제 그 거짓 전설에 종지부를 찍어야 한다. "
        "그 혈통의 마지막 후손을 찾아 죽여라. 그러면 투구를 주겠다. "
        "인간 신이 사는 도시에서 그자를 찾아라."
    ),
    "DA_MalacathComplete.wav": (
        "네가 거짓 영웅을 죽여 그의 혈통을 끊었구나. "
        "오크 종족의 명예를 되찾는 데 힘을 보태 주어 기쁘다. "
        "자, 오레인 베어클로의 투구를 받아라. 당당히 쓰고 다니며 "
        "진실이 무엇이었는지 모두에게 일깨워라."
    ),
    "DA_MehrunesIntro.wav": (
        "하찮은 필멸자여, 어찌 감히 나를 부르느냐? "
        "그토록 빨리 죽고 싶은 것이냐? 지금 당장 널 짓밟아 버려야 마땅하겠지만, "
        "내 앞에 다가올 배짱은 인정해 주마. 작은 녀석치고 야망이 대단하군."
    ),
    "DA_MehrunesComplete.wav": (
        "내 면도날을 찾아왔군. 좋다. 이 무기의 굶주림이 느껴지느냐? "
        "그 좌절이 느껴지느냐? 이제 이 무기를 과거의 모습, 영원히 간직해야 할 모습으로 되돌리겠다. "
        "메이룬스 데이건의 이름으로 온 땅에 피의 길을 그어라!"
    ),
    "DA_MehrunesChoice1.wav": (
        "너는 용감하거나 어리석군. 어쩌면 둘 다겠지. 그렇다면 용기를 증명할 기회를 주마. "
        "인간과 엘프를 도륙하고 앞을 가로막는 자들을 쓸어버리던 내 면도날이 잠들어 있다. "
        "쓸모없고 겁쟁이인 엘프가 훔쳐 간 뒤, 무기는 몰라그 마르 근처 알라스 무덤에 "
        "먼지만 뒤집어쓴 채 방치되어 있지. 필멸자여, 그것을 내게 가져와라. "
        "메이룬스의 면도날을 지닐 자격이 있음을 증명하여라."
    ),
    "DA_MehrunesChoice2.wav": (
        "역시 그 이상은 기대하지 않았다. 당장 이곳을 떠나라. 그렇지 않으면 그 자리에서 죽을 것이다."
    ),
    "DA_MephalaComplete.wav": (
        "잘했다, 필멸자여. 질서를 지키려면 반드시 해야 하는 일도 있는 법이지. "
        "이 일이 세상에 알려졌을 때 벌어질 소동도 내게는 즐거움이 될 것이다. "
        "벌써 기대되는구나. 필멸자여, 이 반지를 받아라. "
        "한낮의 밝은 햇빛 아래서도 빠르고 은밀하게 움직일 수 있을 것이다. 이제 물러가라."
    ),
    "DA_MolagBalIntro1.wav": (
        "지금 어찌하여 나를 부르느냐? 나약한 놈아, 네 애원을 들어 줄 시간 따위는 없다. "
        "내게는 더 중요한 일이 있다. 멘타 나! 그놈의 오만함에는 반드시 대가를 치르게 하겠다! "
        "잘 들어라. 나를 섬기는 자들은 내 명령에 복종해야 한다. "
        "그러지 않으면 영원한 고통을 맛보리라. 필멸자여, 너도 나를 섬겨야 한다."
    ),
    "DA_MolagBalIntro2.wav": (
        "멘타 나는 게으르고 태만해졌다. 지상에서는 아무도 해를 입지 않고 살아가는데, "
        "그놈은 비루한 동굴에 처박혀 있지. 공포를 불러일으키도록 태어난 괴물이다! "
        "인간과 엘프 사이에 두려움과 불화를 퍼뜨리는 것이 놈의 사명인데, "
        "동굴에 틀어박혀 내 뜻을 조롱하고 있단 말이다!"
    ),
    "DA_MolagBalIntro3.wav": (
        "필멸자여, 그놈을 죽여라. 영혼을 외부 영역으로 보내라. "
        "내 명령을 거역한 대가로 영원한 고문을 가하겠다. 이 열쇠를 받아라. "
        "코고룬 동쪽 코라-두르의 동굴에 놈이 있다. "
        "그 게으른 멍청이를 죽여라. 해낸다면 내 총애를 얻게 될 것이다."
    ),
    "DA_MolagBalComplete.wav": (
        "아, 멘타 나의 영혼을 풀어 주었구나! 이제 놈에게는 끝없는 고통만이 있을 것이다. "
        "세상이 끝날 때까지 영원한 고문을 맛보리라. 필멸자여, 잘했다. "
        "언젠가 다시 나를 섬길 수도 있겠군. 이것을 받아 잘 사용해라. "
        "어디를 가든 분쟁과 불화를 불러일으켜라. 이제 가라."
    ),
    "DA_SheogorathIntro.wav": (
        "뭐냐, 필멸자? 이 셰오고라스를 위해 봉사하러 왔느냐? "
        "그런 생각을 했다는 것부터 이미 제법 미쳤다는 증거지. 아주 마음에 들어. "
        "알드 레다이니아 근처에 사는 미친 은둔자에게서 호리필레이션의 포크를 가져와라. "
        "그자를 조심해라. 그리... 안정된 사람은 아니거든."
    ),
    "DA_SheogorathIntro2.wav": (
        "필멸자여, 그 포크를 현명하게 사용해라. 그것을 휘두르고도 변하지 않은 사람은 드물지. "
        "은둔자 근처에 사는 거대한 수컷 네치에게 그 포크로 최후의 일격을 가해라. "
        "해낸 뒤 호리필레이션의 포크를 가져오면 이 셰오고라스가 후하게 보상해 주마."
    ),
    "DA_SheogorathComplete.wav": (
        "아... 내 심부름을 끝냈구나. 잘했다. 너도 광기의 맛을 좀 보았겠지? "
        "필멸자여, 광기가 저주라고 생각하지 마라. 어떤 자에게는 가장 큰 축복이거든. "
        "어쩌면 쓰디쓴 자비겠지만, 그래도 자비는 자비지. "
        "호리필레이션의 포크를 내놓아라. 네게 더 어울리는 물건이 있는 듯하니까. "
        "이제 가라. 네가 본 것들을 기억해라."
    ),
}

SCRIPT_NAMES = {
    "DaedraAzura",
    "DaedraBoethiah",
    "DaedraBoethiah2",
    "DaedraMalacath",
    "DaedraMehrunes",
    "DaedraMephala",
    "DaedraMolagBal",
    "DaedraSheogorath",
}
SCRIPT_SAY = re.compile(
    r'(?im)(\bPlayer\s*->\s*Say\s+"[^"\r\n]*?\\([^"\\\r\n]+\.wav)"\s*,\s*")([^"\r\n]*)(")'
)
SCRIPT_NAME_SIZE = 32


def records(data: bytes):
    offset = 0
    while offset < len(data):
        if offset + 16 > len(data):
            raise ValueError("Truncated TES3 record header")
        tag, size, unknown, flags = struct.unpack_from("<4sIII", data, offset)
        end = offset + 16 + size
        if end > len(data):
            raise ValueError("Truncated TES3 record body")
        yield tag, data[offset + 16:end], unknown, flags
        offset = end


def fields(data: bytes):
    offset = 0
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError("Truncated TES3 subrecord header")
        tag, size = struct.unpack_from("<4sI", data, offset)
        end = offset + 8 + size
        if end > len(data):
            raise ValueError("Truncated TES3 subrecord body")
        yield tag, data[offset + 8:end]
        offset = end


def pack_record(tag: bytes, body: bytes, unknown: int, flags: int):
    return struct.pack("<4sIII", tag, len(body), unknown, flags) + body


def pack_fields(parts):
    return b"".join(struct.pack("<4sI", tag, len(value)) + value for tag, value in parts)


def script_name(parts):
    header = next((value for tag, value in parts if tag == b"SCHD"), None)
    if header is None:
        return None
    return header[:SCRIPT_NAME_SIZE].rstrip(b"\0").decode("ascii")


def say_lines(text: str):
    return {match[2].lower(): match[3] for match in SCRIPT_SAY.finditer(text)}


def extract_master_english(master: Path):
    original = {}
    for tag, body, _, _ in records(master.read_bytes()):
        if tag != b"SCPT":
            continue
        parts = list(fields(body))
        name = script_name(parts)
        if name not in SCRIPT_NAMES:
            continue
        src = next(value for key, value in parts if key == b"SCTX")
        lines = say_lines(src.decode("cp1252").rstrip("\0"))
        if not lines:
            raise ValueError(f"No spoken dialogue found in master script {name}")
        for sound, english in lines.items():
            if sound in original:
                raise ValueError(f"Repeated voice filename: {sound}")
            original[sound] = (name, english)
    requested = {key.lower() for key in SUBTITLES}
    if set(original) != requested:
        raise ValueError(
            f"Master voices and translations differ; missing={requested - set(original)}, "
            f"unexpected={set(original) - requested}"
        )
    return original


def patch_esp(data: bytes, english: dict):
    translated = {key.lower(): value for key, value in SUBTITLES.items()}
    changed = set()
    changed_scripts = set()
    output = []
    for tag, body, unknown, flags in records(data):
        if tag == b"SCPT":
            parts = list(fields(body))
            name = script_name(parts)
            if name in SCRIPT_NAMES:
                sctx = [val for key, val in parts if key == b"SCTX"]
                if len(sctx) != 1:
                    raise ValueError(f"Missing or duplicate SCTX in {name}")
                source = sctx[0].decode("utf-8")
                # A script with a translated SCTX may still contain compiled SCDT;
                # OpenMW compiles SCTX at runtime, so preserve the other subrecords.
                def replace(match):
                    sound = match[2].lower()
                    if sound not in english or english[sound][0] != name:
                        raise ValueError(f"Unrecognized voice in {name}: {sound}")
                    current = match[3]
                    desired = translated[sound]
                    if current not in (english[sound][1], desired):
                        raise ValueError(f"Unexpected subtitle in {name}: {sound}")
                    changed.add(sound)
                    return match[1] + desired + match[4]
                replaced = SCRIPT_SAY.sub(replace, source)
                if replaced != source:
                    parts = [
                        (key, replaced.encode("utf-8") if key == b"SCTX" else val)
                        for key, val in parts
                    ]
                    body = pack_fields(parts)
                changed_scripts.add(name)
        output.append(pack_record(tag, body, unknown, flags))
    if changed != set(english) or changed_scripts != SCRIPT_NAMES:
        raise ValueError(
            f"Incomplete shrine scripts: voices={set(english) - changed}, "
            f"scripts={SCRIPT_NAMES - changed_scripts}"
        )
    updated = b"".join(output)
    list(records(updated))
    return updated, len(changed_scripts), len(changed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-mod", required=True, type=Path)
    parser.add_argument("--master", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output directory must not exist")
    source_file = args.source_mod / "Morrowind_Korean_ReTranslation.esp"
    original = source_file.read_bytes()
    master = extract_master_english(args.master)
    modified, script_count, subtitle_count = patch_esp(original, master)
    shutil.copytree(args.source_mod, args.output)
    (args.output / source_file.name).write_bytes(modified)
    report = {
        "source_sha256": hashlib.sha256(original).hexdigest(),
        "output_sha256": hashlib.sha256(modified).hexdigest(),
        "scripts": script_count,
        "spoken_subtitles": subtitle_count,
        "original_records_preserved": True,
        "scope": "Daedric shrine SCPT/SCTX Player->Say display subtitles",
    }
    (args.output / "daedric-quest-verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
