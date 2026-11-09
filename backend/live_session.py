"""One latest-only video analysis worker; browser handles window/tab capture and playback.

No mss, native Win32 hooks, persistent screenshot files, mouse automation, or
video uploads. Only small JPEG frames are passed to localhost for chessvision.
"""
from __future__ import annotations

import hashlib
import json
import warnings
from io import BytesIO
from threading import Event, RLock, Thread

from allie_local_server import analyse_position
from chess_extras import make_brief
from config import CONFIG, MODEL_ID, parse_time_control
from PIL import Image, UnidentifiedImageError
from position_tracker import PositionTracker
from vision import BoardVision

MAX_JPEG = 3_500_000
MAX_JPEG_PIXELS = 2_200 * 2_200
Image.MAX_IMAGE_PIXELS = MAX_JPEG_PIXELS
warnings.simplefilter('error', Image.DecompressionBombWarning)
class LiveSession:
    def __init__(self):
        self.lock = RLock()
        self.analysis_event = Event()
        self.tracker = PositionTracker()
        self.vision = None  # loaded on first frame, not at server startup
        self.generation = 0
        self.session_id = 0
        self.analysis_job = None
        self.failed_key = None
        self.settings = {}
        self.stable_placement = None
        self.stable_count = 0
        self.unmatched_frames = 0
        self.state = {}
        self.render_revision = 0
        self._reset_state(False)
        Thread(target=self._analysis_worker, name='allie-first-analysis', daemon=True).start()

    def _reset_state(self, running):
        recommendations_enabled = bool(self.settings.get('recommendations_enabled', True))
        self.state = {'running': running, 'message': ('Bereit – Fenster oder Tab freigeben' if running else 'Gestoppt'),
                      'detection': None, 'result': None, 'analysing': False,
                      'history_complete': False, 'turn_verified': False,
                      'history_source': 'unknown', 'moves_seen': 0, 'model': MODEL_ID,
                      'recommendations_enabled': recommendations_enabled,
                      'session_id': str(self.session_id), 'generation': self.generation,
                      'render_revision': self.render_revision}

    def get_state(self):
        with self.lock:
            return json.loads(json.dumps(self.state, ensure_ascii=False))

    def start(self, settings):
        white = int(settings.get('white_elo', CONFIG['white_elo']))
        black = int(settings.get('black_elo', CONFIG['black_elo']))
        tc = str(settings.get('time_control', CONFIG['time_control']))
        if not 600 <= white <= 2800 or not 600 <= black <= 2800:
            raise ValueError('Elo muss zwischen 600 und 2800 liegen')
        parse_time_control(tc)
        player_side = str(settings.get('player_side', CONFIG['player_side']))
        if player_side not in ('white', 'black'):
            raise ValueError('Spielerfarbe muss white oder black sein')
        with self.lock:
            self.generation += 1
            self.session_id += 1
            self.render_revision += 1
            self.tracker = PositionTracker()
            self.vision = None
            self.analysis_job = None
            self.failed_key = None
            self.analysis_event.clear()
            self.stable_placement, self.stable_count = None, 0
            self.unmatched_frames = 0
            self.settings = {'white_elo': white, 'black_elo': black,
                             'player_side': player_side, 'time_control': tc,
                             'preview': CONFIG['preview_opponent_replies'],
                             'play_style': str(settings.get('play_style', 'normal')),
                             'opening_white': str(settings.get('opening_white', 'grob')),
                             'opening_black': str(settings.get('opening_black', 'englund')),
                             'ocr_history': bool(settings.get('ocr_history', CONFIG['ocr_history'])),
                             'recommendations_enabled': bool(settings.get('recommendations_enabled', True))}
            self._reset_state(True)
            self.state['message'] = ('Suche das Schachbrett im freigegebenen Video ...'
                                     if self.settings['recommendations_enabled']
                                     else 'Live-Zugpfeile und Empfehlungen sind ausgeschaltet')
        return self.get_state()

    def stop(self):
        with self.lock:
            self.generation += 1
            self.session_id += 1
            self.render_revision += 1
            self.analysis_job = None
            self.failed_key = None
            self.analysis_event.clear()
            self.tracker.reset()
            self.vision = None
            self.stable_placement, self.stable_count = None, 0
            self.unmatched_frames = 0
            self._reset_state(False)
        return self.get_state()

    def _queue_locked(self):
        if not self.settings.get('recommendations_enabled', True):
            self.state['result'] = None
            self.state['analysing'] = False
            return
        board = self.tracker.board
        if not board or not self.tracker.turn_verified or not board.is_valid() or board.is_game_over():
            self.state['result'] = None
            self.state['analysing'] = False
            return
        # Never pass FEN as if it were full human history.
        field = 'pgn' if self.tracker.complete_history else 'fen'
        text = self.tracker.pgn_uci if self.tracker.complete_history else board.fen()
        payload = dict(self.settings)
        payload[field] = text
        payload['show_moves'] = bool(self.tracker.complete_history)
        job_key = (field, text)
        if job_key == self.failed_key:
            return
        self.generation += 1
        revision = self.generation
        # A complete history goes to Allie first. Stockfish is used for
        # incomplete histories and the explicit fallback in the worker.
        payload['analysis_source'] = 'allie' if self.tracker.complete_history else 'stockfish'
        payload['session_id'] = str(self.session_id)
        payload['generation'] = revision
        payload['history_complete'] = bool(self.tracker.complete_history)
        payload['turn_verified'] = bool(self.tracker.turn_verified)
        payload['analysis_key'] = hashlib.sha256(f"{field}:{text}".encode()).hexdigest()
        self.analysis_job = (revision, payload)
        self.state['result'] = None
        self.state['analysing'] = True
        self.state['generation'] = revision
        self.state['session_id'] = str(self.session_id)
        self.render_revision += 1
        self.state['render_revision'] = self.render_revision
        self.analysis_event.set()

    def set_recommendations(self, enabled: bool):
        """Immediately enable or suppress every live recommendation job."""
        with self.lock:
            if not self.state['running']:
                raise ValueError('Zuerst eine Quelle starten')
            enabled = bool(enabled)
            self.settings['recommendations_enabled'] = enabled
            self.state['recommendations_enabled'] = enabled
            self.generation += 1
            self.analysis_job = None
            self.analysis_event.clear()
            self.state['result'] = None
            self.state['analysing'] = False
            if enabled:
                self.failed_key = None
                self._queue_locked()
                self.state['message'] = ('Live-Empfehlungen eingeschaltet – Analyse läuft ...'
                                         if self.state['analysing']
                                         else 'Live-Empfehlungen eingeschaltet')
            else:
                self.state['message'] = 'Live-Zugpfeile und Empfehlungen sind ausgeschaltet'
        return self.get_state()

    def import_pgn(self, notation: str):
        with self.lock:
            if not self.state['running'] or not self.state['detection']:
                raise ValueError('Zuerst ein Brett im Stream erkennen lassen')
            change = self.tracker.set_notation(notation, self.state['detection']['fen'], origin='PGN-Import')
            if change.changed:
                self._update_history_locked()
                self._queue_locked()
            return {'accepted': change.changed, 'message': change.message}

    def _update_history_locked(self):
        self.state['history_complete'] = self.tracker.complete_history
        self.state['turn_verified'] = self.tracker.turn_verified
        self.state['history_source'] = self.tracker.history_origin
        self.state['moves_seen'] = len(self.tracker.moves)

    def _clear_detection_locked(self, message):
        self.state['detection'] = None
        self.state['result'] = None
        self.state['analysing'] = False
        self.state['message'] = message
        self.generation += 1
        self.analysis_job = None

    def submit_frame(self, data: bytes):
        if not 0 < len(data) <= MAX_JPEG:
            raise ValueError('Videoframe zu groß (maximal 3,5 MB)')
        with self.lock:
            if not self.state['running']:
                raise ValueError('Stream-Erkennung wurde nicht gestartet')
            started_session = self.session_id
            vision = self.vision
        if vision is None:
            # ONNX classifier initialization can download weights; never hold the UI lock.
            vision = BoardVision()
            with self.lock:
                if started_session != self.session_id:
                    return self.get_state()
                if self.vision is None:
                    self.vision = vision
                else:
                    vision = self.vision
        try:
            with Image.open(BytesIO(data)) as source:
                if (source.format != 'JPEG' or max(source.size) > 2200
                        or min(source.size) < 200
                        or source.size[0] * source.size[1] > MAX_JPEG_PIXELS):
                    raise ValueError('Erwartet: JPEG zwischen 200 und 2200 Pixeln')
                frame = source.convert('RGB')
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:
            raise ValueError('Das Videoframe ist nicht lesbar') from exc
        detected = vision.recognize(frame)
        with self.lock:
            if not self.state['running'] or started_session != self.session_id:
                return self.get_state()
            # A new analysis job may have been queued meanwhile. This is fine;
            # screen frames are serialized by the client and update the current state.
            if not detected:
                self.stable_placement, self.stable_count = None, 0
                self._clear_detection_locked('Kein zuverlässiges Schachbrett erkannt')
                return self.get_state()
            placement = detected['fen'].split(' ')[0]
            if placement != self.stable_placement:
                self.stable_placement, self.stable_count = placement, 1
                self._clear_detection_locked('Neue Stellung wird bestätigt ...')
                return self.get_state()
            self.stable_count += 1
            if self.stable_count < CONFIG['stability_frames']:
                return self.get_state()
            change = self.tracker.observe(detected['fen'])
            current = self.tracker.current_fen()
            agrees = bool(current and current.split(' ')[0] == placement)
            if not agrees:
                self.unmatched_frames += 1
                self._clear_detection_locked('Stellungswechsel nicht eindeutig; warte auf stabile Figuren')
                if self.unmatched_frames >= 4:
                    # Do not get stuck forever after three or more missed plies.
                    # Discard unprovable history rather than fabricate moves.
                    self.tracker.reset()
                    self.tracker.observe(detected['fen'])
                    self.unmatched_frames = 0
                    self._update_history_locked()
                    self.state['message'] = 'Nach nicht rekonstruierbarem Sprung neu synchronisiert; History unbekannt'
                return self.get_state()
            self.unmatched_frames = 0
            detected['fen'] = current
            detected['frame'] = list(frame.size)
            self.state['detection'] = detected
            self._update_history_locked()
            if change.changed:
                if self.tracker.turn_verified:
                    self._queue_locked()
                    self.state['message'] = change.message
                else:
                    self.state['message'] = 'Zugrecht unbekannt; warte auf beobachteten Spielzug'
            elif self.state['result'] and self.state['result']['fen'] != current:
                self._clear_detection_locked('Analyse stimmt nicht mit dem sichtbaren Brett überein')
                return self.get_state()
            elif not self.state['result'] and not self.state['analysing'] and self.tracker.turn_verified:
                # A transient missed video frame discarded previous results. Resume.
                self._queue_locked()
        # OCR is expensive. Run outside the state lock, at most once per seven seconds.
        if self.settings.get('ocr_history') and not self.tracker.complete_history:
            notation = vision.read_notation(frame, detected['box'])
            if notation:
                try:
                    with self.lock:
                        if started_session != self.session_id:
                            return self.get_state()
                    self.import_pgn(notation)
                except ValueError:
                    pass
        return self.get_state()

    @staticmethod
    def _with_stream_warning(result, payload):
        if result and 'fen' in payload:
            result['position_facts'] = list(result.get('position_facts') or []) + [
                'Bei einem Streamstart mitten in der Partie sind Rochaderechte/En-passant oft unbekannt. Stockfish-Varianten können dadurch eingeschränkt sein.'
            ]
            result['brief'] = make_brief(result)
        return result

    def _analysis_worker(self):
        while True:
            self.analysis_event.wait()
            self.analysis_event.clear()
            with self.lock:
                job = self.analysis_job
            if job is None:
                continue
            revision, payload = job
            fallback_used = False
            try:
                result = analyse_position(payload)
                if (payload.get('analysis_source') == 'allie'
                        and (not result or not result.get('moves')
                             or result.get('allie_skip_reason'))):
                    fallback_payload = dict(payload)
                    fallback_payload['analysis_source'] = 'stockfish'
                    fallback_payload['preview'] = False
                    result = analyse_position(fallback_payload)
                    fallback_used = True
                error = None
            except Exception as exc:  # noqa: BLE001 - worker errors are returned in session state
                if payload.get('analysis_source') == 'allie':
                    try:
                        fallback_payload = dict(payload)
                        fallback_payload['analysis_source'] = 'stockfish'
                        fallback_payload['preview'] = False
                        result = analyse_position(fallback_payload)
                        fallback_used = True
                        error = None
                    except Exception as fallback_exc:  # noqa: BLE001
                        result, error = None, str(fallback_exc)[:220]
                else:
                    result, error = None, str(exc)[:220]
            with self.lock:
                if not self.state['running'] or revision != self.generation:
                    continue
                result = self._with_stream_warning(result, payload)
                if result is not None:
                    result.update({
                        'session_id': payload.get('session_id'),
                        'generation': revision,
                        'analysis_key': payload.get('analysis_key', ''),
                        'history_complete': bool(payload.get('history_complete')),
                        'turn_verified': bool(payload.get('turn_verified')),
                        'render_revision': self.state.get('render_revision', 0),
                    })
                self.state['result'] = result
                self.state['analysing'] = False
                if error:
                    self.failed_key = ('pgn', payload['pgn']) if 'pgn' in payload else ('fen', payload.get('fen', ''))
                    self.state['message'] = 'Analysefehler: ' + error
                elif fallback_used:
                    reason = (result or {}).get('allie_skip_reason') or 'Allie nicht verfügbar'
                    self.state['message'] = 'Stockfish-Fallback aktiv · ' + str(reason)[:140]
                elif not self.state['history_complete']:
                    self.state['message'] = 'Stockfish aktuell · Allie benötigt die Zugfolge ab Zug 1'
                else:
                    self.state['message'] = 'Allie aktuell · Stockfish nur als Fallback'
