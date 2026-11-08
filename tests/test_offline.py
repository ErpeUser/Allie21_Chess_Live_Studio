"""Fast checks that need no downloads or model inference."""
import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import config
from vision import sanitize_ocr_history

LAUNCHER_SPEC = importlib.util.spec_from_file_location('allie_launcher', ROOT / 'tools/launcher.py')
allie_launcher = importlib.util.module_from_spec(LAUNCHER_SPEC)
assert LAUNCHER_SPEC.loader is not None
LAUNCHER_SPEC.loader.exec_module(allie_launcher)


class StandaloneTests(unittest.TestCase):
    def test_config_rejects_invalid_fields(self):
        raw = json.dumps({'white_elo': 300, 'recognition_interval_ms': 10,
                          'stability_frames': 3})
        with patch.object(Path, 'read_text', return_value=raw):
            loaded = config.load_config()
        self.assertEqual(loaded['white_elo'], 1950)
        self.assertEqual(loaded['recognition_interval_ms'], 750)
        self.assertEqual(loaded['stability_frames'], 2)

    def test_model_identity_is_fixed_outside_user_config(self):
        raw = json.dumps({'model_id': 'stockfish-not-allie',
                          'model_revision': 'untrusted', 'white_elo': 2000})
        with patch.object(Path, 'read_text', return_value=raw):
            loaded = config.load_config()
        self.assertEqual(loaded['white_elo'], 2000)
        self.assertNotIn('model_id', loaded)
        self.assertNotIn('model_revision', loaded)
        self.assertEqual(config.MODEL_ID, 'yimingzhang/allie-2.1')
        self.assertEqual(config.MODEL_REVISION,
                         'd2545701ff5af46a51ac947911844f779b355a08')

    def test_invalid_json_uses_defaults(self):
        with patch.object(Path, 'read_text', return_value='{broken'):
            self.assertEqual(config.load_config()['time_control'], '300+0')

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
        self.assertTrue((ROOT / 'browser/manifest.json').is_file())
        self.assertFalse((ROOT / 'browser/extension_shim.js').exists())
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
        self.assertIn('UV_PROJECT_ENVIRONMENT=%~dp0.allie-venv', script)
        self.assertIn('sync --frozen --all-extras --no-dev', script)
        self.assertIn('backend\\download_stockfish.py', script)
        self.assertIn('backend\\live_server.py', script)
        self.assertNotIn('AllieLauncher', script)
        self.assertNotIn('auto_setup.ps1', script)

    def test_launcher_check_mode_validates_adjacent_project(self):
        launcher = ROOT / 'tools' / 'launcher.py'
        self.assertTrue(launcher.is_file())
        result = subprocess.run(
            [sys.executable, str(launcher), '--check'],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Allie21 Chess Live Studio: OK', result.stdout)

    def test_tray_quit_stops_only_owned_process_tree(self):
        calls = []
        process = SimpleNamespace(pid=4242, poll=lambda: None, terminate=lambda: calls.append('terminate'))
        runner = lambda args, **kwargs: (calls.append((args, kwargs)) or SimpleNamespace(returncode=0))
        icon = SimpleNamespace(stop=lambda: calls.append('icon-stop'))
        app = allie_launcher.TrayApp(ROOT, command_runner=runner)
        app.process = process

        app.quit(icon)

        self.assertEqual(calls[0][0], ['taskkill', '/PID', '4242', '/T', '/F'])
        self.assertEqual(calls[-1], 'icon-stop')
        self.assertNotIn('terminate', calls)

    def test_tray_open_action_uses_local_viewer(self):
        opened = []
        app = allie_launcher.TrayApp(ROOT, browser_open=opened.append)

        app.open_viewer()

        self.assertEqual(opened, ['http://127.0.0.1:8765/viewer'])

    def test_tray_image_is_visible_and_square(self):
        image = allie_launcher.create_tray_image()
        self.assertEqual(image.size, (64, 64))
        self.assertEqual(image.mode, 'RGBA')
        self.assertIsNotNone(image.getbbox())

    def test_launcher_finds_project_above_onedir_bundle(self):
        nested = ROOT / 'release' / 'Allie21 Chess Live Studio'
        self.assertEqual(allie_launcher.find_project_root(nested), ROOT)

    def test_exe_build_pins_tray_dependencies(self):
        script = (ROOT / 'tools/build_exe.ps1').read_text(encoding='utf-8')
        self.assertIn("--python '3.12'", script)
        self.assertIn("--with 'pystray==0.19.5'", script)
        self.assertIn("--with 'pillow==13.0.0'", script)
        self.assertIn("--hidden-import 'pystray._win32'", script)
        self.assertIn("--onedir", script)
        self.assertNotIn("--onefile", script)

    def test_overlay_is_targeted_batched_and_latest_only(self):
        overlay = (ROOT / 'browser/allie21_overlay.user.js').read_text(encoding='utf-8')
        self.assertIn('@version      11.2.9', overlay)
        manifest = json.loads((ROOT / 'browser/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version_name'], '11.2.9')
        self.assertIn('@match        https://*.chess.com/*', overlay)
        self.assertIn('@match        https://lichess.org/*', overlay)
        self.assertNotIn('@match        *://*/*', overlay)
        self.assertIn('new MutationObserver', overlay)
        self.assertIn('setTimeout(()=>tick(manual),120)', overlay)
        self.assertIn('unsettledRetries<4', overlay)
        self.assertIn('unsettledRetries++;scheduleTick()', overlay)
        self.assertIn("request(fen?'stockfish':'allie',false,!!fen)", overlay)
        self.assertIn("request('both',true,true)", overlay)
        self.assertIn("fen?'stockfish':'allie'", overlay)
        self.assertIn('cfg.playerSide', overlay)
        self.assertIn("localPost('/api/browser-position'", overlay)
        self.assertIn('pgn_candidates:candidates', overlay)
        self.assertIn('function chessComGameId()', overlay)
        self.assertIn('game_id},12000)', overlay)
        self.assertNotIn('fetch(`/callback/live/game/${id}`', overlay)
        self.assertIn("'X-Allie-Overlay':'1'", overlay)
        self.assertIn('new AbortController()', overlay)
        self.assertNotIn('GM_xmlhttpRequest', overlay)
        self.assertIn('activeRequest.abort()', overlay)
        self.assertIn('serial===analysisSerial', overlay)
        self.assertIn('if(!current())', overlay)
        self.assertIn('clearOverlay();show({})', overlay)
        self.assertIn('Math.min(10,rect.width/72)', overlay)
        self.assertIn('function insightLines', overlay)
        self.assertIn('function panelPosition', overlay)
        self.assertIn('placePanel()', overlay)
        self.assertIn('button,[role="button"]', overlay)
        self.assertNotIn("[bn]n?", overlay)
        self.assertNotIn("querySelectorAll('*')", overlay)
        self.assertIn("'[class*=\"move-list\"] button'", overlay)
        self.assertNotIn("if(!roots.some(startsAtMoveOne))return ''", overlay)

    def test_overlay_reads_separate_chesscom_figurine(self):
        result = subprocess.run(
            ['node', str(ROOT / 'tests/test_overlay_parser.js')],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_resolves_player_side_automatically(self):
        result = subprocess.run(
            ['node', str(ROOT / 'tests/test_overlay_auto_side.js')],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_shows_full_analysis_bubble_beside_board(self):
        result = subprocess.run(
            ['node', str(ROOT / 'tests/test_overlay_insights.js')],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_analyzes_standard_start_without_stale_browser_session(self):
        result = subprocess.run(
            ['node', str(ROOT / 'tests/test_overlay_start_position.js')],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_resets_session_and_sends_play_style(self):
        result = subprocess.run(
            ['node', str(ROOT / 'tests/test_overlay_round_style.js')],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_orientation_ignores_hidden_unrelated_boards(self):
        result = subprocess.run(
            ['node', str(ROOT / 'tests/test_overlay_orientation.js')],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_uses_authoritative_site_coordinates_during_animation(self):
        result = subprocess.run(
            ['node', str(ROOT / 'tests/test_overlay_board_adapter.js')],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_arrow_roles_have_the_same_exact_colors_in_both_clients(self):
        expected = {
            'ownTop1': '#16c784',
            'ownTop2': '#7ee2b8',
            'opponentTop1': '#ef3340',
            'opponentTop2': '#ff9299',
            'premove': '#2f80ed',
        }
        for relative in ('viewer/index.html', 'browser/allie21_overlay.user.js'):
            source = (ROOT / relative).read_text(encoding='utf-8')
            for role, color in expected.items():
                self.assertIn(f"{role}:'{color}'", source, f'{relative}: {role}')
            for label in ('Mein Top 1', 'Mein Top 2', 'Gegner Top 1',
                          'Gegner Top 2', 'Sicherer Pre-Move'):
                self.assertIn(label, source, f'{relative}: {label}')

    def test_upstream_stockfish_hash_locked(self):
        script = (ROOT / 'backend/download_stockfish.py').read_text(encoding='utf-8')
        self.assertIn('3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7', script)


if __name__ == '__main__':
    unittest.main()
