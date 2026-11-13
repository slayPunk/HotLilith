"""Exercise the real build wrapper/Makefile with a tiny compiled plugin.

Only the running/header ABI probes are simulated; make, C++ compilation,
linking and stripping are real. No compositor or installed header is changed.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hotlilit-build-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ['build.sh', 'source/Makefile', 'source/scripts/generate-plugin-version.sh']:
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, dest)
        (self.root / 'source/fixture.cpp').write_text(
            '#include "fixture-abi.h"\nextern "C" const char* built_abi() { return FIXTURE_ABI; }\n')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        probes = {
            'c++': '''#!/usr/bin/python3
import os, pathlib, sys
p=pathlib.Path(sys.argv[sys.argv.index('-o')+1])
p.write_text('#!/usr/bin/python3\\nprint(' + repr(os.environ['TEST_HEADER_ABI']) + ')\\n')
p.chmod(0o755)
''',
            'hyprctl': '''#!/usr/bin/python3
import json, os
print(json.dumps({'abiHash':os.environ.get('TEST_RUNNING_ABI',os.environ['TEST_HEADER_ABI'])}))
''',
            'pkg-config': '#!/bin/sh\nexit 0\n',
        }
        for name, source in probes.items():
            path = self.bin / name
            path.write_text(source)
            path.chmod(0o755)

    def build(self, abi, *, running=None):
        (self.root / 'source/fixture-abi.h').write_text('#define FIXTURE_ABI ' + json.dumps(abi) + '\n')
        env = os.environ.copy()
        env.pop('TEST_RUNNING_ABI', None)
        env.update(PATH=str(self.bin) + os.pathsep + env['PATH'], TEST_HEADER_ABI=abi,
                   MAKEFLAGS='SOURCES=fixture.cpp PKGS=fixture')
        if running is not None:
            env['TEST_RUNNING_ABI'] = running
        return subprocess.run(['bash', str(self.root / 'build.sh')], env=env,
                              capture_output=True, text=True, timeout=30)

    def built_abi(self):
        # A new process avoids dlopen's cache when the same path is replaced.
        code = ('import ctypes,sys; p=ctypes.CDLL(sys.argv[1]); '
                'p.built_abi.restype=ctypes.c_char_p; print(p.built_abi().decode())')
        return subprocess.check_output(['/usr/bin/python3', '-c', code, str(self.root/'spatialoverview.so')], text=True).strip()

    def test_new_abi_recompiles_existing_objects_and_metadata_matches_binary(self):
        first = self.build('abi-a')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(self.built_abi(), 'abi-a')
        source_mtime = (self.root/'source/fixture.cpp').stat().st_mtime_ns
        second = self.build('abi-b')
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual((self.root/'source/fixture.cpp').stat().st_mtime_ns, source_mtime)
        self.assertEqual(self.built_abi(), 'abi-b')
        self.assertEqual(json.loads((self.root/'build-version.json').read_text())['abiHash'], 'abi-b')

    def test_header_runtime_mismatch_preserves_previous_binary_and_metadata(self):
        first = self.build('abi-a')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        binary = (self.root/'spatialoverview.so').read_bytes()
        metadata = (self.root/'build-version.json').read_bytes()
        result = self.build('abi-b', running='abi-c')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root/'spatialoverview.so').read_bytes(), binary)
        self.assertEqual((self.root/'build-version.json').read_bytes(), metadata)

    def test_missing_dependencies_preserve_previous_build(self):
        first = self.build('abi-a')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        binary = (self.root/'spatialoverview.so').read_bytes()
        metadata = (self.root/'build-version.json').read_bytes()
        (self.bin/'pkg-config').write_text('#!/bin/sh\necho "missing development dependency" >&2\nexit 1\n')
        result = self.build('abi-b')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing development dependency', result.stderr)
        self.assertFalse((self.root/'source/.build/obj/abi-b').exists())
        self.assertEqual((self.root/'spatialoverview.so').read_bytes(), binary)
        self.assertEqual((self.root/'build-version.json').read_bytes(), metadata)


if __name__ == '__main__':
    unittest.main()
