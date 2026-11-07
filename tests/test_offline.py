"""Fast checks that need no downloads or model inference."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import config
from vision import sanitize_ocr_history


class StandaloneTests(unittest.TestCase):
    def test_config_rejects_fake_model_and_invalid_fields(self):
        raw = json.dumps({'model_id': 'stockfish-not-allie', 'white_elo': 300,
                          'recognition_interval_ms': 10, 'stability_frames': 3})
        with patch.object(Path, 'read_text', return_value=raw):
            loaded = config.load_config()
        self.assertEqual(loaded['model_id'], 'yimingzhang/allie-2.1')
        self.assertEqual(loaded['white_elo'], 1950)
        self.assertEqual(loaded['recognition_interval_ms'], 750)
        self.assertEqual(loaded['stability_frames'], 2)

    def test_invalid_json_uses_defaults(self):
        with patch.object(Path, 'read_text', return_value='{broken'):
            self.assertEqual(config.load_config()['time_control'], '600+0')

    def test_one_time_control_definition(self):
        self.assertEqual(config.time_profile('60+1'), ('Bullet', .25))
        self.assertEqual(config.time_profile('180+2'), ('Blitz', .65))
        self.assertEqual(config.time_profile('600+0'), ('Rapid', 1.1))
        self.assertEqual(config.time_profile('1800+0'), ('Classical', 2.0))

    def test_ocr_needs_move_one(self):
        self.assertEqual(sanitize_ocr_history('3. Bb5 a6 4. Ba4'), '')

    def test_ocr_san_construction(self):
        self.assertIn('Nf3', sanitize_ocr_history('1. e4 e5 2. Nf3 Nc6'))

    def test_required_editable_files(self):
        for name in ('START_HIER.bat', 'pyproject.toml', 'uv.lock', 'config.json',
                     'backend/live_server.py', 'backend/live_session.py',
                     'viewer/index.html', 'browser/allie21_overlay.user.js'):
            self.assertTrue((ROOT / name).is_file(), name)
        for removed in ('requirements.txt', 'ALLIE_VORLADEN.bat', 'TEST_HIER.bat',
                        'tools/auto_setup.ps1', 'tools/AllieLauncher.cs'):
            self.assertFalse((ROOT / removed).exists(), removed)

    def test_browser_capture_and_optional_vision_dependencies(self):
        viewer = (ROOT / 'viewer/index.html').read_text(encoding='utf-8')
        self.assertIn('getDisplayMedia', viewer)
        self.assertIn('canvas.toBlob', viewer)
        self.assertIn("(result.opponent_moves||[]).slice(0,2)", viewer)
        self.assertIn("(result.my_moves||[]).slice(0,2)", viewer)
        self.assertIn("[result.premove].filter(Boolean)", viewer)
        self.assertIn('id="allieBubble"', viewer)
        self.assertIn('id="recommendationsToggle"', viewer)
        project = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
        self.assertNotIn('mss', project)
        self.assertIn('[project.optional-dependencies]', project)
        self.assertIn('rapidocr==3.10.0', project)
        self.assertIn('onnxruntime==1.31.1', project)

    def test_production_uses_pinned_real_allie_API(self):
        src = (ROOT / 'backend/allie_local_server.py').read_text(encoding='utf-8')
        self.assertIn('AutoModel.from_pretrained', src)
        self.assertIn('revision=MODEL_REVISION', src)
        self.assertIn('model.analyze(', src)
        self.assertIn('model.predict(', src)
        self.assertNotIn('sorted(result', src)

    def test_single_uv_start_path_wires_stockfish(self):
        script = (ROOT / 'START_HIER.bat').read_text(encoding='utf-8')
        self.assertIn('uv 0.13.7', script)
        self.assertIn('uv sync --frozen --all-extras --no-dev', script)
        self.assertIn('backend\\download_stockfish.py', script)
        self.assertIn('backend\\live_server.py', script)
        self.assertNotIn('AllieLauncher', script)
        self.assertNotIn('auto_setup.ps1', script)

    def test_overlay_is_targeted_batched_and_latest_only(self):
        overlay = (ROOT / 'browser/allie21_overlay.user.js').read_text(encoding='utf-8')
        self.assertIn('@version      11.0.0', overlay)
        self.assertIn('@match        https://*.chess.com/*', overlay)
        self.assertIn('@match        https://lichess.org/*', overlay)
        self.assertNotIn('@match        *://*/*', overlay)
        self.assertIn('new MutationObserver', overlay)
        self.assertIn('setTimeout(()=>tick(manual),250)', overlay)
        self.assertIn("analysis_source:'both'", overlay)
        self.assertNotIn("analysis_source:'stockfish'", overlay)
        self.assertNotIn("analysis_source:'allie'", overlay)
        self.assertIn('cfg.playerSide', overlay)
        self.assertIn("localPost('/api/browser-position'", overlay)
        self.assertIn("'X-Allie-Overlay':'1'", overlay)
        self.assertIn('const current=()=>analysisKey===key', overlay)
        self.assertIn('if(!current())', overlay)
        self.assertIn('clearOverlay();show({})', overlay)

    def test_upstream_stockfish_hash_locked(self):
        script = (ROOT / 'backend/download_stockfish.py').read_text(encoding='utf-8')
        self.assertIn('3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7', script)


if __name__ == '__main__':
    unittest.main()
