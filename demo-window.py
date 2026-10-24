#!/usr/bin/env python3
"""Synthetic content for real foot windows in the disposable preview."""
import sys
import time

title = sys.argv[1]
content = {
    'Canvas notes': [
        'Two scopes, one shortcut', '',
        'Workspace canvas  /  Global canvas',
        'Positions and zoom are remembered.', '',
        'New window? Draw its region.',
        'Escape places it automatically.',
        'Dialogs stay with their parent.',
    ],
    'Controls': [
        'Super + G        Tiling / canvas',
        'Super + Ctrl + G Switch scope',
        'Ctrl + wheel     Zoom',
        'Middle drag      Pan',
        'Super + drag     Move window',
        'Super + Z        Fit everything', '',
        'Super + Ctrl + Shift + G',
        'Emergency return to tiling',
    ],
    'Terminal': [
        '$ python3 preview.py', '',
        'Disposable Hyprland session',
        'Three real Wayland foot windows',
        'Synthetic demonstration content', '',
        'Main desktop config stays separate.',
    ],
}
print('\033[2J\033[H\033[1;36mHotLilith 0.2 / ' + title + '\033[0m\n')
print('\n'.join(content.get(title, content['Terminal'])), flush=True)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
