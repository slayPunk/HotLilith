#include "CanvasPhysics.hpp"
#include <cassert>
#include <iostream>
using namespace Hotlilit;
bool near(double a, double b, double e = .001) {
    return std::abs(a - b) < e;
}
int main() {
    MotionSamples s;
    assert(s.release(1, 1).length() == 0);
    s.add(1, {0, 0});
    s.add(1.04, {40, 0});
    s.add(1.08, {80, 0});
    assert(near(s.release(1.08, 1).x, 600));
    assert(s.release(1.3, 1).length() == 0);
    s.clear();
    s.add(1, {0, 0});
    s.add(1.05, {1, 0});
    assert(s.release(1.05, 1).length() == 0);
    s.clear();
    s.add(1, {0, 0});
    s.add(1.05, {10000, 0});
    assert(near(s.release(1.05, .5).x, 4800));
    Coast a, b;
    a.start({600, 200}, 1);
    b.start({600, 200}, 1);
    Point pa, pb;
    for (int i = 1; i <= 60; ++i)
        pa = pa + a.step(1 + i / 60., 1);
    for (int i = 1; i <= 144; ++i)
        pb = pb + b.step(1 + i / 144., 1);
    assert(near(pa.x, pb.x) && near(pa.y, pb.y)); // Frame-rate independent travel.
    a.start({600, 0}, 1);
    assert(a.step(3, 1).length() == 0 && !a.active);
    a.start({600, 0}, 1);
    a.stop();
    assert(a.step(1.01, 1).length() == 0);
    Rect              viewport{-1000, -1000, 4000, 4000};
    std::vector<Rect> neighbours{{400, 100, 200, 200}};
    auto              r = magnet({187, 100, 200, 200}, neighbours, viewport, 1, 12, 12);
    assert(near(r.box.x, 188) && r.x && near(*r.x, 388));
    r = magnet({170, 100, 200, 200}, neighbours, viewport, 1, 12, 12);
    assert(!r.x);
    r = magnet({170, 100, 200, 200}, neighbours, viewport, .5, 12, 12);
    assert(near(r.box.x, 188));
    r = magnet({187, 800, 200, 200}, neighbours, viewport, 1, 12, 12);
    assert(!r.x); // No distant attraction.
    r = magnet({170, 100, 200, 200}, neighbours, viewport, 1, 12, 12, 388);
    assert(near(r.box.x, 188)); // Hysteresis.
    r = magnet({160, 100, 200, 200}, neighbours, viewport, 1, 12, 12, 388);
    assert(!r.x);
    r = magnet({100, 100, 287, 200}, neighbours, viewport, 1, 12, 12, {}, {}, false, true, false, true);
    assert(near(r.box.x, 100) && near(r.box.w, 288));
    r = magnet({613, 100, 200, 200}, neighbours, viewport, 1, 12, 12, {}, {}, true, false, true, false);
    assert(near(r.box.x, 612) && near(r.box.w, 201));
    r = magnet({-994, 200, 200, 200}, {}, viewport, 1, 12, 12);
    assert(near(r.box.x, -1000));
    // A latched edge is not replaced by a later, closer candidate.
    r = magnet({170, 100, 200, 200}, {{400, 100, 200, 200}, {385, 100, 200, 200}}, viewport, 1, 12, 12, 388);
    assert(near(r.box.x, 188));
    std::cout << "PASS 18 physics invariants\n";
}
