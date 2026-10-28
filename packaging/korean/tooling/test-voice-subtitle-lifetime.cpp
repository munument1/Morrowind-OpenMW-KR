#include <apps/openmw/mwgui/messagelifetime.hpp>
#include <cmath>
#include <iostream>

int main()
{
    using MWGui::messageBoxExpired;
    // Real CharGenName2.mp3 duration; the released Korean text has 42 characters.
    constexpr double clipSeconds = 7.810625;
    constexpr float textTimeout = 4.2f;
    for (const int fps : { 30, 60, 120 })
    {
        double firstExpiry = 0;
        for (int frame = 0; frame < fps * 12; ++frame)
        {
            const double elapsed = double(frame) / fps;
            const auto activeId = elapsed < clipSeconds ? 17u : 0u;
            if (messageBoxExpired(float(elapsed), textTimeout, 17, activeId))
            {
                firstExpiry = elapsed;
                break;
            }
        }
        if (firstExpiry < clipSeconds || firstExpiry > clipSeconds + 1.0 / fps)
            return 1;
    }
    if (messageBoxExpired(60.f, textTimeout, 17, 17)) // paused/queued speech remains active
        return 2;
    if (!messageBoxExpired(2.f, textTimeout, 17, 0)) // stopped or missing stream
        return 3;
    if (!messageBoxExpired(2.f, textTimeout, 17, 18)) // replacement is a different utterance
        return 4;
    if (messageBoxExpired(4.f, textTimeout, 0, 17) || !messageBoxExpired(4.3f, textTimeout, 0, 17))
        return 5; // ordinary notifications retain their timer despite unrelated speech
    if (messageBoxExpired(0.f, textTimeout, 0, 0) || !messageBoxExpired(4.3f, textTimeout, 0, 0))
        return 6; // absent/missing/disabled audio has a finite text-based fallback
    std::cout << "PASS: real-clip lifetime at 30/60/120 fps, pause/queue, stop/replacement, notification isolation and no-audio fallback\n";
}
