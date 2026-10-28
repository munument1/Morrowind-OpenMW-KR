// Read-only adapter for checking saved IDs with the actual runtime decoder.
#include <apps/openmw/mwdialogue/legacykoreantopic.hpp>
#include <iostream>
#include <string>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

int main()
{
#ifdef _WIN32
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
#endif
    std::string line;
    while (std::getline(std::cin, line))
    {
        if (!line.empty() && line.back() == '\r')
            line.pop_back();
        std::cout << MWDialogue::decodeLegacyKoreanTopic(line) << '\n';
    }
}
