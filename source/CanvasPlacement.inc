// New toplevels wait for a canvas region; dialogs follow their parent.
PHLWINDOW CScrollOverview::canvasDialogParent(PHLWINDOW window) const {
    if (!window)
        return {};
    const auto parent = window->backend().parent();
    if (parent && (shouldShowOverviewWindow(parent) || g_canvasPendingWindows.contains(parent->metadata().stableID())))
        return parent;
    return {};
}

bool CScrollOverview::queueCanvasWindow(PHLWINDOW window) {
    if (!isCanvasDesktop() || !ScrollOverview::Config::getValue<bool>("plugin:spatialoverview:canvas:spawn_on_open") || !shouldShowOverviewWindow(window) || (window->m_state & Desktop::View::WINDOW_STATE_PINNED) ||
        canvasCompositorDndActive())
        return false;
    const auto parent = canvasDialogParent(window);
    if (!manageCanvasWindow(window, false) || !window->layoutTarget())
        return false;
    if (parent && parent->layoutTarget()) {
        if (g_canvasPendingWindows.contains(parent->metadata().stableID())) {
            g_canvasPendingWindows.insert(window->metadata().stableID());
            pendingDialogs.emplace_back(window, parent);
            return true;
        }
        placeCanvasDialog(window, parent);
        noteCanvasLayoutChanged();
        return true;
    }
    if (Fullscreen::controller()->isFullscreen(window))
        Fullscreen::controller()->setFullscreenMode(window, Fullscreen::FSMODE_NONE, Fullscreen::FSMODE_NONE);
    // A region deliberately drawn before launching also satisfies placement.
    if (!regionArmed && spawnRegion && applySpawnRegion(window))
        return true;
    g_canvasPendingWindows.insert(window->metadata().stableID());
    pendingRegions.push_back(window);
    stopCanvasMotion();
    if (pendingRegions.size() == 1)
        startNextPendingRegion();
    return true;
}

void CScrollOverview::placeCanvasDialog(PHLWINDOW window, PHLWINDOW parent) {
    if (!window || !window->layoutTarget() || !parent || !parent->layoutTarget())
        return;
    auto       box    = window->layoutTarget()->position();
    const auto centre = parent->layoutTarget()->position().middle();
    box.x             = centre.x - box.w * .5;
    box.y             = centre.y - box.h * .5;
    window->layoutTarget()->setPositionGlobal(box);
    window->layoutTarget()->warpPositionSize();
}

void CScrollOverview::revealPendingDialogs(PHLWINDOW parent) {
    std::vector<PHLWINDOW> children;
    for (const auto& [child, owner] : pendingDialogs)
        if (owner.lock() == parent)
            if (const auto window = child.lock())
                children.push_back(window);
    std::erase_if(pendingDialogs, [&](const auto& item) { return !item.first || item.second.lock() == parent; });
    for (const auto& window : children) {
        g_canvasPendingWindows.erase(window->metadata().stableID());
        if (!Desktop::View::validMapped(window))
            continue;
        placeCanvasDialog(window, parent);
        canvasAdoptFocus(window);
        Desktop::focusState()->fullWindowFocus(window, Desktop::FOCUS_REASON_DESKTOP_STATE_CHANGE);
        ensureCanvasKeyboardFocus(window);
        revealPendingDialogs(window);
    }
}

void CScrollOverview::startNextPendingRegion() {
    while (!pendingRegions.empty() && !Desktop::View::validMapped(pendingRegions.front().lock())) {
        if (const auto w = pendingRegions.front().lock())
            g_canvasPendingWindows.erase(w->metadata().stableID());
        pendingRegions.erase(pendingRegions.begin());
    }
    if (pendingRegions.empty()) {
        resetSpawnRegion();
        return;
    }
    if (!regionArmed)
        resetSpawnRegion();
    regionArmed    = true;
    regionDeadline = std::numeric_limits<double>::infinity();
    setCanvasCursor("crosshair");
    const auto w = pendingRegions.front().lock();
    HyprlandAPI::addNotification(SCROLLOVERVIEW_HANDLE, "Выделите область для окна: " + SpatialOverview::Navigator::displayTitle(w) + " · Esc: разместить автоматически",
                                 CHyprColor{.5F, .8F, 1.F, 1.F}, 3500);
    damage();
}

void CScrollOverview::finishPendingRegion(bool automatic) {
    if (pendingRegions.empty()) {
        resetSpawnRegion();
        return;
    }
    const auto w = pendingRegions.front().lock();
    pendingRegions.erase(pendingRegions.begin());
    if (w)
        g_canvasPendingWindows.erase(w->metadata().stableID());
    if (Desktop::View::validMapped(w) && w->layoutTarget()) {
        if (automatic) {
            resetSpawnRegion();
            g_canvasManagedTargets.erase(w->layoutTarget().get());
            manageCanvasWindow(w, true);
            followCanvasWindow(w, true);
        } else {
            applySpawnRegion(w);
            canvasAdoptFocus(w);
            Desktop::focusState()->fullWindowFocus(w, Desktop::FOCUS_REASON_DESKTOP_STATE_CHANGE);
        }
        ensureCanvasKeyboardFocus(w);
        revealPendingDialogs(w);
    }
    resetSpawnRegion();
    if (!pendingRegions.empty())
        startNextPendingRegion();
    rebuildPending = true;
    noteCanvasLayoutChanged();
    damage();
}

void CScrollOverview::cancelSpawnRegion() {
    if (!pendingRegions.empty())
        finishPendingRegion(true);
    else
        resetSpawnRegion();
}

void CScrollOverview::forgetPendingRegion(PHLWINDOW window) {
    if (!window)
        return;
    const bool first = !pendingRegions.empty() && pendingRegions.front().lock() == window;
    g_canvasPendingWindows.erase(window->metadata().stableID());
    std::erase_if(pendingRegions, [&](const auto& ref) { return !ref || ref.lock() == window; });
    std::erase_if(pendingDialogs, [&](const auto& item) { return !item.first || item.first.lock() == window; });
    revealPendingDialogs(window);
    if (first) {
        resetSpawnRegion();
        startNextPendingRegion();
    }
}

void CScrollOverview::clearPendingRegions() {
    for (const auto& ref : pendingRegions)
        if (const auto w = ref.lock())
            g_canvasPendingWindows.erase(w->metadata().stableID());
    pendingRegions.clear();
    for (const auto& [child, parent] : pendingDialogs)
        if (const auto w = child.lock())
            g_canvasPendingWindows.erase(w->metadata().stableID());
    pendingDialogs.clear();
    // No placement on shutdown: the native layout restoration owns geometry.
    regionArmed   = false;
    regionDrawing = false;
    spawnRegion.reset();
}
