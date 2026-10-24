// Hotlilit mechanics. Included by scrollOverview.cpp to share its canvas
// eligibility and native-layout guards, without exposing compositor internals.
double CScrollOverview::mechanicsTime() {
    return std::chrono::duration<double>(Time::steadyNow().time_since_epoch()).count();
}

void CScrollOverview::stopCanvasMotion() {
    const bool moving = panCoast.active || windowCoast.active;
    panCoast.stop();
    windowCoast.stop();
    coastingWindow.reset();
    if (moving) {
        noteCanvasLayoutChanged();
        damage();
    }
}

void CScrollOverview::beginMotionSample(bool pan) {
    stopCanvasMotion();
    magnetX.reset();
    magnetY.reset();
    auto& samples = pan ? panSamples : windowSamples;
    samples.clear();
    if (pan && viewOffset)
        samples.add(mechanicsTime(), {viewOffset->value().x, viewOffset->value().y});
}

void CScrollOverview::sampleWindowMotion() {
    if (!isCanvasDesktop() || !dragActiveWindow)
        return;
    const auto w = dragActiveWindow.lock();
    const auto i = dragWorkspaceIndex(w);
    if (i >= images.size())
        return;
    const auto pos = overviewPointToGlobal(i, lastMousePosLocal - dragGrabOffsetLocal);
    windowSamples.add(mechanicsTime(), {pos.x, pos.y});
}

void CScrollOverview::releaseWindowMotion(PHLWINDOW w) {
    if (!isCanvasDesktop() || !Desktop::View::validMapped(w) || !w->m_isFloating || !ScrollOverview::Config::getValue<bool>("plugin:spatialoverview:canvas:inertia_enabled"))
        return;
    auto v = windowSamples.release(mechanicsTime(), canvasZoom());
    if (magnetX)
        v.x = 0;
    if (magnetY)
        v.y = 0;
    coastingWindow = w;
    windowCoast.start(v, mechanicsTime());
    magnetX.reset();
    magnetY.reset();
    requestInputFrame();
}

CBox CScrollOverview::magnetWindowBox(const CBox& world, PHLWINDOW window, bool resize) const {
    if (!isCanvasDesktop() || !window || !ScrollOverview::Config::getValue<bool>("plugin:spatialoverview:canvas:magnet_enabled"))
        return world;
    const auto                  viewport = currentCanvasViewportWorld();
    std::vector<Hotlilit::Rect> neighbours;
    for (const auto& w : Desktop::windowState()->windows()) {
        if (w == window || !shouldShowOverviewWindow(w) || w->m_pinned || !w->layoutTarget() || !g_canvasNativeLayout.contains(w->m_stableID))
            continue;
        const auto b = w->layoutTarget()->position();
        neighbours.push_back({b.x, b.y, b.w, b.h});
    }
    const bool left = resize && (resizeCorner == Layout::CORNER_TOPLEFT || resizeCorner == Layout::CORNER_BOTTOMLEFT);
    const bool top  = resize && (resizeCorner == Layout::CORNER_TOPLEFT || resizeCorner == Layout::CORNER_TOPRIGHT);
    const auto result =
        Hotlilit::magnet({world.x, world.y, world.w, world.h}, neighbours, {viewport.x, viewport.y, viewport.w, viewport.h}, canvasZoom(),
                         ScrollOverview::Config::getValue<int>("plugin:spatialoverview:canvas:magnet_gap"),
                         ScrollOverview::Config::getValue<int>("plugin:spatialoverview:canvas:magnet_distance"), magnetX, magnetY, left, resize && !left, top, resize && !top);
    CBox box{result.box.x, result.box.y, result.box.w, result.box.h};
    if (resize && window->layoutTarget()) {
        auto       size   = box.size();
        const auto target = window->layoutTarget();
        const auto min    = target->minSize().value_or(Vector2D{1, 1});
        const auto max    = target->maxSize().value_or(Vector2D{16384, 16384});
        size.x            = std::clamp(size.x, std::max(1.0, min.x), max.x > 0 ? std::max(min.x, max.x) : 16384.0);
        size.y            = std::clamp(size.y, std::max(1.0, min.y), max.y > 0 ? std::max(min.y, max.y) : 16384.0);
        // An app's size constraints take priority over magnets.
        if (size != box.size()) {
            magnetX.reset();
            magnetY.reset();
            return world;
        }
    }
    magnetX = result.x;
    magnetY = result.y;
    return box;
}

CBox CScrollOverview::magnetLocalBox(const CBox& local, PHLWINDOW window, bool resize) const {
    const auto monitor = pMonitor.lock();
    if (!isCanvasDesktop() || !monitor)
        return local;
    auto screen = local;
    screen.scale(1.F / std::max(monitor->m_scale, .01F));
    screen.translate(monitor->m_position);
    const auto world = canvasScreenToWorld(screen);
    if (!world)
        return local;
    auto result = canvasWorldToScreen(magnetWindowBox(*world, window, resize));
    result.translate(-monitor->m_position);
    result.scale(monitor->m_scale);
    return result;
}

