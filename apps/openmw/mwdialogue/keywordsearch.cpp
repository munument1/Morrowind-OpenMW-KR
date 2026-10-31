#include "keywordsearch.hpp"

#include <algorithm>
#include <iterator>
#include <stdexcept>

#include <components/misc/strings/algorithm.hpp>
#include <components/misc/strings/lower.hpp>
#include <components/translation/translation.hpp>

namespace
{
    std::string_view removePseudoAsterisks(std::string_view phrase)
    {
        std::size_t lastNonAsteriskPos = phrase.find_last_not_of('\x7F');
        if (lastNonAsteriskPos == std::string_view::npos)
            return {};
        return phrase.substr(0, lastNonAsteriskPos + 1);
    }

    // Korean Hangul syllables occupy three bytes in UTF-8.
    bool isHangulSyllable(std::string_view text)
    {
        if (text.size() < 3)
            return false;
        const auto a = static_cast<unsigned char>(text[0]);
        const auto b = static_cast<unsigned char>(text[1]);
        const auto c = static_cast<unsigned char>(text[2]);
        if ((a & 0xf0) != 0xe0 || (b & 0xc0) != 0x80 || (c & 0xc0) != 0x80)
            return false;
        const char32_t codepoint = ((a & 0x0f) << 12) | ((b & 0x3f) << 6) | (c & 0x3f);
        return codepoint >= 0xac00 && codepoint <= 0xd7a3;
    }

    // Permit Korean inflections without turning arbitrary word prefixes into hyperlinks.
    // Ambiguous inflections can still be linked explicitly with @...#.
    bool isKoreanParticle(std::string_view ending)
    {
        constexpr std::string_view endings[] = {
            "은", "는", "이", "가", "을", "를", "의", "에", "에서", "에게", "께", "께서", "께서는",
            "한테", "한테서", "로", "으로", "와", "과", "랑", "이랑", "하고", "도", "만",
            "라는", "이라는", "란", "이란",
            "까지", "부터", "조차", "마저", "처럼", "같이", "보다", "밖에", "라도",
            "이라도", "나", "이나", "든", "이든", "든지", "이든지", "라고", "이라고",
            "이라", "이라면", "에서부터", "에게서", "에는", "에서는", "에게는",
            "에게도", "으로는", "로는", "들의", "들은", "들을", "들이", "들과", "들"
        };
        return std::find(std::begin(endings), std::end(endings), ending) != std::end(endings);
    }

