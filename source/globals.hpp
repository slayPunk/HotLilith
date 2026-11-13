#pragma once

#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/desktop/DesktopTypes.hpp>

inline HANDLE SCROLLOVERVIEW_HANDLE = nullptr;

bool ensureScrollOverviewHooks();
void disableScrollOverviewHooks();

// Syspunk: mode lifecycle is independent of overview/navigation zoom.
bool syspunkCanvasActive();
bool syspunkCanvasCompatible(PHLWORKSPACE workspace, bool workspaceOnly);
bool syspunkCanvasWorkspaceOnly();
int64_t syspunkCanvasWorkspaceID();
std::string syspunkCanvasWorkspaceAddress();
void syspunkCanvasPrepare(PHLWORKSPACE workspace, bool workspaceOnly);
void syspunkCanvasStop();
bool canvasSuppressRelativeMotion();
bool canvasReleasePointerCapture();
