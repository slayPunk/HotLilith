import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('installer', Path(__file__).resolve().parents[1] / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hotlilit-install-')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.bundle, self.target = self.base/'bundle', self.base/'установка с пробелами'
        self.config = self.base/'hyprland.lua'
        self.original = '-- my config\nhl.bind("SUPER + L", function() end)\n'
        self.config.write_text(self.original)
        for name in ['spatialoverview.so','config/canvas.lua','config/bindings.example.lua',
                     'LICENSE','NOTICE.md','build-version.json']:
            p=self.bundle/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(json.dumps({'abiHash':'tested-abi'}) if name.endswith('.json') else '-- fixture\n')
        self.root_patch = patch.object(installer, 'ROOT', self.bundle)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.outputs = patch.object(installer.subprocess,'check_output',side_effect=self.fake_output)
        self.outputs.start()
        self.addCleanup(self.outputs.stop)
        self.run_patch = patch.object(installer.subprocess,'run', return_value=subprocess.CompletedProcess([], 0, 'ok\n', ''))
        self.shutdown = self.run_patch.start()
        self.addCleanup(self.run_patch.stop)
        self.abi = 'tested-abi'
        self.plugins = []
        self.canvas = {'screens': [], 'fullscreen': []}

    def fake_output(self, args, **kwargs):
        if 'version' in args:
            return json.dumps({'abiHash':self.abi})
        if args[-1] == 'spatialoverview':
            return json.dumps(self.canvas)
        return json.dumps(self.plugins) if '-j' in args else str(self.plugins)

    def invoke(self, *args):
        return installer.main([*args,'--target',str(self.target),'--config',str(self.config)])

    def test_copy_does_not_change_config(self):
        self.assertEqual(self.invoke(),0)
        self.assertEqual(self.config.read_text(),self.original)
        self.assertTrue((self.target/'spatialoverview.so').is_file())
        self.assertEqual(list(self.base.glob('*.before-hotlilit-*')),[])

    def test_enable_and_remove_preserve_original_unicode_config(self):
        self.assertEqual(self.invoke('--enable'),0)
        included=self.config.read_text()
        self.assertIn(str(self.target/'config/canvas.lua'),included)
        self.assertNotIn('\\u04',included)
        self.assertEqual(installer.disconnect(included),self.original)
        self.assertTrue(list(self.base.glob('*.before-hotlilit-*')))
        self.assertEqual(self.invoke('--remove'),0)
        self.assertEqual(self.config.read_text(),self.original)

    def test_repeated_enable_has_single_include(self):
        self.assertEqual(self.invoke('--enable'),0)
        self.assertEqual(self.invoke('--enable'),0)
        self.assertEqual(self.config.read_text().count(installer.BEGIN),1)

    def test_enable_leaves_optional_bindings_out_of_config(self):
        self.assertEqual(self.invoke('--enable'), 0)
        self.assertNotIn('bindings.example.lua', self.config.read_text())
        self.assertTrue((self.target/'config/bindings.example.lua').is_file())

    def test_legacy_connection_is_migrated_once(self):
        self.config.write_text(self.original+installer.LEGACY_BEGIN+'-- old\n'+installer.LEGACY_END)
        self.assertEqual(self.invoke('--enable'), 0)
        self.assertNotIn(installer.LEGACY_BEGIN, self.config.read_text())
        self.assertEqual(self.config.read_text().count(installer.BEGIN), 1)

    def test_multiple_old_and_new_blocks_are_rejected(self):
        text=self.original+installer.BEGIN+installer.END+installer.LEGACY_BEGIN+installer.LEGACY_END
        self.config.write_text(text)
        self.assertEqual(self.invoke('--enable'), 1)
        self.assertEqual(self.config.read_text(),text)
        self.assertFalse(self.target.exists())

    def test_hyprlang_config_is_not_modified(self):
        config=self.base/'hyprland.conf';config.write_text('# existing Hyprlang\n')
        self.assertEqual(installer.main(['--enable','--config',str(config),'--target',str(self.target)]), 1)
        self.assertEqual(config.read_text(),'# existing Hyprlang\n')
        self.assertFalse(self.target.exists())

    def test_xdg_defaults_use_generic_location(self):
        with patch.dict(os.environ, {'XDG_DATA_HOME':str(self.base/'data'),
                                    'XDG_CONFIG_HOME':str(self.base/'config')}):
            config=self.base/'config/hypr/hyprland.lua'
            config.parent.mkdir(parents=True);config.write_text(self.original)
            self.assertEqual(installer.main(['--enable']),0)
            self.assertIn(str(self.base/'data/hotlilith/config/canvas.lua'),config.read_text())

    def test_wrong_abi_does_not_touch_config_or_destination(self):
        self.abi='different-version'
        self.assertEqual(self.invoke('--enable'),1)
        self.assertEqual(self.config.read_text(),self.original)
        self.assertFalse(self.target.exists())

    def test_malformed_markers_leave_config_untouched(self):
        text=self.original+installer.BEGIN
        self.config.write_text(text)
        self.assertEqual(self.invoke('--enable'),1)
        self.assertEqual(self.config.read_text(),text)
        self.assertFalse(self.target.exists())

    def test_reversed_markers_leave_config_untouched(self):
        text=installer.END+self.original+installer.BEGIN
        self.config.write_text(text)
        self.assertEqual(self.invoke('--remove'),1)
        self.assertEqual(self.config.read_text(),text)

    def connected_config(self):
        text = self.original + installer.BEGIN + '-- canvas bindings\n' + installer.END
        self.config.write_text(text)
        self.plugins = [{'name': 'spatialoverview'}]
        return text

    def assert_remove_refused(self, original):
        self.assertEqual(self.invoke('--remove'), 1)
        self.assertEqual(self.config.read_text(), original)
        self.assertEqual(list(self.base.glob('*.before-hotlilit-*')), [])

    def test_remove_checks_command_failure(self):
        original = self.connected_config()
        self.shutdown.return_value = subprocess.CompletedProcess([], 1, 'error: shutdown failed', '')
        self.assert_remove_refused(original)

    def test_remove_checks_error_reply_even_with_zero_exit_status(self):
        original = self.connected_config()
        self.shutdown.return_value = subprocess.CompletedProcess([], 0, 'error: dispatcher failed', '')
        self.assert_remove_refused(original)

    def test_remove_preserves_emergency_binding_if_canvas_stays_active(self):
        original = self.connected_config()
        self.canvas['screens'] = [{'monitor': 'test'}]
        self.assert_remove_refused(original)

    def test_remove_preserves_emergency_binding_while_fullscreen_stepped_aside(self):
        original = self.connected_config()
        self.canvas['fullscreen'] = [{'window': 'test'}]
        self.assert_remove_refused(original)

    def test_remove_requires_valid_state_reply(self):
        original = self.connected_config()
        self.canvas = {}
        self.assert_remove_refused(original)

    def test_remove_handles_ipc_timeout_without_changing_config(self):
        original = self.connected_config()
        self.shutdown.side_effect = subprocess.TimeoutExpired(['hyprctl'], 5)
        self.assert_remove_refused(original)

    def test_remove_accepts_missing_plugin_without_calling_dispatcher(self):
        self.connected_config()
        self.plugins = []
        self.assertEqual(self.invoke('--remove'), 0)
        self.assertEqual(self.config.read_text(), self.original)
        self.shutdown.assert_not_called()

    def test_remove_accepts_verified_shutdown(self):
        self.connected_config()
        self.assertEqual(self.invoke('--remove'), 0)
        self.assertEqual(self.config.read_text(), self.original)
        self.shutdown.assert_called_once()


if __name__=='__main__': unittest.main()