    bool hasKoreanDisplayBoundary(std::string_view keyword, std::string_view before, std::string_view after)
    {
        if (!isHangulSyllable(keyword))
            return true;

        // The Korean work topic shares its spelling with the generic noun
        // meaning "thing/event". Spelling boundaries cannot disambiguate it.
        // Keep explicit @일# links and the unambiguous keyword "일거리".
        if (keyword == "일")
            return false;

        // "싫은" must not match "은", nor may a compound name like
        // "하지-에이" link its second half to the independent topic "에이".
        if (before.size() >= 3 && isHangulSyllable(before.substr(before.size() - 3)))
            return false;
        constexpr std::string_view joiners[] = { "-", "·", "‐", "‑", "–", "—" };
        for (std::string_view joiner : joiners)
        {
            if (before.size() >= joiner.size() + 3 && before.ends_with(joiner)
                && isHangulSyllable(before.substr(before.size() - joiner.size() - 3, 3)))
                return false;
        }

        // Only a trailing Hangul syllable needs Korean suffix handling.
        if (!isHangulSyllable(keyword.substr(keyword.size() - 3)))
            return true;

        std::size_t suffixBytes = 0;
        while (suffixBytes + 3 <= after.size() && isHangulSyllable(after.substr(suffixBytes, 3)))
            suffixBytes += 3;

        if (suffixBytes == 0)
        {
            // Keep prefixes from being linked inside hyphenated Korean compounds.
            for (std::string_view joiner : joiners)
            {
                if (after.starts_with(joiner) && after.size() >= joiner.size() + 3
                    && isHangulSyllable(after.substr(joiner.size(), 3)))
                    return false;
            }
            return true;
        }

        const std::string_view suffix = after.substr(0, suffixBytes);
        // "빛나" is a verb, not the independent topic "빛" + a particle.
        // For one-syllable topics, bare "나" is especially ambiguous.
        if (keyword.size() == 3 && suffix == "나")
            return false;

        // Common attached particles and noun-predicate endings.
        constexpr std::string_view extendedSuffixes[] = {
            "에서만", "에서부터", "으로부터", "에게만", "에만", "에도",
            "이라고", "이라서", "이다", "입니다", "이었다", "이었던",
            "이었지만", "이지만", "였고", "였다", "였습니다",
            "이군", "이군요", "이오", "이요", "이네", "이네요", "이지",
            "이지요", "이죠", "이야", "이랍니다", "이라네", "이라오",
            "인가", "입니까", "입죠", "일세", "이더군", "이더군요",
            "이었소", "이었네", "이었지", "이었어", "이었습니다"
        };
        const auto isEnding = [&](std::string_view ending) {
            return isKoreanParticle(ending)
                || std::find(std::begin(extendedSuffixes), std::end(extendedSuffixes), ending)
                    != std::end(extendedSuffixes);
        };
        // Short topic nouns such as "말" also occur inside the verb "말라는"
        // ("do not..."); avoid introducing false links for one-syllable topics.
        if (keyword.size() == 3
            && (suffix == "라는" || suffix == "이라는" || suffix == "란" || suffix == "이란"))
            return false;
        if (isEnding(suffix))
            return true;

        // Common Korean predicate/relationship endings, but only for longer noun
        // topics: the single-syllable "말" inside "말인" is too ambiguous.
        constexpr std::string_view contextualNounEndings[] = {
            "와의", "과의", "인", "이자", "임을", "였어", "야"
        };
        if (keyword.size() >= 6
            && std::find(std::begin(contextualNounEndings), std::end(contextualNounEndings), suffix)
                != std::end(contextualNounEndings))
            return true;

        // Plural nouns take case particles too: "블레이드 교관들에", "길드원들에게".
        // Keep the longest noun topic rather than falling back to a short prefix.
        return suffix.starts_with("들") && suffix.size() > std::string_view("들").size()
            && isEnding(suffix.substr(std::string_view("들").size()));
    }
}

namespace MWDialogue
{
    void KeywordSearch::seed(std::string_view keyword, std::string_view value)
    {
        if (keyword.empty())
            return;
        buildTrie(keyword, value, 0, mRoot);
    }

    void KeywordSearch::clear()
    {
        mRoot.mChildren.clear();
        mRoot.mKeyword.clear();
    }

    void KeywordSearch::highlightKeywords(Point beg, Point end, std::vector<Match>& out, bool overlaps) const
    {
        std::vector<Match> matches;
        for (Point i = beg; i != end; ++i)
        {
            if (i != beg)
            {
                Point prev = i;
                --prev;
                constexpr std::string_view wordSeparators = "\n\r \t'\"([";
                if (wordSeparators.find(*prev) == std::string_view::npos
                    && static_cast<unsigned char>(*i) < 0xe0) // allow starts of 3/4-byte UTF-8 chars (CJK/Hangul)
                    continue;
            }

            const Entry* current = &mRoot;
            for (Point it = i; it != end; ++it)
            {
                auto found = current->mChildren.find(Misc::StringUtils::toLower(*it));
                if (found == current->mChildren.end())
                    break;
                current = &found->second;
                if (!current->mKeyword.empty())
                {
                    std::string_view remainingText(it + 1, end);
                    std::string_view remainingKeyword = std::string_view(current->mKeyword).substr(it + 1 - i);
                    if (Misc::StringUtils::ciStartsWith(remainingText, remainingKeyword)
                        && hasKoreanDisplayBoundary(current->mKeyword, std::string_view(beg, i),
                            std::string_view(i + current->mKeyword.size(), end)))
                        matches.emplace_back(i, i + current->mKeyword.size(), current->mTopicId);
                }
            }
        }
        if (overlaps)
        {
            out.insert(out.end(), matches.begin(), matches.end());
            return;
        }
        // resolve overlapping keywords
        while (!matches.empty())
        {
            std::size_t longestKeywordSize = 0;
            auto longestKeyword = matches.begin();
            for (auto it = matches.begin(); it != matches.end(); ++it)
            {
                std::size_t size = it->mEnd - it->mBeg;
                if (size > longestKeywordSize)
                {
                    longestKeywordSize = size;
                    longestKeyword = it;
                }

                auto next = it + 1;

                if (next == matches.end())
                    break;

                if (it->mEnd <= next->mBeg)
                {
                    break; // no overlap
                }
            }

            Match keyword = *longestKeyword;
            matches.erase(longestKeyword);
            out.push_back(keyword);
            // erase anything that overlaps with the keyword we just added to the output
            std::erase_if(
                matches, [&](const Match& match) { return match.mBeg < keyword.mEnd && match.mEnd > keyword.mBeg; });
        }

        std::sort(out.begin(), out.end(), [](const Match& left, const Match& right) { return left.mBeg < right.mBeg; });
    }

