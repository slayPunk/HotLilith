#pragma once

#include <hyprland/src/desktop/view/window/Window.hpp>
#include <hyprland/src/desktop/view/window/WindowPresentation.hpp>
#include <hyprland/src/render/decorations/IHyprWindowDecoration.hpp>
// Hyprland exposes the rendered gradient on decorations rather than windows.
// Keep the version-specific access in this file.
#define private public
#include <hyprland/src/render/decorations/CHyprBorderDecoration.hpp>
#include <hyprland/src/render/decorations/CHyprDropShadowDecoration.hpp>
#include <hyprland/src/render/decorations/CHyprInnerGlowDecoration.hpp>
#undef private

namespace OverviewWindow {
inline CAnimatedDecorationGradient* decorationGradient(const PHLWINDOW& window, eDecorationType type) {
    const auto decoration = window->presentation().decoration(type);
    if (!decoration)
        return nullptr;
    switch (type) {
        case DECORATION_BORDER: return &static_cast<CHyprBorderDecoration*>(decoration.get())->m_gradient;
        case DECORATION_SHADOW: return &static_cast<CHyprDropShadowDecoration*>(decoration.get())->m_gradient;
        case DECORATION_INNER_GLOW: return &static_cast<CHyprInnerGlowDecoration*>(decoration.get())->m_gradient;
        default: return nullptr;
    }
}
inline CAnimatedDecorationGradient::SRenderState decorationState(const PHLWINDOW& window, eDecorationType type) {
    const auto gradient = decorationGradient(window, type);
    return gradient ? gradient->renderState() : CAnimatedDecorationGradient::SRenderState{};
}
inline bool decorationAnimating(const PHLWINDOW& window) {
    for (const auto type : {DECORATION_BORDER, DECORATION_SHADOW, DECORATION_INNER_GLOW}) {
        const auto gradient = decorationGradient(window, type);
        if (gradient && ((gradient->m_fadeProgress && gradient->m_fadeProgress->isBeingAnimated()) ||
                         (gradient->m_angleProgress && gradient->m_angleProgress->isBeingAnimated())))
            return true;
    }
    return false;
}
}
