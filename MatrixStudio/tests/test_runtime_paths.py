import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_paths import runtime_paths, project_asset


class RuntimePathsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'config').mkdir()
        example = Path(__file__).resolve().parents[2] / 'config/runtime-paths.example.json'
        (self.root / 'config/runtime-paths.example.json').write_bytes(example.read_bytes())

    def test_defaults_do_not_create_runtime_files(self):
        self.assertEqual(runtime_paths(self.root)['comfy_engine'], 'Data/Engines/ComfyUI')
        self.assertFalse((self.root / 'Data').exists())

    def test_existing_legacy_engine_is_reused_without_moving_it(self):
        legacy = self.root / 'Data/Packages/ComfyUI'
        legacy.mkdir(parents=True)
        self.assertEqual(project_asset('comfy_engine', self.root), legacy)
        self.assertFalse((self.root / 'Data/Engines').exists())

    def test_explicit_config_overrides_legacy_and_accepts_absolute_paths(self):
        (self.root / 'Data/Packages/ComfyUI').mkdir(parents=True)
        custom = self.root / 'custom-engine'
        (self.root / 'Data/runtime-paths.json').write_text(json.dumps({'comfy_engine': str(custom)}))
        self.assertEqual(project_asset('comfy_engine', self.root), custom)
        self.assertIn('qwen_vae', runtime_paths(self.root))
