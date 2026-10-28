#ifndef OPENMW_MWDIALOGUE_KOREANTOPICTAGS_H
#define OPENMW_MWDIALOGUE_KOREANTOPICTAGS_H

#include <string>
#include <string_view>

namespace MWDialogue
{
    inline std::string visibleKoreanTopicText(std::string_view text)
    {
        std::string result;
        std::size_t pos = 0;
        while (pos < text.size())
        {
            const auto begin = text.find('@', pos);
            const auto end = begin == std::string_view::npos ? std::string_view::npos : text.find('#', begin);
            if (end == std::string_view::npos)
            {
                result.append(text.substr(pos));
                break;
            }
            result.append(text.substr(pos, begin - pos));
            auto phrase = text.substr(begin + 1, end - begin - 1);
            const auto last = phrase.find_last_not_of('\x7f');
            if (last != std::string_view::npos)
                result.append(phrase.substr(0, last + 1));
            pos = end + 1;
        }
        return result;
    }

    // Use corrected content markup only when every visible byte still matches
    // the historical entry. Never replace wording, expanded player names, dates
    // or quest state from a saved game with current translation templates.
    inline std::string reconcileKoreanTopicMarkup(std::string_view saved, std::string_view current)
    {
        if (visibleKoreanTopicText(saved) == visibleKoreanTopicText(current))
            return std::string(current);
        return std::string(saved);
    }

    // Repair markup in the journal view, without rewriting historical save
    // strings, timestamps, actors or quest stages. Visible wording is retained.
    inline std::string repairLegacyKoreanTopicTags(std::string_view text)
    {
        std::string result(text);
        const auto replace = [&](std::string_view from, std::string_view to) {
            std::size_t pos = 0;
            while ((pos = result.find(from, pos)) != std::string::npos)
            {
                result.replace(pos, from.size(), to);
                pos += to.size();
            }
        };
        replace("@하지#-@에이#", "@하지-에이#");
        replace("하지-@에이#", "@하지-에이#");
        replace("훌륭한 @일#이었네", "훌륭한 일이었네");
        return result;
    }
}
#endif
