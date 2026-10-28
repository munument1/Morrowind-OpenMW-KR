// Regression runner using the actual OpenMW keyword parser and Translation::Storage.
#include <apps/openmw/mwdialogue/keywordsearch.hpp>
#include <apps/openmw/mwdialogue/koreantopictags.hpp>
#include <components/translation/translation.hpp>
#include <components/misc/strings/algorithm.hpp>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <set>
#include <stdexcept>

uint32_t count(std::istream& in)
{
    uint32_t n=0;
    if(!in.read(reinterpret_cast<char*>(&n),4)) throw std::runtime_error("Truncated count");
    return n;
}
std::string read(std::istream& in)
{
    auto n=count(in);
    if(n>16*1024*1024) throw std::runtime_error("Oversized string");
    std::string s(n,'\0');
    if(!in.read(s.data(),n)) throw std::runtime_error("Truncated text");
    return s;
}
void write(std::ostream& out,const std::string& s)
{
    uint32_t n=static_cast<uint32_t>(s.size());
    out.write(reinterpret_cast<const char*>(&n),4);out.write(s.data(),n);
}
int main(int argc,char** argv)
{
    if(argc!=5 && argc!=6) return 2;
    std::ifstream in(argv[1],std::ios::binary);
    std::ofstream out(argv[2],std::ios::binary);
    MWDialogue::KeywordSearch parser;
    Translation::Storage storage;
    ToUTF8::Utf8Encoder encoder(ToUTF8::WINDOWS_1252);
    storage.setEncoder(&encoder);
    storage.loadTranslationData(Files::Collections({std::filesystem::path(argv[3])}),"Morrowind_Korean_ReTranslation.esp");
    const bool patched = std::string_view(argv[4])=="patched";
    std::set<std::string> known;
    auto n=count(in);
    while(n--)
    {
        auto topic=read(in);
        // Consume the protocol's reference value, but use the actual loader result:
        // first-wins duplicate handling and BOM/line endings must match the engine.
        read(in);
        auto keyword=storage.topicKeyword(topic);
        auto id=Misc::StringUtils::lowerCase(topic);
        known.insert(id);parser.seed(keyword,id);
        if(patched)
        {
            parser.seed(topic,id);
            for(auto alias:storage.journalKeywords(topic)) parser.seed(alias,id);
        }
    }
    n=count(in);
    while(n--) {auto alias=read(in);auto topic=read(in);storage.addPhraseForm(alias,topic);}
    n=count(in);out.write(reinterpret_cast<const char*>(&n),4);
    while(n--)
    {
        const auto source=read(in);
        const bool discovery=argc==6 && std::string_view(argv[5])=="discovery";
        const auto text=patched && !discovery ? MWDialogue::repairLegacyKoreanTopicTags(source) : source;
        auto matches=parser.parseHyperText(text,storage,discovery);
        std::string displayed;
        auto pos=text.begin();
        uint32_t links=0;
        std::vector<std::string> targets;
        for(const auto& m:matches)
        {
            if(!discovery) {displayed.append(pos,m.mBeg);displayed.append(m.getDisplayName());pos=m.mEnd;}
            if(known.count(m.mTopicId)) { ++links;targets.push_back(m.mTopicId); }
        }
        if(discovery) displayed=text;
        else displayed.append(pos,text.end());
        out.write(reinterpret_cast<const char*>(&links),4);write(out,displayed);
        for(const auto& target:targets) write(out,target);
    }
    return out ? 0 : 3;
}
