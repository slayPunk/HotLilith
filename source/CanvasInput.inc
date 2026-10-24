void canvasRememberPointerPosition(const Vector2D&);

// The native input path already sends relative motion before mouse.move.
// Keep those deltas in device units: zoom must not change game sensitivity.
// Only the cursor lock/confinement and absolute surface position are projected.
bool CScrollOverview::handleCanvasPointerConstraint() {
    if (!isCanvasDesktop() || closing || sessionLocked() || canvasCompositorDndActive() || regionArmed || dragPendingPrimary || dragActiveWindow || resizePointerDown ||
        resizeActiveWindow || scrollingPanPointerDown || spacePanHeld || (g_pInputManager->getModsFromAllKBs() & HL_MODIFIER_META))
        return false;
    const auto window = Desktop::focusState()->window();
    if (!shouldShowOverviewWindow(window) || window->m_pinned || !canvasDrawsWindow(window))
        return false;
    const auto surface    = Desktop::focusState()->surface();
    const auto owner      = Desktop::View::CWLSurface::fromResource(surface);
    if (!owner)
        return false;
    const auto constraint = owner ? owner->constraint() : nullptr;
    const bool manual     = g_canvasManualCapture.lock() == window;
    if ((!constraint || !constraint->isActive()) && !manual)
        return false;
    if (g_canvasCaptureBlocked.contains(window->m_stableID)) {
        if (constraint)
            constraint->deactivate();
        return false;
    }
    const auto native  = owner->getSurfaceBoxGlobal();
    const auto monitor = pMonitor.lock();
    if (!native || !monitor)
        return false;
    const auto drawn   = canvasWorldToScreen(*native);
    const auto visible = drawn.intersection(monitor->logicalBox());
    if (visible.empty())
        return false;
    Vector2D   position = g_pInputManager->getMouseCoordsInternal();
    const bool locked   = manual || constraint->isLocked();
    if (locked) {
        if (!manual && constraint->m_hintSet) {
            const auto hint = constraint->logicPositionHint();
            position        = canvasWorldToScreen(CBox{hint, {1, 1}}).pos();
        } else
            position = drawn.middle();
        position = visible.closestPoint(position);
    } else {
        auto region = constraint->logicConstraintRegion();
        region.translate(-native->pos()).scale(canvasZoom()).translate(drawn.pos());
        region.intersect(visible.x, visible.y, visible.w, visible.h);
        if (region.empty())
            return false;
        position = region.closestPoint(position);
    }
    const auto  local    = (position - drawn.pos()) / std::max(.01F, canvasZoom()) * window->m_X11SurfaceScaledBy;
    static bool handling = false;
    if (handling)
        return true;
    handling   = true;
    auto reset = Hyprutils::Utils::CScopeGuard([] { handling = false; });
    g_pSeatManager->setPointerFocus(surface, local);
    Pointer::pointerController()->warpTo(position, true);
    // mouseMoveUnified skips equal floored positions before its event. Its
    // native bookkeeping is bypassed when this handler cancels that event.
    // Keep it in sync so a large delta reaching (0,0) cannot skip the lock.
    canvasRememberPointerPosition(position);
    if (!locked)
        g_pSeatManager->sendPointerMotion(Time::millis(Time::steadyNow()), local);
    g_pSeatManager->sendPointerFrame();
    canvasForwardedPointerWindow  = window;
    canvasForwardedPointerSurface = surface;
    lastMousePosLocal             = (position - monitor->m_position) * monitor->m_scale;
    requestInputFrame();
    return true;
}

bool CScrollOverview::suppressCanvasRelativeMotion() const {
    if (!isCanvasDesktop() || closing)
        return false;
    return regionArmed || dragPendingPrimary || dragActiveWindow || resizePointerDown || resizeActiveWindow || scrollingPanPointerDown || spacePanHeld ||
        (g_pInputManager->getModsFromAllKBs() & HL_MODIFIER_META);
}

bool canvasSuppressRelativeMotion() {
    if (sessionLocked())
        return false;
    for (const auto& overview : scrollOverviews()) {
        const auto* canvas = canvasOf(overview);
        if (canvas && canvas->suppressCanvasRelativeMotion())
            return true;
    }
    const auto focused = g_pSeatManager->m_state.pointerFocus.lock();
    const auto surface = Desktop::View::CWLSurface::fromResource(focused);
    const auto window  = surface ? Desktop::View::CWindow::fromView(surface->view()) : nullptr;
    return window && g_canvasCaptureBlocked.contains(window->m_stableID);
}

bool canvasReleasePointerCapture() {
    bool released = false;
    if (const auto window = g_canvasManualCapture.lock()) {
        g_canvasCaptureBlocked.insert(window->m_stableID);
        released = true;
    }
    g_canvasManualCapture.reset();
    for (const auto& ref : g_pInputManager->m_constraints) {
        const auto c      = ref.lock();
        const auto owner  = c ? c->owner() : nullptr;
        const auto window = owner ? Desktop::View::CWindow::fromView(owner->view()) : nullptr;
        if (!c || !window || (!g_canvasNativeLayout.contains(window->m_stableID) && !canvasFullscreenWindow(window)))
            continue;
        g_canvasCaptureBlocked.insert(window->m_stableID);
        // deactivate() may remove a one-shot from m_constraints: deferred below.
        released = true;
    }
    const auto constraints = g_pInputManager->m_constraints;
    for (const auto& ref : constraints) {
        const auto c      = ref.lock();
        const auto owner  = c ? c->owner() : nullptr;
        const auto window = owner ? Desktop::View::CWindow::fromView(owner->view()) : nullptr;
        if (c && window && g_canvasCaptureBlocked.contains(window->m_stableID))
            c->deactivate();
    }
    if (released) {
        g_canvasCursorShape = "left_ptr";
        Pointer::Cursor::overrideController->setOverride("left_ptr", Pointer::Cursor::CURSOR_OVERRIDE_SPECIAL_ACTION);
        g_pSeatManager->setPointerFocus(nullptr, {});
    }
    return released;
}

bool canvasCapturePointer() {
    const auto window = Desktop::focusState()->window();
    if (!window)
        return false;
    if (g_canvasManualCapture.lock() == window)
        return canvasReleasePointerCapture();
    for (const auto& overview : scrollOverviews()) {
        const auto* canvas = canvasOf(overview);
        if (!canvas || !canvas->canvasDrawsWindow(window))
            continue;
        g_canvasManualCapture = window;
        g_canvasCaptureBlocked.erase(window->m_stableID);
        Pointer::Cursor::overrideController->unsetOverride(Pointer::Cursor::CURSOR_OVERRIDE_SPECIAL_ACTION);
        g_canvasCursorShape.clear();
        return true;
    }
    return false;
}