void CScrollOverview::advanceCanvasMotion() {
    if (!isCanvasDesktop() || closing) {
        stopCanvasMotion();
        return;
    }
    const double now = mechanicsTime();
    if (pendingRegions.empty() && (regionArmed || spawnRegion) && now > regionDeadline)
        cancelSpawnRegion();
    const bool wasMoving = panCoast.active || windowCoast.active;
    if (panCoast.active) {
        const auto d = panCoast.step(now, canvasZoom());
        viewOffset->setValueAndWarp(viewOffset->value() + Vector2D{d.x, d.y});
    }
    if (windowCoast.active) {
        const auto w = coastingWindow.lock();
        if (!shouldShowOverviewWindow(w) || !w->m_isFloating || !w->layoutTarget() || !g_canvasNativeLayout.contains(w->m_stableID) || Fullscreen::controller()->isFullscreen(w))
            windowCoast.stop();
        else {
            const auto d   = windowCoast.step(now, canvasZoom());
            auto       box = w->layoutTarget()->position();
            box.translate({d.x, d.y});
            box = magnetWindowBox(box, w);
            if (magnetX)
                windowCoast.velocity.x = 0;
            if (magnetY)
                windowCoast.velocity.y = 0;
            if (windowCoast.velocity.length() * canvasZoom() < 20)
                windowCoast.stop();
            box.x = std::clamp(box.x, -1e6, 1e6);
            box.y = std::clamp(box.y, -1e6, 1e6);
            w->layoutTarget()->damageEntire();
            w->layoutTarget()->setPositionGlobal(box);
            w->layoutTarget()->warpPositionSize();
            w->layoutTarget()->damageEntire();
        }
    }
    if (wasMoving) {
        markBlurDirty();
        requestInputFrame();
        damage();
        if (!panCoast.active && !windowCoast.active) {
            magnetX.reset();
            magnetY.reset();
            noteCanvasLayoutChanged();
        }
    }
}

void CScrollOverview::resetSpawnRegion() {
    if (!regionArmed && !spawnRegion)
        return;
    if (regionDrawing)
        navigatorSwallowedButtons.emplace(ScrollOverview::Config::getLeftHanded() ? BTN_RIGHT : BTN_LEFT);
    regionArmed   = false;
    regionDrawing = false;
    spawnRegion.reset();
    if (g_pointerGrabOverview == this)
        g_pointerGrabOverview = nullptr;
    setCanvasCursor(navigatorOwnsPointer() ? "left_ptr" : "");
    damage();
}

bool CScrollOverview::handleRegionButton(uint32_t button, uint32_t state) {
    if (!regionArmed)
        return false;
    const uint32_t main = ScrollOverview::Config::getLeftHanded() ? BTN_RIGHT : BTN_LEFT;
    if (button != main)
        return true; // Consume the complete gesture, including releases.
    if (state == WL_POINTER_BUTTON_STATE_PRESSED) {
        const auto monitor = pMonitor.lock();
        if (!monitor)
            return true;
        const auto world = canvasScreenToWorld(CBox{monitor->m_position + lastMousePosLocal / monitor->m_scale, {1, 1}});
        if (!world)
            return true;
        regionStart           = world->pos();
        regionDrawing         = true;
        spawnRegion           = CBox{regionStart, {1, 1}};
        g_pointerGrabOverview = this;
        g_pSeatManager->setPointerFocus(nullptr, {});
    } else if (regionDrawing) {
        updateSpawnRegion();
        regionDrawing = false;
        if (!spawnRegion || spawnRegion->w < 80 || spawnRegion->h < 60) {
            spawnRegion.reset(); // Keep armed so a misclick can be retried.
        } else {
            regionArmed    = false;
            regionDeadline = mechanicsTime() + 60;
            setCanvasCursor(navigatorOwnsPointer() ? "left_ptr" : "");
            if (!pendingRegions.empty())
                finishPendingRegion(false);
        }
    }
    damage();
    return true;
}

void CScrollOverview::updateSpawnRegion() {
    const auto monitor = pMonitor.lock();
    if (!regionDrawing || !monitor)
        return;
    const auto world = canvasScreenToWorld(CBox{monitor->m_position + lastMousePosLocal / monitor->m_scale, {1, 1}});
    if (!world)
        return;
    const auto p = world->pos();
    spawnRegion  = CBox{std::min(p.x, regionStart.x), std::min(p.y, regionStart.y), std::abs(p.x - regionStart.x), std::abs(p.y - regionStart.y)};
    damage();
}

