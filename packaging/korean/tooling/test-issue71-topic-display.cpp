// Exercise the real sidecar loader: display aliases cannot change search IDs.
#include <components/files/collections.hpp>
#include <components/toutf8/toutf8.hpp>
#include <components/translation/translation.hpp>
#include <apps/openmw/mwgui/journalindex.hpp>

#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <string_view>

namespace
{
    void write(const std::filesystem::path& path, std::string_view contents)
    {
        std::ofstream output(path, std::ios::binary);
        output << "\xef\xbb\xbf" << contents;
        if (!output)
            throw std::runtime_error("Could not write temporary sidecar");
    }

    void require(bool condition, const char* message)
    {
        if (!condition)
            throw std::runtime_error(message);
    }
}

int main(int argc, char** argv)
{
    if (argc != 2)
        return 2;

    const std::filesystem::path folder(argv[1]);
    std::filesystem::create_directories(folder);
    write(folder / "TR_Mainland.mrk", "Necrom\t네크롬\n");
    write(folder / "TR_Mainland.dsp", "retribution\t응징\nlocal area\t주변 지역\n");

    ToUTF8::Utf8Encoder encoder(ToUTF8::WINDOWS_1252);
    Translation::Storage storage;
    storage.setEncoder(&encoder);
    storage.loadTranslationData(Files::Collections({folder}), "TR_Mainland.esm");

    require(storage.topicKeyword("Necrom") == "네크롬", "MRK search mapping missing");
    require(storage.topicDisplayName("Necrom") == "네크롬", "MRK display fallback missing");
    require(storage.topicKeyword("retribution") == "retribution", "DSP changed search behavior");
    require(storage.topicDisplayName("retribution") == "응징", "DSP display mapping missing");
    require(storage.topicDisplayName("local area") == "주변 지역", "Second DSP mapping missing");
    require(storage.canonicalTopicId("retribution") == "retribution", "DSP changed canonical topic ID");
    require(storage.topicDisplayName("unknown topic") == "unknown topic", "Unknown topic fallback missing");

    // Journal headings and the Korean topic index must use the *display* caption
    // while preserving the original ID for click and savegame lookup.
    Utf8Stream koreanTitle(storage.topicDisplayName("Necrom"));
    require(MWGui::journalIndexMatches(koreanTitle.peek(), 0x3134),
        "Translated Necrom should appear under Korean initial NIEUN");
    require(!MWGui::journalIndexMatches(koreanTitle.peek(), '*'),
        "Translated Necrom must not be grouped under English A-Z");
    Utf8Stream dspTitle(storage.topicDisplayName("retribution"));
    require(MWGui::journalIndexMatches(dspTitle.peek(), 0x3147),
        "DSP-only retribution should appear under Korean initial IEUNG");
    Utf8Stream englishTitle(storage.topicDisplayName("unknown topic"));
    require(MWGui::journalIndexMatches(englishTitle.peek(), '*'),
        "Untranslated topic should remain selectable in the Latin index");
}
