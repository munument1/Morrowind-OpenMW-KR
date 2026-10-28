#include <apps/openmw/mwdialogue/koreantopictags.hpp>
#include <iostream>
int main()
{
    using namespace MWDialogue;
    if (reconcileKoreanTopicMarkup("@가입 전에# 말했다.", "가입 전에 말했다.") != "가입 전에 말했다.")
        return 1;
    if (reconcileKoreanTopicMarkup("@옛 문장#이다.", "새 문장이다.") != "@옛 문장#이다.")
        return 2;
    if (reconcileKoreanTopicMarkup("주인공이 말했다.", "%PCName이 말했다.") != "주인공이 말했다.")
        return 3;
    const auto name = repairLegacyKoreanTopicTags("@하지#-@에이#의 행방.");
    if (name != "@하지-에이#의 행방." || visibleKoreanTopicText(name) != "하지-에이의 행방.")
        return 4;
    if (visibleKoreanTopicText("그대로인 문장 @아직 끝나지 않은 태그") != "그대로인 문장 @아직 끝나지 않은 태그")
        return 5;
    if (visibleKoreanTopicText("@광산\x7f#을 찾았다.") != "광산을 찾았다.")
        return 6;
    std::cout << "PASS: markup-only historical view repair, unchanged wording, player-name protection and legacy name tags\n";
}
