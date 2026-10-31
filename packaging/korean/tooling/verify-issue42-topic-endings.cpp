// Native smoke tests for issue #42, using OpenMW's real KeywordSearch parser.
#include <apps/openmw/mwdialogue/keywordsearch.hpp>
#include <components/translation/translation.hpp>
#include <iostream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

static void expectHits(MWDialogue::KeywordSearch& search, const Translation::Storage& storage,
    const std::string& source, const std::vector<std::string_view>& expected, bool discovery = false)
{
    const auto matches = search.parseHyperText(source, storage, discovery);
    if (matches.size() != expected.size())
        throw std::runtime_error("Issue #42 match-count mismatch in: " + source);
    for (std::size_t i = 0; i < matches.size(); ++i)
    {
        if (matches[i].mTopicId != expected[i] || matches[i].mExplicit)
            throw std::runtime_error("Issue #42 topic target mismatch in: " + source);
    }
}

int main()
{
    try
    {
        Translation::Storage storage;
        MWDialogue::KeywordSearch nouns;
        nouns.seed("도망친 노예", "escaped slave");
        nouns.seed("디바이스 피르의 아내", "wives");
        nouns.seed("아주라의 바보", "fool");
        nouns.seed("생명 없는 자", "lifeless");
        nouns.seed("모로윈드의 수호자", "defender");
        nouns.seed("에노 로마리", "eno");
        expectHits(nouns, storage,
            "도망친 노예요. 디바이스 피르의 아내지. 아주라의 바보다. "
            "생명 없는 자여. 모로윈드의 수호자로서. 에노 로마리라 하오.",
            { "escaped slave", "wives", "fool", "lifeless", "defender", "eno" });
        expectHits(nouns, storage, "도망친 노예요. 생명 없는 자여.",
            { "escaped slave", "lifeless" }, true);

        MWDialogue::KeywordSearch verbs;
        verbs.seed("그대를 네레바린으로 지명하겠", "nomination");
        verbs.seed("풀어주시겠", "freedom");
        verbs.seed("동행하겠", "company");
        verbs.seed("지혜가 나를 이끈다", "wisdom");
        verbs.seed("마법", "magic");
        verbs.seed("말", "speech");
        verbs.seed("행", "journey");
        verbs.seed("발견", "found");
        expectHits(verbs, storage,
            "그대를 네레바린으로 지명하겠소. 그대를 네레바린으로 지명하겠네. "
            "풀어주시겠다면. 동행하겠습니다. 지혜가 나를 이끈다면.",
            { "nomination", "nomination", "freedom", "company", "wisdom" });
        expectHits(verbs, storage,
            "풀어주시겠다고? 풀어주시겠어요? 동행하겠다.",
            { "freedom", "freedom", "company" });
        expectHits(verbs, storage,
            "마법사다. 발견했다. 말라. 행여. 지혜가 나를 이끈다면야.", {});
        std::cout << "PASS: issue #42 noun/verb topic suffixes, discovery and false-positive guards\n";
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }
    return 0;
}
