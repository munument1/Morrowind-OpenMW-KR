"""Claude issue #42: reproduce missed Korean topic links with the real C++ parser.

These are conservative engine syntax fixtures, not in-game quest progression QA.
"""
from pathlib import Path
import sys
import tempfile

from verify_kr5_links import inspect

runner = Path(sys.argv[1]).resolve()
with tempfile.TemporaryDirectory(prefix="claude-issue42-") as temp:
    mod = Path(temp)
    topics = [
        "지명", "풀어주시겠", "동행하겠", "도망친 노예",
        "디바이스 피르의 아내", "아주라의 바보",
        "생명 없는 자", "모로윈드의 수호자",
        "강령술", "마법", "말", "일",
    ]
    sidecars = {
        "top": "".join(topic + "\t" + topic + "\n" for topic in topics),
        "mrk": "지명\t그대를 네레바린으로 지명하겠\n",
        "jrn": "",
        "cel": "",
    }
    for ext, content in sidecars.items():
        (mod / ("Morrowind_Korean_ReTranslation." + ext)).write_text(
            content, encoding="utf-8-sig"
        )

    cases = [
        ("nom1", "도망친 노예요."),
        ("nom2", "디바이스 피르의 아내지."),
        ("nom3", "아주라의 바보다."),
        ("nom4", "생명 없는 자여."),
        ("nom5", "모로윈드의 수호자로서."),
        ("verb1", "그대를 네레바린으로 지명하겠소."),
        ("verb2", "그대를 네레바린으로 지명하겠네."),
        ("verb3", "풀어주시겠다면 부탁드립니다."),
        ("verb4", "동행하겠습니다."),
        ("false1", "강령술사야. 대마법사가 왔다."),
        ("false2", "하지 말라는 부탁. 일요일에는 바쁘다."),
    ]
    expected = {
        "nom1": ["도망친 노예"],
        "nom2": ["디바이스 피르의 아내"],
        "nom3": ["아주라의 바보"],
        "nom4": ["생명 없는 자"],
        "nom5": ["모로윈드의 수호자"],
        "verb1": ["지명"],
        "verb2": ["지명"],
        "verb3": ["풀어주시겠"],
        "verb4": ["동행하겠"],
        "false1": [],
        "false2": [],
    }
    for discovery in [False, True]:
        result = inspect(runner, mod, cases, topics, True, discovery)
        for case, targets in expected.items():
            assert result[case]["targets"] == targets, (
                discovery, case, result[case], targets
            )
print("PASS: Claude #42 noun predicates, verbal 겠 suffixes, and protected false links")
