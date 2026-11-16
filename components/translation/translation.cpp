#include "translation.hpp"

#include <fstream>
#include <algorithm>

#include <components/misc/pathhelpers.hpp>
#include <components/misc/strings/lower.hpp>

namespace Translation
{
    Storage::Storage()
        : mEncoder(nullptr)
    {
    }

    void Storage::loadTranslationData(const Files::Collections& dataFileCollections, std::string_view esmFileName)
    {
        std::string_view esmNameNoExtension = Misc::stemFile(esmFileName);

        loadData(mCellNamesTranslations, esmNameNoExtension, "cel", dataFileCollections);
        loadData(mPhraseForms, esmNameNoExtension, "top", dataFileCollections);
        loadData(mKeywords, esmNameNoExtension, "mrk", dataFileCollections);
        loadData(mJournalKeywords, esmNameNoExtension, "jrn", dataFileCollections);
        loadData(mTopicDisplayNames, esmNameNoExtension, "dsp", dataFileCollections);
    }

    void Storage::loadData(ContainerType& container, std::string_view fileNameNoExtension, std::string_view extension,
        const Files::Collections& dataFileCollections)
    {
        std::string fileName(fileNameNoExtension);
        fileName += '.';
        fileName += extension;

        const Files::MultiDirCollection& collection = dataFileCollections.getCollection(extension);
        if (collection.doesExist(fileName))
        {
            std::ifstream stream(collection.getPath(fileName), std::ios::binary);

            if (!stream.is_open())
                throw std::runtime_error("failed to open translation file: " + fileName);

            loadDataFromStream(container, stream);
        }
    }

    void Storage::loadDataFromStream(ContainerType& container, std::istream& stream)
    {
        std::string line;
        bool firstLine = true;
        bool utf8BomMode = false;
        while (!stream.eof() && !stream.fail())
        {
            std::getline(stream, line);
            if (!line.empty() && *line.rbegin() == '\r')
                line.resize(line.size() - 1);

            if (firstLine)
            {
                firstLine = false;
                if (line.compare(0, 3, "\xEF\xBB\xBF") == 0)
                {
                    utf8BomMode = true;
                    line.erase(0, 3);
                }
            }

            if (!line.empty())
            {
                const std::string_view utf8 = utf8BomMode ? std::string_view(line) : mEncoder->getUtf8(line);

                size_t tabPos = utf8.find('\t');
                if (tabPos != std::string::npos && tabPos > 0 && tabPos < utf8.size() - 1)
                {
                    const std::string_view key = utf8.substr(0, tabPos);
                    const std::string_view value = utf8.substr(tabPos + 1);

                    if (!key.empty() && !value.empty())
                        container.emplace(key, value);
                }
            }
        }
    }

    std::string_view Storage::translateCellName(std::string_view cellName) const
    {
        auto entry = mCellNamesTranslations.find(cellName);

        if (entry == mCellNamesTranslations.end())
            return cellName;

        return entry->second;
    }

    std::string_view Storage::topicStandardForm(std::string_view phrase) const
    {
        auto phraseFormsIterator = mPhraseForms.find(phrase);

        if (phraseFormsIterator != mPhraseForms.end())
            return phraseFormsIterator->second;
        else
            return phrase;
    }

    std::string_view Storage::topicKeyword(std::string_view phrase) const
    {
        auto entry = mKeywords.find(phrase);

        if (entry == mKeywords.end())
            return phrase;

        return entry->second;
    }

    std::string_view Storage::topicDisplayName(std::string_view topicId) const
    {
        const auto entry = mTopicDisplayNames.find(topicId);
        if (entry != mTopicDisplayNames.end())
            return entry->second;

        return topicKeyword(topicId);
    }

    std::vector<std::string_view> Storage::topicKeywordAliases(std::string_view topicId) const
    {
        std::vector<std::string_view> result;
        for (const auto& [source, keyword] : mKeywords)
        {
            const std::string sourceId = Misc::StringUtils::lowerCase(source);
            if (canonicalTopicId(sourceId) == topicId)
            {
                if (sourceId != topicId)
                    result.emplace_back(keyword);
                if (std::none_of(source.begin(), source.end(), [](unsigned char c) { return c >= 0x80; })
                    && std::any_of(keyword.begin(), keyword.end(), [](unsigned char c) { return c >= 0x80; }))
                    result.emplace_back(source);
            }
        }
        return result;
    }

    std::string_view Storage::canonicalTopicId(std::string_view topicId) const
    {
        const auto nonAscii = [](unsigned char c) { return c >= 0x80; };
        if (std::any_of(topicId.begin(), topicId.end(), nonAscii))
            return topicId;
        const auto found = mPhraseForms.find(Misc::StringUtils::lowerCase(topicId));
        if (found == mPhraseForms.end())
            return topicId;
        const std::string_view target = found->second;
        // TOP phrase forms also contain Korean homonyms and inflections. They
        // must not reinterpret an already canonical Korean dialogue ID.
        return std::any_of(target.begin(), target.end(), nonAscii) ? target : topicId;
    }

    void Storage::addPhraseForm(std::string_view phrase, std::string_view topicId)
    {
        mPhraseForms.emplace(phrase, topicId);
    }

    std::vector<std::string_view> Storage::journalKeywords(std::string_view topicId) const
    {
        std::vector<std::string_view> result;
        for (const auto& [phrase, target] : mJournalKeywords)
        {
            if (target == topicId)
                result.emplace_back(phrase);
        }
        return result;
    }

    void Storage::setEncoder(ToUTF8::Utf8Encoder* encoder)
    {
        mEncoder = encoder;
    }
}
