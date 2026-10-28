#ifndef OPENMW_MWGUI_MESSAGELIFETIME_H
#define OPENMW_MWGUI_MESSAGELIFETIME_H
#include <cstdint>
namespace MWGui
{
    inline bool messageBoxExpired(float elapsed, float timeout, std::uint64_t speechId, std::uint64_t activeSpeechId)
    {
        return speechId != 0 ? speechId != activeSpeechId : elapsed >= timeout;
    }
}
#endif
