# Contributing to HotLilith

HotLilith 0.2 currently targets Hyprland 0.56.2, Lua configuration and dwindle, without a desktop-preset dependency. Keep the generic module free of user-specific bindings and imports. Discuss broader compositor-version support before relying on newer private APIs.

## Repository layout

- `source/`: vendored Phantomat renderer with local changes, upstream license, reference documentation and auxiliary tools.
- `config/canvas.lua`: generic settings and workspace lifecycle, with no key bindings.
- `config/bindings.example.lua`: separately selected example bindings, never included by the installer.
- `build.sh`, `install.py`, `preview.py`: supported HotLilith entry points.
- `tests/`: HotLilith integration, build and installer tests.
- `patches/`: pinned upstream DnD patch and the complete local renderer diff.
- `docs/`: user documentation and validation notes.
- `work/` and `outputs/`: ignored local scratch space and evidence, respectively.

The scripts and default bindings under `source/scripts/` are upstream references. They deploy a different preset; use the root-level installer for HotLilith.

## Checks without a compositor

On Linux with Python 3, a C++ compiler, Make, pkg-config and binutils:

```bash
python3 tools/check-repository.py
python3 -m unittest discover -s tests -p 'test_*.py'
make -C source test-physics test-dnd-route
git diff --check
```

The installer tests use temporary configs. The build tests simulate ABI probes but compile and load a real tiny C++ library. The C++ models do not depend on Hyprland headers. GitHub Actions runs this subset; it does not establish compatibility with a live compositor.

## Full integration checks

Use a running Wayland/Hyprland 0.56.2 session with matching development headers and the dependencies in the README. Additional tools: `foot`, `grim`, `wayland-scanner`, Wayland client/xkbcommon development files, PyGObject + GTK4, and SDL2 development files for the relative-input client. XWayland must be available for X11 checks. The appearance checks additionally require Pillow and inspect actual screenshots and camera motion across a live theme reload.

```bash
bash build.sh
bash tests/build-tools.sh
export NESTED_BACKEND=headless
python3 tests/standalone.py
python3 tests/appearance.py
python3 tests/integration.py
python3 tests/regressions.py
python3 tests/mechanics.py
python3 tests/placement.py
python3 tests/relative_input.py wayland
python3 tests/relative_input.py x11
python3 tests/dnd.py
```

The harness bootstraps a child compositor through the current Wayland session, then creates a fixed virtual output. It uses the child's IPC/Wayland sockets and temporary state files. It still needs a parent Wayland session. Captured logs/screenshots go under ignored `work/`. A missing SDL2 client is not a passed game-input test.

Before changing input or fullscreen code, exercise both native Wayland and XWayland, including a real game when possible. Document the exact Proton/backend/capture mode and distinguish observed gameplay from protocol-client tests. See [validation.md](docs/validation.md).

## Keep the renderer patch reproducible

The baseline is Phantomat at `a1e8a0806541640d01503ac861a8a39548de8724` with the two PR #19 commits represented by `patches/upstream-pr19-dnd.patch`:

```bash
mkdir -p work
git clone --no-checkout https://github.com/kaolti/phantomat.git work/upstream-with-pr19
git -C work/upstream-with-pr19 checkout --detach a1e8a0806541640d01503ac861a8a39548de8724
git -C work/upstream-with-pr19 apply ../../patches/upstream-pr19-dnd.patch
python3 tools/refresh-renderer-patch.py --check
```

After changing `source/`, regenerate with `python3 tools/refresh-renderer-patch.py`, then run `--check`. Do not apply the complete local patch on top of the already patched `source/` tree. Keep the baseline and build outputs outside the publication set.

## Pull requests and reports

Explain the trigger, expected behaviour, resulting change and relevant checks. Report the exact Hyprland version, desktop preset, output count/scales, reproduction steps and whether the issue also occurs in tiling. Remove private window titles and unrelated personal configuration from attached logs.

Preserve upstream attribution and protocol copyright notices. HotLilith changes use the root BSD-3-Clause license. No commit-author email is prescribed by the project; configure your own local Git identity.
