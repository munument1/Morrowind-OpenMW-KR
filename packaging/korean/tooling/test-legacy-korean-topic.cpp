#include <apps/openmw/mwdialogue/legacykoreantopic.hpp>

#include <iostream>

int main()
{
    using MWDialogue::decodeLegacyKoreanTopic;
    if (decodeLegacyKoreanTopic("\x12\xc2\xaa\x7f\x15\xc2\xaa\x7f\x17\xc2\xa1\x7f\x15\xc3\x96\xc3\xa1") != "네레바린")
        return 1;
    if (decodeLegacyKoreanTopic("\x12\xc2\xa2\x7f \x1c\xc3\x96\xc3\x9c\x1b\xc2\xa6\xc3\xaf") != "내 직업")
        return 2;
    if (decodeLegacyKoreanTopic("\x1b\xc3\x96\xc3\xa1\x10\xc3\x96\x7f \x1b\xc3\x96\xc3\xb3\x12\xc3\x89\xc3\xa1 \x16\xc2\xbf\xc3\xa6\x1b\xc2\xa3\xc3\x9c") != "인기 있는 물약")
        return 4;
    if (!decodeLegacyKoreanTopic("English topic").empty()
        || !decodeLegacyKoreanTopic("네레바린").empty()
        || !decodeLegacyKoreanTopic("\x12\xc2\xaa").empty()
        || !decodeLegacyKoreanTopic("\xc0\x92\xc2\xaa\x7f").empty()
        || !decodeLegacyKoreanTopic("\xff").empty()
        || !decodeLegacyKoreanTopic("\x12\xc2\xaa\xc3\xad").empty()
        || !decodeLegacyKoreanTopic("\x12\xc2\xa4\x7f").empty())
        return 3;
    std::cout << "PASS: legacy topic decoding and conservative rejection\n";
}
