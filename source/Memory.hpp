#pragma once

#include "globals.hpp"

#include <hyprland/src/desktop/DesktopTypes.hpp>
#include <hyprland/src/helpers/math/Math.hpp>

#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

// Where windows live on the canvas, remembered across restarts. Entries are
// keyed by app class and title; a closed window keeps its entry so it can
// come home when it is opened again.
namespace SpatialOverview::Memory {

    struct SWindowPlacement {
        PHLWINDOW window;
        CBox      box;
    };

    struct SCamera {
        Vector2D offset;
        float    zoom = 1.F;
    };

    // restoring: true while a fresh canvas is being populated (login, first
    // open). Then any window of a remembered app may take that app's most
    // recent free spot; afterwards an exact title match is required. Claims
    // are unique per live window within a scope, including same-title siblings.
    std::optional<CBox>    claim(const PHLWINDOW& window, bool restoring, const std::string& scope = "global");
    std::optional<SCamera> camera(const std::string& monitor, const std::string& scope = "global");
    void                   save(const std::vector<SWindowPlacement>& windows, const std::unordered_map<std::string, SCamera>& cameras, const std::string& scope = "global");
    std::string            path();
}