    void KeywordSearch::buildTrie(std::string_view keyword, std::string_view topicId, size_t depth, Entry& entry)
    {
        const char ch = Misc::StringUtils::toLower(keyword[depth]);
        const auto found = entry.mChildren.find(ch);

        if (found == entry.mChildren.end())
        {
            entry.mChildren[ch].mTopicId = topicId;
            entry.mChildren[ch].mKeyword = keyword;
        }
        else
        {
            if (!found->second.mKeyword.empty())
            {
                std::string_view existingKeyword = found->second.mKeyword;
                if (Misc::StringUtils::ciEqual(keyword, existingKeyword))
                    return;
                if (depth >= existingKeyword.size())
                    throw std::runtime_error("unexpected trie depth");
                // Turn this Entry into a branch and append a leaf to hold its current ID
                if (depth + 1 < existingKeyword.size())
                {
                    buildTrie(existingKeyword, found->second.mTopicId, depth + 1, found->second);
                    found->second.mKeyword.clear();
                }
            }
            if (depth + 1 == keyword.size())
            {
                found->second.mTopicId = topicId;
                found->second.mKeyword = keyword;
            }
            else
            {
                buildTrie(keyword, topicId, depth + 1, found->second);
            }
        }
    }

    std::vector<KeywordSearch::Match> KeywordSearch::parseHyperText(
        const std::string& text, const Translation::Storage& storage, bool overlaps) const
    {
        std::vector<Match> matches;
        size_t posEnd = std::string::npos;
        size_t iterationPos = 0;

        for (;;)
        {
            const size_t posBegin = text.find('@', iterationPos);
            if (posBegin != std::string::npos)
                posEnd = text.find('#', posBegin);

            if (posBegin != std::string::npos && posEnd != std::string::npos)
            {
                if (posBegin != iterationPos)
                    highlightKeywords(text.begin() + iterationPos, text.begin() + posBegin, matches, overlaps);

                Match token;
                token.mExplicit = true;

                // This covers the entire link including the tags
                token.mBeg = text.begin() + posBegin;
                token.mEnd = text.begin() + posEnd + 1;

                const std::string_view id(token.mBeg + 1, token.mEnd - 1);
                token.mTopicId = removePseudoAsterisks(id);
                token.mTopicId.append(id.size() - token.mTopicId.size(), '*');
                token.mTopicId = Misc::StringUtils::lowerCase(storage.topicStandardForm(token.mTopicId));

                // Old translation data marked verbs such as "작동" as the work
                // topic, and even marked the last syllable of "만일"/"소행일".
                // Strip their visible markup but do not make them clickable.
                if (token.mTopicId == "일"
                    && ((id != "일" && id != "일거리")
                        || (posBegin >= 3 && isHangulSyllable(std::string_view(text).substr(posBegin - 3, 3)))))
                    token.mTopicId.clear();

                if (!token.mTopicId.empty() || !overlaps)
                    matches.push_back(std::move(token));

                iterationPos = posEnd + 1;
            }
            else
            {
                if (iterationPos < text.size())
                    highlightKeywords(text.begin() + iterationPos, text.end(), matches, overlaps);
                break;
            }
        }

        return matches;
    }

    std::string_view KeywordSearch::Match::getDisplayName() const
    {
        if (mExplicit)
            return removePseudoAsterisks(std::string_view(mBeg + 1, mEnd - 1));
        return std::string_view(mBeg, mEnd);
    }
}
