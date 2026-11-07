"""One latest-only video analysis worker; browser handles window/tab capture and playback.

No mss, native Win32 hooks, persistent screenshot files, mouse automation, or
video uploads. Only small JPEG frames are passed to localhost for chessvision.
"""
from __future__ import annotations
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from threading import Event, RLock, Thread
import json
import time

from allie_local_server import analyse_position, merge_results
from chess_extras import make_brief
from config import CONFIG, parse_time_control
from position_tracker import PositionTracker
from vision import BoardVision

MAX_JPEG = 3_500_000
class LiveSession:
    def __init__(self):
        self.lock = RLock()
        self.engine_event = Event()
        self.allie_event = Event()
        self.tracker = PositionTracker()
        self.vision = None  # loaded on first frame, not at server startup
        self.generation = 0
        self.session_id = 0
        self.engine_job = None
        self.allie_job = None
        self.failed_key = None
        self.settings = {}
        self.stable_placement = None
        self.stable_count = 0
        self.unmatched_frames = 0
        self.state = {}
        self._reset_state(False)
        Thread(target=self._engine_worker, name='stockfish-analysis', daemon=True).start()
        Thread(target=self._allie_worker, name='allie-analysis', daemon=True).start()

    def _reset_state(self, running):
        recommendations_enabled = bool(self.settings.get('recommendations_enabled', True))
        self.state = {'running': running, 'message': ('Bereit – Fenster oder Tab freigeben' if running else 'Gestoppt'),
                      'detection': None, 'result': None, 'analysing': False,
                      'engine_analysing': False, 'allie_analysing': False,
                      'history_complete': False, 'turn_verified': False,
                      'history_source': 'unknown', 'moves_seen': 0, 'model': CONFIG['model_id'],
                      'recommendations_enabled': recommendations_enabled}

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
            self.tracker = PositionTracker()
            self.vision = None
            self.engine_job = None
            self.allie_job = None
            self.failed_key = None
            self.engine_event.clear()
            self.allie_event.clear()
            self.stable_placement, self.stable_count = None, 0
            self.unmatched_frames = 0
            self.settings = {'white_elo': white, 'black_elo': black,
                             'player_side': player_side, 'time_control': tc,
                             'preview': CONFIG['preview_opponent_replies'],
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
            self.engine_job = None
            self.allie_job = None
            self.failed_key = None
            self.engine_event.clear()
            self.allie_event.clear()
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
            self.state['engine_analysing'] = False
            self.state['allie_analysing'] = False
            return
        board = self.tracker.board
        if not board or not self.tracker.turn_verified or not board.is_valid() or board.is_game_over():
            self.state['result'] = None
            self.state['analysing'] = False
            self.state['engine_analysing'] = False
            self.state['allie_analysing'] = False
            return
        # Never pass FEN as if it were full human history.
        field = 'pgn' if self.tracker.complete_history else 'fen'
        text = self.tracker.pgn_uci if self.tracker.complete_history else board.fen()
        payload = dict(self.settings)
        payload[field] = text
        job_key = (field, text)
        if job_key == self.failed_key:
            return
        self.generation += 1
        revision = self.generation
        wants_engine = True
        wants_allie = self.tracker.complete_history
        if wants_engine:
            engine_payload = dict(payload)
            engine_payload['analysis_source'] = 'stockfish'
            self.engine_job = (revision, engine_payload)
        else:
            self.engine_job = None
        if wants_allie:
            allie_payload = dict(payload)
            allie_payload['analysis_source'] = 'allie'
            self.allie_job = (revision, allie_payload)
        else:
            self.allie_job = None
        self.state['result'] = None
        self.state['engine_analysing'] = wants_engine
        self.state['allie_analysing'] = wants_allie
        self.state['analysing'] = wants_engine or wants_allie
        if wants_engine:
            self.engine_event.set()
        if wants_allie:
            self.allie_event.set()

    def set_recommendations(self, enabled: bool):
        """Immediately enable or suppress every live recommendation job."""
        with self.lock:
            if not self.state['running']:
                raise ValueError('Zuerst eine Quelle starten')
            enabled = bool(enabled)
            self.settings['recommendations_enabled'] = enabled
            self.state['recommendations_enabled'] = enabled
            self.generation += 1
            self.engine_job = None
            self.allie_job = None
            self.engine_event.clear()
            self.allie_event.clear()
            self.state['result'] = None
            self.state['analysing'] = False
            self.state['engine_analysing'] = False
            self.state['allie_analysing'] = False
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
        self.state['engine_analysing'] = False
        self.state['allie_analysing'] = False
        self.state['message'] = message
        self.generation += 1
        self.engine_job = None
        self.allie_job = None

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
                if source.format != 'JPEG' or max(source.size) > 2200 or min(source.size) < 200:
                    raise ValueError('Erwartet: JPEG zwischen 200 und 2200 Pixeln')
                frame = source.convert('RGB')
        except (UnidentifiedImageError, OSError) as exc:
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

    def _engine_worker(self):
        while True:
            self.engine_event.wait()
            self.engine_event.clear()
            with self.lock:
                job = self.engine_job
            if job is None:
                continue
            revision, payload = job
            try:
                result = analyse_position(payload)
                error = None
            except Exception as exc:
                result, error = None, str(exc)[:220]
            with self.lock:
                if not self.state['running'] or revision != self.generation:
                    continue
                result = self._with_stream_warning(result, payload)
                current = self.state.get('result')
                if result and current and (current.get('moves') or current.get('allie_skip_reason')):
                    result = merge_results(result, current)
                self.state['result'] = result
                self.state['engine_analysing'] = False
                self.state['analysing'] = self.state['allie_analysing']
                if error:
                    self.failed_key = ('pgn', payload['pgn']) if 'pgn' in payload else ('fen', payload.get('fen', ''))
                    self.state['message'] = 'Analysefehler: ' + error
                elif self.state['allie_analysing']:
                    self.state['message'] = 'Stockfish aktuell · Allie rechnet parallel ...'
                elif not self.state['history_complete']:
                    self.state['message'] = 'Stockfish aktuell · Allie benötigt die Zugfolge ab Zug 1'
                else:
                    self.state['message'] = 'Analyse aktuell'
    def _allie_worker(self):
        while True:
            self.allie_event.wait()
            self.allie_event.clear()
            with self.lock:
                job = self.allie_job
            if job is None:
                continue
            revision, payload = job
            try:
                result = analyse_position(payload)
                error = None
            except Exception as exc:
                result, error = None, str(exc)[:220]
            with self.lock:
                if not self.state['running'] or revision != self.generation:
                    continue
                current = self.state.get('result')
                if result:
                    result = merge_results(current, result)
                    result['brief'] = make_brief(result)
                    self.state['result'] = result
                self.state['allie_analysing'] = False
                self.state['analysing'] = self.state['engine_analysing']
                if error:
                    self.state['message'] = 'Allie-Analysefehler: ' + error
                elif result and result.get('allie_skip_reason'):
                    self.state['message'] = result['allie_skip_reason']
                elif self.state['engine_analysing']:
                    self.state['message'] = 'Allie aktuell · Stockfish rechnet weiter ...'
                else:
                    self.state['message'] = 'Allie + Stockfish aktuell'
