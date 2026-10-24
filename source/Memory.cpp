#define WLR_USE_UNSTABLE
#include "Memory.hpp"
#include "Navigator.hpp"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>
#include <hyprland/src/desktop/state/WindowState.hpp>
#include <hyprland/src/desktop/view/Window.hpp>

namespace SpatialOverview::Memory {
    namespace {
        struct Entry {
            std::string scope, klass, title;
            CBox        box;
            int64_t     seen   = 0;
            uint64_t    window = 0;
        };
        struct CameraEntry {
            std::string scope, monitor;
            SCamera     camera;
        };
        bool                     loaded = false;
        std::vector<Entry>       entries;
        std::vector<CameraEntry> cameras;
        constexpr size_t         MAX_ENTRIES = 512, MAX_CAMERAS = 128;

        bool                     sane(double n, double limit) {
            return std::isfinite(n) && std::abs(n) <= limit;
        }
        bool saneBox(const CBox& b) {
            return sane(b.x, 1e6) && sane(b.y, 1e6) && sane(b.w, 16384) && sane(b.h, 16384) && b.w >= 1 && b.h >= 1;
        }
        bool saneCamera(const SCamera& c) {
            return sane(c.offset.x, 1e6) && sane(c.offset.y, 1e6) && sane(c.zoom, 10) && c.zoom >= .01;
        }
        std::string clean(std::string s) {
            for (auto& c : s)
                if (c == '\t' || c == '\n' || c == '\r')
                    c = ' ';
            if (s.size() > 2048)
                s.resize(2048);
            return s;
        }
        void load() {
            if (loaded)
                return;
            loaded = true;
            std::error_code ec;
            const auto      size = std::filesystem::file_size(path(), ec);
            if (ec || size > 2 * 1024 * 1024)
                return;
            std::ifstream in(path());
            std::string   line;
            if (!std::getline(in, line) || line != "# hotlilit canvas memory v2")
                return;
            size_t lines = 0;
            while (std::getline(in, line) && ++lines <= MAX_ENTRIES + MAX_CAMERAS + 32) {
                if (line.size() > 8192)
                    continue;
                std::istringstream row(line);
                std::string        kind;
                row >> kind;
                if (kind == "window" && entries.size() < MAX_ENTRIES) {
                    Entry e;
                    if (row >> std::quoted(e.scope) >> std::quoted(e.klass) >> std::quoted(e.title) >> e.box.x >> e.box.y >> e.box.w >> e.box.h >> e.seen)
                        if (!e.scope.empty() && !e.klass.empty() && saneBox(e.box))
                            entries.push_back(std::move(e));
                } else if (kind == "camera" && cameras.size() < MAX_CAMERAS) {
                    CameraEntry e;
                    if (row >> std::quoted(e.scope) >> std::quoted(e.monitor) >> e.camera.offset.x >> e.camera.offset.y >> e.camera.zoom)
                        if (!e.scope.empty() && !e.monitor.empty() && saneCamera(e.camera))
                            cameras.push_back(std::move(e));
                }
            }
        }
        void write() {
            std::error_code ec;
            const auto      dest = std::filesystem::path(path());
            std::filesystem::create_directories(dest.parent_path(), ec);
            if (ec)
                return;
            const auto    temp = path() + ".next-" + std::to_string(getpid());
            std::ofstream out(temp, std::ios::trunc);
            if (!out)
                return;
            chmod(temp.c_str(), 0600);
            out << "# hotlilit canvas memory v2\n" << std::setprecision(12);
            for (const auto& c : cameras)
                out << "camera " << std::quoted(c.scope) << ' ' << std::quoted(c.monitor) << ' ' << c.camera.offset.x << ' ' << c.camera.offset.y << ' ' << c.camera.zoom << '\n';
            for (const auto& e : entries)
                out << "window " << std::quoted(e.scope) << ' ' << std::quoted(e.klass) << ' ' << std::quoted(e.title) << ' ' << e.box.x << ' ' << e.box.y << ' ' << e.box.w << ' '
                    << e.box.h << ' ' << e.seen << '\n';
            out.close();
            if (out)
                std::filesystem::rename(temp, dest, ec);
            if (!out || ec)
                std::filesystem::remove(temp, ec);
        }
    }

    std::string path() {
        std::filesystem::path base;
        if (const char* state = std::getenv("XDG_STATE_HOME"); state && *state)
            base = state;
        else
            base = std::filesystem::path(std::getenv("HOME") ? std::getenv("HOME") : "/tmp") / ".local/state";
        return (base / "hotlilit/canvas-memory-v2.txt").string();
    }

    std::optional<CBox> claim(const PHLWINDOW& window, bool restoring, const std::string& scope) {
        if (!window)
            return {};
        load();
        const auto klass = clean(window->m_class.empty() ? window->m_initialClass : window->m_class);
        const auto title = clean(Navigator::displayTitle(window));
        if (klass.empty())
            return {};
        const auto& live = Desktop::windowState()->windows();
        Entry*      best = nullptr;
        for (auto& e : entries) {
            if (e.scope != scope || e.klass != klass)
                continue;
            if (e.window == window->m_stableID)
                return e.box;
            if (e.window && std::ranges::none_of(live, [&](const auto& w) { return w && w->m_isMapped && w->m_stableID == e.window; }))
                e.window = 0;
            if (e.window)
                continue;
            if (e.title == title && (!best || best->title != title || e.seen > best->seen))
                best = &e;
            else if (restoring && (!best || (best->title != title && e.seen > best->seen)))
                best = &e;
        }
        if (!best || (!restoring && best->title != title))
            return {};
        best->window = window->m_stableID;
        return best->box;
    }

    std::optional<SCamera> camera(const std::string& monitor, const std::string& scope) {
        load();
        for (const auto& e : cameras)
            if (e.scope == scope && e.monitor == monitor)
                return e.camera;
        return {};
    }

    void save(const std::vector<SWindowPlacement>& windows, const std::unordered_map<std::string, SCamera>& views, const std::string& scope) {
        load();
        const int64_t now = std::time(nullptr);
        for (const auto& p : windows) {
            if (!p.window || !saneBox(p.box))
                continue;
            const auto klass = clean(p.window->m_class.empty() ? p.window->m_initialClass : p.window->m_class);
            const auto title = clean(Navigator::displayTitle(p.window));
            if (klass.empty())
                continue;
            auto it = std::ranges::find_if(entries, [&](const Entry& e) { return e.scope == scope && e.window == p.window->m_stableID; });
            if (it == entries.end()) {
                // A previously closed window can reclaim an exact home. Do not
                // merge two simultaneous windows with the same class/title.
                it = std::ranges::find_if(entries, [&](const Entry& e) { return e.scope == scope && !e.window && e.klass == klass && e.title == title && e.box == p.box; });
            }
            Entry e{scope, klass, title, p.box, now, p.window->m_stableID};
            if (it == entries.end())
                entries.push_back(std::move(e));
            else
                *it = std::move(e);
        }
        std::ranges::stable_sort(entries, [](const Entry& a, const Entry& b) { return a.seen > b.seen; });
        if (entries.size() > MAX_ENTRIES)
            entries.resize(MAX_ENTRIES);
        for (const auto& [monitor, view] : views) {
            if (!saneCamera(view))
                continue;
            auto it = std::ranges::find_if(cameras, [&](const CameraEntry& e) { return e.scope == scope && e.monitor == monitor; });
            if (it != cameras.end())
                it->camera = view;
            else if (cameras.size() < MAX_CAMERAS)
                cameras.push_back({scope, monitor, view});
        }
        write();
    }
}
