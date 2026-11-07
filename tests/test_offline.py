"""Runs without downloading chess models, Python packages or touching the internet."""
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
    def test_config_rejects_fake_model(self):
        raw = json.dumps({'model_id':'stockfish-not-allie', 'white_elo':300,
                          'recognition_interval_ms':10, 'stability_frames':3})
        with patch.object(Path, 'read_text', return_value=raw):
            c = config.load_config()
        self.assertEqual(c['model_id'], 'yimingzhang/allie-2.1')
        self.assertEqual(c['white_elo'], 1950)
        self.assertEqual(c['recognition_interval_ms'], 750)
        self.assertEqual(c['stability_frames'], 3)

    def test_invalid_json_uses_defaults(self):
        with patch.object(Path, 'read_text', return_value='{broken'):
            self.assertEqual(config.load_config()['time_control'], '600+0')

    def test_ocr_needs_move_one(self):
        self.assertEqual(sanitize_ocr_history('3. Bb5 a6 4. Ba4'), '')

    def test_ocr_san_construction(self):
        self.assertIn('Nf3', sanitize_ocr_history('1. e4 e5 2. Nf3 Nc6'))

    def test_required_editable_files(self):
        for name in ('START_HIER.bat', 'requirements.txt', 'config.json',
                     'backend/live_server.py', 'backend/live_session.py',
                     'viewer/index.html', 'browser/allie21_overlay.user.js'):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_browser_capture_replaces_native_code(self):
        viewer = (ROOT / 'viewer/index.html').read_text(encoding='utf-8')
        self.assertIn('getDisplayMedia', viewer)
        self.assertIn('canvas.toBlob', viewer)
        self.assertIn('stream-hud' if 'stream-hud' in viewer else 'id="hud"', viewer)
        self.assertIn("(result.opponent_moves||[]).slice(0,2)", viewer)
        self.assertIn("(result.my_moves||[]).slice(0,2)", viewer)
        self.assertIn("[result.premove].filter(Boolean)", viewer)
        self.assertNotIn("(result.stockfish||{}).lines", viewer)
        self.assertNotIn('id="moveBadges"', viewer)
        self.assertNotIn("createElementNS('http://www.w3.org/2000/svg','text')", viewer)
        self.assertIn('id="allieBubble"', viewer)
        self.assertIn('id="recommendationsToggle"', viewer)
        self.assertIn("post('/api/recommendations',{enabled})", viewer)
        self.assertNotIn('Gegner nach', viewer)
        req = (ROOT / 'requirements.txt').read_text(encoding='utf-8')
        self.assertNotIn('mss', req)
        self.assertIn('rapidocr', req)
        self.assertIn('onnxruntime', req)
        self.assertIn('transformers', req)

    def test_no_simulated_model_in_production(self):
        src = (ROOT / 'backend/allie_local_server.py').read_text(encoding='utf-8')
        self.assertIn('AutoModel.from_pretrained', src)
        self.assertIn('model.analyze(', src)
        self.assertIn('MODEL_NAME = MODEL_ID', src)
        self.assertIn('fen_only', src)

    def test_installer_wires_stockfish(self):
        script = (ROOT / 'tools/auto_setup.ps1').read_text(encoding='utf-8')
        self.assertIn('download_stockfish.py', script)
        self.assertIn('pip install', script)
        self.assertIn('Python.Python.3.12', script)
        self.assertIn('requirements-sha256', script)

    def test_generic_overlay_tracks_the_visible_board(self):
        overlay = (ROOT / 'browser/allie21_overlay.user.js').read_text(encoding='utf-8')
        self.assertIn('@version      10.7.0', overlay)
        self.assertIn('@match        *://*/*', overlay)
        self.assertIn('placementFromBoard(board)', overlay)
        self.assertIn("localPost('/api/browser-position'", overlay)
        self.assertIn("'X-Allie-Overlay':'1'", overlay)
        self.assertIn("wrapper.style.display=visibleBoard?'':'none'", overlay)
        self.assertIn('structuralMoveRoot()', overlay)
        self.assertIn('wc-simple-move-list', overlay)
        self.assertIn('wc-vertical-move-list', overlay)
        self.assertIn('candidateMoveRoots()', overlay)
        self.assertIn("'♞':'N'", overlay)
        self.assertIn('button[data-ply="0"]', overlay)
        self.assertIn("isStandardStartPosition()?'*':''", overlay)
        self.assertIn("values.filter(x=>x==='wk').length!==1", overlay)
        self.assertIn('Live-Hinweise:', overlay)
        self.assertNotIn('permittedPage', overlay)
        self.assertNotIn('Mensch-gegen-Mensch', overlay)
        self.assertNotIn('token', overlay.lower())
        self.assertIn("data.opponent_moves", overlay)
        self.assertIn("data.my_moves", overlay)
        self.assertIn("data.premove", overlay)
        self.assertIn("tc:'600+0'", overlay)
        self.assertIn("analysis_source:'stockfish'", overlay)
        self.assertIn("analysis_source:'allie'", overlay)
        self.assertIn('wc-move-list .main-line-ply', overlay)
        self.assertIn('wc-chess-board', overlay)
        self.assertIn('data.plan_messages', overlay)
        self.assertIn('clearOverlay();show({})', overlay)

    def test_installer_detects_existing_python_312(self):
        script = (ROOT / 'tools/auto_setup.ps1').read_text(encoding='utf-8')
        self.assertIn("print('OK' if sys.version_info[:2] == (3,12)", script)
        self.assertIn('$pythonExe = [string]$p.Executable', script)
        self.assertNotIn('& $p.Executable', script)
        self.assertIn('$wingetExitCode = $LASTEXITCODE', script)

    def test_upstream_stockfish_hash_locked(self):
        script = (ROOT / 'backend/download_stockfish.py').read_text(encoding='utf-8')
        self.assertIn('3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7', script)


if __name__ == '__main__':
    unittest.main()
