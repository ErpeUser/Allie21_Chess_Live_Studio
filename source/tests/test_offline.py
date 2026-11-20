"""Fast checks that need no downloads or model inference."""
import builtins
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'source/app/backend'))
import chess_extras
import config
import download_stockfish as installer
from vision import sanitize_ocr_history

LAUNCHER_SPEC = importlib.util.spec_from_file_location('allie_launcher', ROOT / 'source/automation/launcher.py')
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

    def test_no_config_file_uses_validated_defaults(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(config, 'PATH', Path(folder) / 'config.json'):
            self.assertEqual(config.load_config(), config.AppConfig().model_dump())

    def test_user_local_engine_requires_pinned_hash(self):
        if os.name != 'nt':
            self.skipTest('Windows engine paths only')
        with tempfile.TemporaryDirectory() as folder:
            engine = Path(folder) / 'Allie21' / 'engines' / 'stockfish.exe'
            engine.parent.mkdir(parents=True)
            engine.write_bytes(b'fake engine')
            other = Path(folder) / 'untrusted.exe'
            other.write_bytes(b'fake engine')
            with patch.dict(os.environ, {'LOCALAPPDATA': folder,
                                         'STOCKFISH_PATH': str(engine),
                                         'ALLIE_ALLOW_EXTERNAL_STOCKFISH': '0'}):
                with patch.object(chess_extras, '_verified_user_engine', return_value=True):
                    self.assertEqual(chess_extras.find_stockfish(), str(engine.resolve()))
                    os.environ['STOCKFISH_PATH'] = str(other)
                    self.assertIsNone(chess_extras.find_stockfish())
                os.environ['STOCKFISH_PATH'] = str(engine)
                with patch.object(chess_extras, '_verified_user_engine', return_value=False):
                    self.assertIsNone(chess_extras.find_stockfish())

    @unittest.skipUnless(os.name == 'nt', 'Stockfish release binaries are Windows-only')
    def test_source_uses_only_hash_verified_engine_from_installed_release(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backend = root / 'backend'
            backend.mkdir()
            engine = (root / 'generated' / 'dist' / 'win' / 'Allie21 Chess Live Studio' / 'app'
                      / 'backend' / 'engines' / 'stockfish.exe')
            engine.parent.mkdir(parents=True)
            payload = b'test-only-verified-engine'
            engine.write_bytes(payload)
            with (patch.object(chess_extras, 'BASE', backend),
                  patch.object(installer, 'EXPECTED_EXE_SHA256', hashlib.sha256(payload).hexdigest()),
                  patch.dict(os.environ, {'LOCALAPPDATA': str(root / 'local'),
                                          'STOCKFISH_PATH': '',
                                          'ALLIE_ALLOW_EXTERNAL_STOCKFISH': '0'}),
                  patch.object(chess_extras.shutil, 'which', return_value=None)):
                chess_extras._verified_user_engine.cache_clear()
                self.assertEqual(chess_extras.find_stockfish(), str(engine.resolve()))
                engine.write_bytes(b'corrupted-release-engine')
                chess_extras._verified_user_engine.cache_clear()
                self.assertIsNone(chess_extras.find_stockfish())

    def test_one_time_control_definition(self):
        self.assertEqual(config.time_profile('60+1'), ('Bullet', .25))
        self.assertEqual(config.time_profile('180+2'), ('Blitz', .65))
        self.assertEqual(config.time_profile('600+0'), ('Rapid', 1.1))
        self.assertEqual(config.time_profile('1800+0'), ('Classical', 2.0))

    def test_service_port_validation_is_shared(self):
        self.assertEqual(config.parse_port('18765'), 18765)
        with self.assertRaises(ValueError):
            config.parse_port('80')
        with self.assertRaises(ValueError):
            config.parse_port('65536')
        with self.assertRaises(ValueError):
            config.parse_port('not-a-port')

    def test_ocr_needs_move_one(self):
        self.assertEqual(sanitize_ocr_history('3. Bb5 a6 4. Ba4'), '')

    def test_ocr_san_construction(self):
        self.assertIn('Nf3', sanitize_ocr_history('1. e4 e5 2. Nf3 Nc6'))

    def test_required_editable_files(self):
        for name in ('START_HIER.bat', 'pyproject.toml', 'uv.lock',
                     'source/app/backend/live_server.py', 'source/app/backend/live_session.py',
                     'source/app/viewer/index.html', 'source/app/browser/allie21_overlay.user.js'):
            self.assertTrue((ROOT / name).is_file(), name)
        self.assertTrue((ROOT / 'source/app/browser/manifest.json').is_file())
        self.assertFalse((ROOT / 'source/app/browser/extension_shim.js').exists())
        for removed in ('requirements.txt', 'ALLIE_VORLADEN.bat', 'TEST_HIER.bat',
                        'source/automation/auto_setup.ps1', 'source/automation/AllieLauncher.cs'):
            self.assertFalse((ROOT / removed).exists(), removed)

    def test_browser_capture_and_optional_vision_dependencies(self):
        viewer = (ROOT / 'source/app/viewer/index.html').read_text(encoding='utf-8')
        self.assertIn('getDisplayMedia', viewer)
        self.assertIn('canvas.toBlob', viewer)
        self.assertIn("(result.opponent_moves?.length?result.opponent_moves:", viewer)
        self.assertIn("(result.my_moves?.length?result.my_moves:", viewer)
        self.assertIn("(result.engine_moves||[]).slice(0,2)", viewer)
        self.assertIn("[result.premove].filter(Boolean)", viewer)
        self.assertIn('id="allieBubble"', viewer)
        self.assertIn('id="recommendationsToggle"', viewer)
        project = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
        self.assertNotIn('mss', project)
        self.assertIn('[project.optional-dependencies]', project)
        self.assertIn('rapidocr==3.10.0', project)
        self.assertIn('onnxruntime==1.31.1', project)

    def test_production_uses_pinned_real_allie_API(self):
        src = (ROOT / 'source/app/backend/allie_local_server.py').read_text(encoding='utf-8')
        self.assertIn('AutoModel.from_pretrained', src)
        self.assertIn('revision=MODEL_REVISION', src)
        self.assertIn('model.analyze(', src)
        self.assertIn('model.predict(', src)
        self.assertNotIn('sorted(result', src)

    def test_single_uv_start_path_wires_stockfish(self):
        script = (ROOT / 'START_HIER.bat').read_text(encoding='utf-8')
        self.assertIn('uv 0.13.7', script)
        self.assertIn('UV_PROJECT_ENVIRONMENT=%ALLIE_GENERATED_DIR%\\environments\\source', script)
        self.assertNotIn('UV_PROJECT_ENVIRONMENT=%~dp0.allie-venv', script)
        self.assertIn('sync --frozen --extra vision --no-dev', script)
        self.assertIn('backend\\download_stockfish.py', script)
        self.assertIn('backend\\live_server.py', script)
        self.assertIn('Pruefe Stockfish 19', script)
        self.assertIn('if "%ALLIE_PORT%"=="" set "ALLIE_PORT=8765"', script)
        self.assertIn('127.0.0.1:%ALLIE_PORT%/viewer', script)
        self.assertNotIn('AllieLauncher', script)
        self.assertNotIn('auto_setup.ps1', script)

    def test_launcher_has_os_level_single_instance_guard(self):
        source = (ROOT / 'source/automation/launcher.py').read_text(encoding='utf-8')
        self.assertIn('CreateMutexW', source)
        self.assertIn('ERROR_ALREADY_EXISTS', source)
        # Never contend with a running user launcher or another test process.
        with patch.object(allie_launcher.SingleInstanceGuard, 'NAME',
                          rf'Local\Allie21LauncherTest-{uuid4().hex}'):
            guard = allie_launcher.SingleInstanceGuard()
            competitor = allie_launcher.SingleInstanceGuard()
            try:
                self.assertTrue(guard.acquire())
                if os.name == 'nt':
                    self.assertFalse(competitor.acquire())
                guard.release()
                self.assertTrue(competitor.acquire())
            finally:
                competitor.release()
                guard.release()

    def test_launcher_check_mode_validates_adjacent_project(self):
        launcher = ROOT / 'source/automation' / 'launcher.py'
        self.assertTrue(launcher.is_file())
        result = subprocess.run(
            [sys.executable, str(launcher), '--check'],
            cwd=ROOT,
            check=False,
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

    def test_launcher_uses_generated_model_cache_without_copying_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cache = root / 'generated' / 'dependencies' / 'models'
            (cache / 'hub' / 'models--yimingzhang--allie-2.1').mkdir(parents=True)
            bundle = root / 'generated' / 'dist' / 'win' / 'Allie21 Chess Live Studio'
            for relative in allie_launcher.PORTABLE_REQUIRED:
                file = bundle / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
            captured = {}

            def capture(_arguments, **kwargs):
                captured.update(kwargs)
                return SimpleNamespace(poll=lambda: None)

            with patch.object(allie_launcher, 'port_available', return_value=True):
                allie_launcher.TrayApp(bundle, process_factory=capture).start()
            self.assertEqual(captured['env'].get('HF_HOME'), str(cache))

    def test_launcher_prevents_regenerating_bytecode_in_portable_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in allie_launcher.PORTABLE_REQUIRED:
                file = root / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
            captured = {}

            def capture(_arguments, **kwargs):
                captured.update(kwargs)
                return SimpleNamespace(poll=lambda: None)

            with (patch.object(allie_launcher, 'port_available', return_value=True),
                  patch.dict(os.environ, {'PYTHONDONTWRITEBYTECODE': '0'})):
                app = allie_launcher.TrayApp(root, process_factory=capture)
                app.start()
            self.assertEqual(captured['env'].get('PYTHONDONTWRITEBYTECODE'), '1')

    def test_launcher_validates_and_propagates_custom_port(self):
        with patch.dict(os.environ, {'ALLIE_PORT': '18765'}):
            self.assertEqual(allie_launcher.configured_port(), 18765)
            self.assertEqual(allie_launcher.viewer_url(), 'http://127.0.0.1:18765/viewer')
        with patch.dict(os.environ, {'ALLIE_PORT': '80'}), self.assertRaises(RuntimeError):
            allie_launcher.configured_port()

    def test_launcher_reuses_healthy_allie_port_without_owning_process(self):
        health = {'alive': True, 'api_version': 2, 'schema_version': 1,
                  'instance_id': 'a' * 32, 'overlay': {}}
        with patch.object(allie_launcher, 'port_available', return_value=False), \
             patch.object(allie_launcher, 'health_snapshot', return_value=health):
            app = allie_launcher.TrayApp(ROOT, process_factory=lambda *_a, **_k: self.fail('must reuse'))
            self.assertIsNone(app.start())
            self.assertTrue(app.reused_existing)
            self.assertFalse(app.owns_process)
            app.stop_server()

    def test_launcher_refuses_foreign_listener_without_killing_it(self):
        calls = []
        with patch.object(allie_launcher, 'port_available', return_value=False), \
             patch.object(allie_launcher, 'health_snapshot', return_value={'alive': True}):
            app = allie_launcher.TrayApp(ROOT, command_runner=lambda *a, **k: calls.append(a))
            with self.assertRaises(RuntimeError):
                app.start()
            app.stop_server()
        self.assertEqual(calls, [])

    def test_tray_image_is_visible_and_square(self):
        image = allie_launcher.create_tray_image()
        self.assertEqual(image.size, (64, 64))
        self.assertEqual(image.mode, 'RGBA')
        self.assertIsNotNone(image.getbbox())

    def test_launcher_finds_project_above_onedir_bundle(self):
        nested = ROOT / 'generated/dist/win' / 'Allie21 Chess Live Studio'
        self.assertEqual(allie_launcher.find_project_root(nested), ROOT)

    def test_launcher_resolves_backend_inside_frozen_bundle(self):
        bundle = ROOT / 'generated/dist/win' / 'Allie21 Chess Live Studio'
        script = bundle / '_internal' / 'launcher.py'
        executable = bundle / 'Allie21 Chess Live Studio.exe'
        self.assertEqual(
            allie_launcher.resolve_backend_path(script, frozen=True, executable=executable),
            bundle / 'app' / 'backend',
        )

    def test_launcher_import_does_not_require_backend_config(self):
        launcher = ROOT / 'source/automation' / 'launcher.py'
        original_import = builtins.__import__

        def reject_config(name, *args, **kwargs):
            if name == 'config':
                raise AssertionError('launcher imported the heavyweight backend config')
            return original_import(name, *args, **kwargs)

        spec = importlib.util.spec_from_file_location('lightweight_launcher', launcher)
        module = importlib.util.module_from_spec(spec)
        with patch('builtins.__import__', reject_config):
            spec.loader.exec_module(module)

    def test_exe_build_pins_tray_dependencies(self):
        script = (ROOT / 'source/automation/build_exe.ps1').read_text(encoding='utf-8')
        self.assertIn("--python '3.12'", script)
        self.assertIn("--with 'pystray==0.19.5'", script)
        self.assertIn("--with 'pillow==13.0.0'", script)
        self.assertIn("--hidden-import 'pystray._win32'", script)
        self.assertIn('$expectedStockfishSha256', script)
        self.assertIn("--onedir", script)
        self.assertNotIn("--onefile", script)
        self.assertIn("__pycache__", script)
        self.assertIn("release-version.json", script)
        self.assertIn("source_revision", script)
        smoke = (ROOT / "source/automation/release_smoke.py").read_text(encoding="utf-8")
        self.assertIn("model_loaded", smoke)
        self.assertIn("stockfish_available", smoke)
        self.assertIn("/readyz?source=both", smoke)
        shortcut = (ROOT / "source/automation/desktop_shortcut.ps1").read_text(encoding="utf-8")
        self.assertIn("release-version.json", shortcut)
        self.assertIn("[switch]$Check", shortcut)
        self.assertIn("$link.TargetPath", shortcut)

    def test_quality_tooling_is_declared_on_demand(self):
        project = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
        for package in ('pytest', 'ruff', 'mypy', 'playwright'):
            self.assertIn(package, project)
        quality = ROOT / 'source/automation' / 'quality_check.ps1'
        self.assertTrue(quality.is_file())
        self.assertIn('pip install --python', quality.read_text(encoding='utf-8'))

    def test_overlay_is_targeted_batched_and_latest_only(self):
        overlay = (ROOT / 'source/app/browser/allie21_overlay.user.js').read_text(encoding='utf-8')
        manifest = json.loads((ROOT / 'source/app/browser/manifest.json').read_text(encoding='utf-8'))
        self.assertIn(f"@version      {manifest['version_name']}", overlay)
        self.assertEqual(manifest['version_name'], manifest['version'].rsplit('.', 1)[0])
        self.assertIn('@match        https://www.chess.com/play/*', overlay)
        self.assertIn('@match        https://lichess.org/*', overlay)
        self.assertNotIn('@match        *://*/*', overlay)
        self.assertIn('const supportedPath=', overlay)
        self.assertIn('new MutationObserver', overlay)
        self.assertIn('ResizeObserver', overlay)
        self.assertIn('location.href', overlay)
        self.assertIn('setTimeout(()=>tick(manual),120)', overlay)
        self.assertIn('unsettledRetries<4', overlay)
        self.assertIn('unsettledRetries++;scheduleTick()', overlay)
        # Execute the real handler instead of requiring the obsolete preview=False source text.
        preview = subprocess.run(
            ['node', str(ROOT / 'source/tests/test_browser_preview.js')], cwd=ROOT,
            check=False, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(preview.returncode, 0, preview.stdout + preview.stderr)
        self.assertNotIn("request('both',true,true)", overlay)
        self.assertIn("source==='allie'", overlay)
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

    def test_extension_badge_reports_local_server_state(self):
        manifest = json.loads((ROOT / 'source/app/browser/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['background']['service_worker'], 'background.js')
        self.assertIn('alarms', manifest['permissions'])
        self.assertIn('storage', manifest['permissions'])
        self.assertEqual(manifest['options_page'], 'options.html')
        self.assertIn('http://127.0.0.1/*', manifest['host_permissions'])
        background = (ROOT / 'source/app/browser/background.js').read_text(encoding='utf-8')
        self.assertIn("chrome.storage.local.get", background)
        self.assertIn("allie21:get-port", background)
        self.assertIn("serviceUrl(port, '/health')", background)
        self.assertIn("setBadgeText", background)
        options = (ROOT / 'source/app/browser/options.html').read_text(encoding='utf-8')
        # MV3 blocks inline executable JavaScript: exercise packaged storage logic.
        storage = subprocess.run(
            ['node', str(ROOT / 'source/tests/test_extension_options.js')], cwd=ROOT,
            check=False, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(storage.returncode, 0, storage.stdout + storage.stderr)
        self.assertIn('min="1024"', options)
        overlay = (ROOT / 'source/app/browser/allie21_overlay.user.js').read_text(encoding='utf-8')
        self.assertIn("id='port'", overlay)
        self.assertIn('ensureServicePort()', overlay)
        self.assertNotIn("http://127.0.0.1:8765/api/capability", overlay)

    def test_overlay_reads_separate_chesscom_figurine(self):
        result = subprocess.run(
            ['node', str(ROOT / 'source/tests/test_overlay_parser.js')],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_resolves_player_side_automatically(self):
        result = subprocess.run(
            ['node', str(ROOT / 'source/tests/test_overlay_auto_side.js')],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_shows_full_analysis_bubble_beside_board(self):
        result = subprocess.run(
            ['node', str(ROOT / 'source/tests/test_overlay_insights.js')],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_analyzes_standard_start_without_stale_browser_session(self):
        result = subprocess.run(
            ['node', str(ROOT / 'source/tests/test_overlay_start_position.js')],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_resets_session_and_sends_play_style(self):
        result = subprocess.run(
            ['node', str(ROOT / 'source/tests/test_overlay_round_style.js')],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_overlay_orientation_ignores_hidden_unrelated_boards(self):
        result = subprocess.run(
            ['node', str(ROOT / 'source/tests/test_overlay_orientation.js')],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        overlay = (ROOT / 'source/app/browser/allie21_overlay.user.js').read_text(encoding='utf-8')
        self.assertIn('boardOrientation(board,pieceNodes(board))', overlay)

    def test_overlay_uses_authoritative_site_coordinates_during_animation(self):
        result = subprocess.run(
            ['node', str(ROOT / 'source/tests/test_overlay_board_adapter.js')],
            cwd=ROOT,
            check=False,
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
        for relative in ('source/app/viewer/index.html', 'source/app/browser/allie21_overlay.user.js'):
            source = (ROOT / relative).read_text(encoding='utf-8')
            for role, color in expected.items():
                self.assertIn(f"{role}:'{color}'", source, f'{relative}: {role}')
            for label in ('Mein Top 1', 'Mein Top 2', 'Gegner Top 1',
                          'Gegner Top 2', 'Pre-Move'):
                self.assertIn(label, source, f'{relative}: {label}')

    def test_upstream_stockfish_hash_locked(self):
        script = (ROOT / 'source/app/backend/download_stockfish.py').read_text(encoding='utf-8')
        self.assertIn('3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7', script)


if __name__ == '__main__':
    unittest.main()
