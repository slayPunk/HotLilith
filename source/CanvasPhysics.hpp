#pragma once

// Canvas mechanics in world coordinates. Thresholds are expressed in screen
// pixels so a zoomed-out desktop has the same grip and release behaviour.
#include <algorithm>
#include <cmath>
#include <deque>
#include <optional>
#include <vector>

namespace Hotlilit {
    struct Point {
        double x = 0, y = 0;
        Point  operator+(Point p) const {
            return {x + p.x, y + p.y};
        }
        Point operator-(Point p) const {
            return {x - p.x, y - p.y};
        }
        Point operator*(double s) const {
            return {x * s, y * s};
        }
        double length() const {
            return std::hypot(x, y);
        }
    };
    struct Rect {
        double x, y, w, h;
    };

    class MotionSamples {
        struct Sample {
            double time;
            Point  position;
        };
        std::deque<Sample> samples;

      public:
        void clear() {
            samples.clear();
        }
        void add(double time, Point p) {
            if (!std::isfinite(time) || !std::isfinite(p.x) || !std::isfinite(p.y))
                return;
            if (!samples.empty() && time <= samples.back().time)
                return;
            samples.push_back({time, p});
            while (samples.size() > 2 && time - samples.front().time > .10)
                samples.pop_front();
            while (samples.size() > 32)
                samples.pop_front();
        }
        Point release(double now, double zoom, double gain = .6) const {
            if (samples.size() < 2 || now - samples.back().time > .10)
                return {};
            const auto&  first = samples.front();
            const auto&  last  = samples.back();
            const double dt    = last.time - first.time;
            if (dt < .008 || dt > .20)
                return {};
            auto v             = (last.position - first.position) * (1.0 / dt);
            zoom               = std::clamp(zoom, .01, 10.0);
            const double speed = v.length() * zoom;
            if (speed < 150)
                return {};
            v = v * gain;
            if (v.length() * zoom > 2400)
                v = v * (2400 / (v.length() * zoom));
            return v;
        }
    };

    struct Coast {
        Point  velocity;
        double lastTime = 0;
        bool   active   = false;
        void   stop() {
            active   = false;
            velocity = {};
        }
        void start(Point v, double now) {
            velocity = v;
            lastTime = now;
            active   = v.length() > 0;
        }
        Point step(double now, double zoom, double tau = .4) {
            if (!active)
                return {};
            const double dt = now - lastTime;
            lastTime        = now;
            // Suspend/resume or a stalled compositor must not fling a window away.
            if (dt <= 0 || dt > .25 || !std::isfinite(dt)) {
                stop();
                return {};
            }
            tau                = std::clamp(tau, .05, 2.0);
            const double decay = std::exp(-dt / tau);
            const auto   delta = velocity * (tau * (1 - decay));
            velocity           = velocity * decay;
            if (velocity.length() * zoom < 20)
                stop();
            return delta;
        }
    };

    struct MagnetResult {
        Rect                  box;
        std::optional<double> x, y; // guide coordinate in world space
    };

    // Match adjacent or aligned edges only when rectangles overlap on the other
    // axis. Distant windows cannot pull a window across empty canvas. Existing
    // locks get a wider release threshold, preventing jitter at the boundary.
    inline MagnetResult magnet(Rect moving, const std::vector<Rect>& neighbours, Rect viewport, double zoom, double gap, double radius, std::optional<double> lockX = {},
                               std::optional<double> lockY = {}, bool resizeLeft = false, bool resizeRight = false, bool resizeTop = false, bool resizeBottom = false) {
        const bool            resizing  = resizeLeft || resizeRight || resizeTop || resizeBottom;
        const double          threshold = radius / std::clamp(zoom, .01, 10.0);
        double                dx = threshold + 1, dy = threshold + 1;
        std::optional<double> gx, gy;
        bool                  heldX = false, heldY = false;
        auto                  considerX = [&](double candidate, double edge) {
            const double d    = candidate - edge;
            const bool   held = lockX && std::abs(candidate - *lockX) < .01;
            if (std::abs(d) <= threshold * (held ? 1.6 : 1.0) && ((held && !heldX) || (held == heldX && std::abs(d) < std::abs(dx)))) {
                dx    = d;
                gx    = candidate;
                heldX = held;
            }
        };
        auto considerY = [&](double candidate, double edge) {
            const double d    = candidate - edge;
            const bool   held = lockY && std::abs(candidate - *lockY) < .01;
            if (std::abs(d) <= threshold * (held ? 1.6 : 1.0) && ((held && !heldY) || (held == heldY && std::abs(d) < std::abs(dy)))) {
                dy    = d;
                gy    = candidate;
                heldY = held;
            }
        };
        const double left = moving.x, right = left + moving.w, top = moving.y, bottom = top + moving.h;
        for (const auto& r : neighbours) {
            if (bottom >= r.y - threshold && top <= r.y + r.h + threshold) {
                if (!resizing || resizeLeft) {
                    considerX(r.x + r.w + gap, left);
                    considerX(r.x, left);
                }
                if (!resizing || resizeRight) {
                    considerX(r.x - gap, right);
                    considerX(r.x + r.w, right);
                }
            }
            if (right >= r.x - threshold && left <= r.x + r.w + threshold) {
                if (!resizing || resizeTop) {
                    considerY(r.y + r.h + gap, top);
                    considerY(r.y, top);
                }
                if (!resizing || resizeBottom) {
                    considerY(r.y - gap, bottom);
                    considerY(r.y + r.h, bottom);
                }
            }
        }
        if (!resizing || resizeLeft)
            considerX(viewport.x, left);
        if (!resizing || resizeRight)
            considerX(viewport.x + viewport.w, right);
        if (!resizing || resizeTop)
            considerY(viewport.y, top);
        if (!resizing || resizeBottom)
            considerY(viewport.y + viewport.h, bottom);
        if (gx) {
            if (!resizing)
                moving.x += dx;
            else if (resizeLeft) {
                moving.x += dx;
                moving.w -= dx;
            } else
                moving.w += dx;
        }
        if (gy) {
            if (!resizing)
                moving.y += dy;
            else if (resizeTop) {
                moving.y += dy;
                moving.h -= dy;
            } else
                moving.h += dy;
        }
        return {moving, gx, gy};
    }
}
