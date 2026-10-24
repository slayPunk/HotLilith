#!/usr/bin/env python3
"""Copy a matching build; --enable connects it to Hyprland, --remove disconnects it."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
BEGIN, END = '-- BEGIN HOTLILITH\n', '-- END HOTLILITH\n'
LEGACY_BEGIN, LEGACY_END = '-- BEGIN SYSPUNK CANVAS\n', '-- END SYSPUNK CANVAS\n'


def disconnect(text):
    blocks = []
    for begin, end in [(BEGIN, END), (LEGACY_BEGIN, LEGACY_END)]:
        if text.count(begin) != text.count(end) or text.count(begin) > 1:
            raise ValueError('Malformed HotLilith markers; config was not changed.')
        if begin in text:
            start, finish = text.index(begin), text.index(end)
            if finish < start:
                raise ValueError('Reversed HotLilith markers; config was not changed.')
            blocks.append((start, finish + len(end)))
    if len(blocks) > 1:
        raise ValueError('Multiple HotLilith connection blocks; config was not changed.')
    if not blocks:
        return text
    start, finish = blocks[0]
    return text[:start] + text[finish:]


def close_canvas():
    plugins = json.loads(subprocess.check_output(
        ['hyprctl', '-j', 'plugin', 'list'], text=True, timeout=5))
    if not isinstance(plugins, list) or any(not isinstance(p, dict) for p in plugins):
        raise ValueError('Cannot verify loaded plugins. Config was not changed.')
    if not any(p.get('name') == 'spatialoverview' for p in plugins):
        return
    result = subprocess.run(['hyprctl', 'dispatch', 'hl.plugin.spatialoverview.mode("off")'],
                            capture_output=True, text=True, timeout=5)
    if result.returncode or result.stdout.strip() != 'ok':
        raise ValueError('Canvas shutdown failed: ' + (result.stderr.strip() or result.stdout.strip()) +
                         '. Config and emergency shortcuts were not changed.')
    state = json.loads(subprocess.check_output(['hyprctl', 'spatialoverview'], text=True, timeout=5))
    if (not isinstance(state, dict) or not isinstance(state.get('screens'), list) or
            not isinstance(state.get('fullscreen'), list) or state['screens'] or state['fullscreen']):
        raise ValueError('Cannot confirm that the canvas is closed. Config and emergency shortcuts were not changed.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    actions = ap.add_mutually_exclusive_group()
    actions.add_argument('--enable', action='store_true', help='Connect the module; Hyprland may automatically reload the config')
    actions.add_argument('--remove', action='store_true', help='Disconnect the module and return to tiling')
    ap.add_argument('--target', type=Path,
                    default=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'hotlilith')
    ap.add_argument('--config', type=Path,
                    default=Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'hypr/hyprland.lua')
    args = ap.parse_args(argv)
    config, target = args.config.resolve(), args.target.resolve()
    try:
        if args.enable and config.suffix != '.lua':
            raise ValueError('HotLilith 0.2 supports Lua configuration (.lua). Config was not changed.')
        original = config.read_text() if args.enable or args.remove else None
        text = disconnect(original) if original is not None else None
        if not args.remove:
            current = json.loads(subprocess.check_output(['hyprctl', '-j', 'version'], text=True, timeout=5))
            built = json.loads((ROOT / 'build-version.json').read_text())
            if not built.get('abiHash') or current.get('abiHash') != built['abiHash']:
                raise ValueError('Hyprland ABI changed. Run ./build.sh first. Config was not changed.')
            plugins = subprocess.check_output(['hyprctl', 'plugin', 'list'], text=True, timeout=5)
            if 'spatialoverview' in plugins:
                raise ValueError('An overview plugin is already loaded. Install this build after restarting the session.')
            required = ['spatialoverview.so', 'config/canvas.lua', 'config/bindings.example.lua',
                        'build-version.json', 'LICENSE', 'NOTICE.md']
            for relative in required:
                if not (ROOT / relative).is_file():
                    raise ValueError('Missing build file: ' + relative + '. Run ./build.sh first.')
            for relative in required:
                dest = target / relative
                if dest == ROOT / relative:
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, dest)
            print('Installed files:', target)
            if not args.enable:
                print('Desktop config unchanged. To connect without adding bindings: python3 install.py --enable')
                return 0
            include = str(target / 'config/canvas.lua')
            text += ('\n' if text and not text.endswith('\n') else '')
            binary = str(target / 'spatialoverview.so')
            text += BEGIN + 'hl.plugin.load(' + json.dumps(binary, ensure_ascii=False) + ')\n'
            text += 'dofile(' + json.dumps(include, ensure_ascii=False) + ')\n' + END
        elif text == original:
            print('Module is already disconnected; config unchanged.')
            return 0
        if args.remove:
            close_canvas()
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = config.with_name(config.name + '.before-hotlilit-' + stamp)
        shutil.copy2(config, backup)
        with tempfile.NamedTemporaryFile(mode='w', dir=config.parent, prefix='.hotlilit-', delete=False) as f:
            temporary = Path(f.name)
            f.write(text)
        try:
            shutil.copymode(config, temporary)
            os.replace(temporary, config)
        finally:
            temporary.unlink(missing_ok=True)
        print('Disconnected.' if args.remove else 'Connected.')
        if args.enable:
            print('No key bindings were added. See config/bindings.example.lua for optional examples.')
        print('Backup:', backup)
        print('Hyprland may reload automatically; otherwise run: hyprctl reload')
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