bool CScrollOverview::applySpawnRegion(PHLWINDOW window) {
    if (regionArmed || !spawnRegion || mechanicsTime() > regionDeadline || !shouldShowOverviewWindow(window) || !g_canvasNativeLayout.contains(window->m_stableID) ||
        !window->layoutTarget())
        return false;
    auto       box    = *spawnRegion;
    const auto target = window->layoutTarget();
    const auto min    = target->minSize().value_or(Vector2D{1, 1});
    const auto max    = target->maxSize().value_or(Vector2D{16384, 16384});
    box.w             = std::clamp(box.w, std::max(1.0, min.x), max.x > 0 ? std::max(min.x, max.x) : 16384.0);
    box.h             = std::clamp(box.h, std::max(1.0, min.y), max.y > 0 ? std::max(min.y, max.y) : 16384.0);
    target->rememberFloatingSize(box.size());
    target->setPositionGlobal(box);
    target->warpPositionSize();
    target->damageEntire();
    resetSpawnRegion();
    noteCanvasLayoutChanged();
    return true;
}

void CScrollOverview::renderCanvasMechanics(PHLMONITOR monitor) {
    if (!monitor)
        return;
    auto local = [&](CBox world) {
        auto b = canvasWorldToScreen(world);
        b.translate(-monitor->m_position);
        b.scale(monitor->m_scale);
        return b;
    };
    const auto gradient = ScrollOverview::Config::getCanvasAccent();
    auto accent = gradient.m_colors.empty() ? Colors::WHITE : gradient.m_colors.front();
    if (spawnRegion) {
        const auto                  b = local(*spawnRegion);
        CRectPassElement::SRectData fill;
        fill.box   = b;
        fill.color = accent;
        fill.color.a *= .12F;
        g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(fill));
        CBorderPassElement::SBorderData border;
        border.box        = b;
        border.grad1      = gradient;
        border.borderSize = std::max(1, sc<int>(std::round(ScrollOverview::Config::getValue<int>("general:border_size") * monitor->m_scale)));
        g_pHyprRenderer->m_renderPass.add(makeUnique<CBorderPassElement>(border));
    }
    if (!ScrollOverview::Config::getValue<bool>("plugin:spatialoverview:canvas:magnet_guides") || (!dragActiveWindow && !resizeActiveWindow && !windowCoast.active))
        return;
    const auto viewport = currentCanvasViewportWorld();
    for (int axis = 0; axis < 2; ++axis) {
        const auto guide = axis == 0 ? magnetX : magnetY;
        if (!guide)
            continue;
        CRectPassElement::SRectData line;
        line.box   = local(axis == 0 ? CBox{*guide, viewport.y, 1.0 / canvasZoom(), viewport.h} : CBox{viewport.x, *guide, viewport.w, 1.0 / canvasZoom()});
        line.color = accent;
        g_pHyprRenderer->m_renderPass.add(makeUnique<CRectPassElement>(line));
    }
}

void CScrollOverview::renderDoubleBorder(PHLMONITOR monitor, PHLWINDOW window, const CBox& box, float zoom) {
    if (!isCanvasDesktop() || !monitor || !window || box.empty() || window->m_pinned || !ScrollOverview::Config::getValue<bool>("plugin:spatialoverview:canvas:double_border"))
        return;
    if (window->getRealBorderSize() <= 0 || !window->m_ruleApplicator->decorate().valueOrDefault())
        return;
    const auto gradient = window->m_realBorderColor;
    const int width = std::max(1, sc<int>(std::round(monitor->m_scale * zoom * window->getRealBorderSize())));
    const int rounding = std::max(0, sc<int>(std::round(window->rounding() * monitor->m_scale * zoom)));
    CBorderPassElement::SBorderData outer;
    outer.box = box;
    outer.box.expand(width);
    outer.grad1      = gradient;
    outer.borderSize = width;
    outer.round      = rounding > 0 ? rounding + width : 0;
    outer.outerRound = rounding > 0 ? rounding + 2 * width : 0;
    outer.roundingPower = window->roundingPower();
    outer.a          = .45F;
    outer.window     = window;
    g_pHyprRenderer->m_renderPass.add(makeUnique<CBorderPassElement>(outer));
    CBorderPassElement::SBorderData inner;
    inner.box        = box;
    inner.grad1      = gradient;
    inner.borderSize = width;
    inner.round      = rounding;
    inner.outerRound = rounding > 0 ? rounding + width : 0;
    inner.roundingPower = window->roundingPower();
    inner.window     = window;
    g_pHyprRenderer->m_renderPass.add(makeUnique<CBorderPassElement>(inner));
}

std::string CScrollOverview::mechanicsStateJson() const {
    return std::format("{{\"pan_inertia\":{},\"window_inertia\":{},\"region_armed\":{},\"pending_windows\":{},\"captured_pointer\":{},\"region\":{}}}", panCoast.active, windowCoast.active, regionArmed,
                       pendingRegions.size(), g_pInputManager->isConstrained() || bool(g_canvasManualCapture.lock()), spawnRegion ? std::format("[{:.1f},{:.1f},{:.1f},{:.1f}]", spawnRegion->x, spawnRegion->y, spawnRegion->w, spawnRegion->h) : "null");
}
