"""Compile the production hook lifecycle with fault-injecting hook doubles."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HookLifecycleTests(unittest.TestCase):
    def test_activation_rollback_and_repeated_shutdown(self):
        source = (ROOT/'source/main.cpp').read_text()
        lifecycle = source[source.index('static auto overviewHooks()'):source.index('\nstatic void hkScheduleFrame')]
        registry = lifecycle[:lifecycle.index('bool ensureScrollOverviewHooks()')]
        names = re.findall(r'\bg_p\w*Hook\w*\b', registry)
        self.assertEqual(len(names), 14)
        self.assertEqual(len(set(names)), 14)
        self.assertNotIn('g_pX11ClientMessageHook', names)
        declarations = '\n'.join('CFunctionHook* '+name+' = nullptr;' for name in names)
        assignments = '\n'.join(f'{name} = &storage[{i}];' for i, name in enumerate(names))
        null_cases = '\n'.join(f'case {i}: {name} = nullptr; break;' for i, name in enumerate(names))
        fixture = r'''
#include <array>
#include <cassert>
#include <string>
#include <vector>
std::vector<int> attempts, removals;
int notifications = 0;
struct CFunctionHook {
    int id = 0;
    bool fail = false, active = false;
    bool hook() { attempts.push_back(id); active = !fail; return active; }
    bool unhook() { removals.push_back(id); active = false; return true; }
};
bool g_scrollOverviewHooksActive = false;
void disableScrollOverviewHooks();
void failNotif(const std::string&) { ++notifications; }
''' + declarations + '\n' + lifecycle + r'''
int main() {
    std::array<CFunctionHook, 14> storage;
    auto reset = [&] {
        attempts.clear(); removals.clear(); notifications = 0;
        g_scrollOverviewHooksActive = false;
        for (int i = 0; i < 14; ++i) storage[i] = CFunctionHook{.id=i};
        ''' + assignments + r'''
    };
    // Every possible failure stops activation and rolls back in reverse order.
    for (int failure = 0; failure < 14; ++failure) {
        reset();
        storage[failure].fail = true;
        assert(!ensureScrollOverviewHooks());
        assert(!g_scrollOverviewHooksActive && notifications == 1);
        assert(attempts.size() == failure+1 && removals.size() == 14);
        for (int i = 0; i <= failure; ++i) assert(attempts[i] == i);
        for (int i = 0; i < 14; ++i) {
            assert(removals[i] == 13-i);
            assert(!storage[i].active);
        }
    }
    // Missing pointers fail cleanly and are skipped during rollback.
    for (int missing = 0; missing < 14; ++missing) {
        reset();
        switch (missing) { ''' + null_cases + r''' }
        assert(!ensureScrollOverviewHooks());
        assert(!g_scrollOverviewHooksActive && notifications == 1);
        assert(attempts.size() == missing && removals.size() == 13);
        for (const auto& hook : storage) assert(!hook.active);
    }
    reset();
    assert(ensureScrollOverviewHooks() && g_scrollOverviewHooksActive);
    for (const auto& hook : storage) assert(hook.active);
    attempts.clear();
    assert(ensureScrollOverviewHooks() && attempts.empty());
    disableScrollOverviewHooks();
    assert(!g_scrollOverviewHooksActive);
    for (int i = 0; i < 14; ++i) assert(removals[i] == 13-i);
    removals.clear();
    disableScrollOverviewHooks();
    assert(removals.size() == 14 && !g_scrollOverviewHooksActive);
    for (const auto& hook : storage) assert(!hook.active);
}
'''
        with tempfile.TemporaryDirectory(prefix='hotlilith-hooks-') as directory:
            cpp = Path(directory)/'hooks.cpp'
            binary = Path(directory)/'hooks'
            cpp.write_text(fixture)
            subprocess.run(['c++', '-std=c++23', '-Wall', '-Wextra', str(cpp), '-o', str(binary)], check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=10)
