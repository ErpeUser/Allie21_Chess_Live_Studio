"""Offline opening lookup, cautious chess observations and optional Stockfish analysis.

Opening names come from the bundled public-domain lichess-org/chess-openings TSV files.
All explanations are transparent heuristics;
the objective candidate lines come from a real UCI Stockfish executable when available.
"""
from __future__ import annotations

import csv
import functools
import io
import os
from pathlib import Path
import shutil
import threading
import atexit
from typing import Any
from config import CONFIG

import chess
import chess.pgn
import chess.engine

BASE = Path(__file__).resolve().parent

OPENING_OPTIONS = {
    'white': {
        'grob': ('Grob Gambit', ('g2g4', 'd7d5', 'f1g2')),
        'vienna': ('Wiener Gambit', ('e2e4', 'e7e5', 'b1c3', 'b8c6', 'f2f4')),
        'danish': ('Dänisches Gambit', ('e2e4', 'e7e5', 'd2d4', 'e5d4', 'c2c3')),
    },
    'black': {
        'englund': ('Englund Gambit', ('d2d4', 'e7e5')),
        'budapest': ('Budapester Gambit', ('d2d4', 'g8f6', 'c2c4', 'e7e5')),
        'alekhine': ('Aljechin-Verteidigung', ('e2e4', 'g8f6')),
    },
}
DEFAULT_OPENINGS = {'white': 'grob', 'black': 'englund'}


def standard_repertoire(side: str, selection: str | None = None) -> dict[str, str]:
    """Return the selected human repertoire without changing Allie's model."""
    normalized = str(side).lower()
    options = OPENING_OPTIONS.get(normalized)
    if not options:
        raise ValueError('side must be white or black')
    key = str(selection or DEFAULT_OPENINGS[normalized]).lower()
    if key not in options:
        key = DEFAULT_OPENINGS[normalized]
    names = [name for option, (name, _line) in options.items() if option != key]
    return {'primary': options[key][0], 'alternative': names[0],
            'additional': ' · '.join(names[1:]), 'selection': key}


def repertoire_move_for(moves: list[str], side: str, selection: str | None = None) -> str | None:
    """Return the next move of the primary/alternative line, if history matches."""
    normalized = str(side).lower()
    options = OPENING_OPTIONS.get(normalized)
    if not options:
        return None
    history = tuple(moves)
    key = str(selection or DEFAULT_OPENINGS[normalized]).lower()
    ordered = [key] + [option for option in options if option != key]
    for option in ordered:
        line = options[option][1]
        if len(history) < len(line) and line[:len(history)] == history:
            return line[len(history)]
    return None

def epd_key(board: chess.Board) -> str:
    return board.epd(en_passant='legal')


def _position_from_pgn(pgn: str) -> tuple[chess.Board, int] | None:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None or game.errors:
        return None
    board = game.end().board()
    return board, board.ply()


@functools.lru_cache(maxsize=1)
def opening_indexes() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Parse each opening only once. Exact EPD and cautious placement fallback."""
    rows = []
    for file in sorted((BASE / 'openings').glob('?.tsv')):
        with file.open(encoding='utf-8-sig', newline='') as handle:
            rows.extend((x['eco'], x['name'], x['pgn']) for x in csv.DictReader(handle, delimiter='\t')
                        if x.get('eco') and x.get('name') and x.get('pgn'))
    epds: dict[str, dict[str, Any]] = {}
    placements: dict[str, dict[str, Any]] = {}
    for eco, name, pgn in rows:
        try:
            parsed = _position_from_pgn(pgn)
            if parsed is None:
                continue
            board, ply = parsed
            item = {'eco': eco, 'name': name, 'ply': ply}
            key = epd_key(board)
            if key not in epds or len(name) > len(epds[key]['name']):
                epds[key] = item
            placement = board.board_fen()
            if placement not in placements or ply > placements[placement]['ply']:
                placements[placement] = item
        except (ValueError, AssertionError):
            continue
    return epds, placements


def opening_book():
    return opening_indexes()[0]


def placement_opening_book():
    return opening_indexes()[1]


def opening_for_position(board: chess.Board, moves: list[str]) -> dict[str, Any] | None:
    book = opening_book()
    lookup = board.copy(stack=False)
    match = book.get(epd_key(lookup))
    if match:
        return {**match, 'source': 'history' if moves else 'position'}
    if not moves:
        fallback = placement_opening_book().get(board.board_fen())
        return {**fallback, 'source': 'position'} if fallback else None
    # The most recent named position along the actual move sequence.
    lookup = chess.Board()
    best = None
    for uci in moves:
        lookup.push_uci(uci)
        match = book.get(epd_key(lookup))
        if match:
            best = match
    return {**best, 'source': 'history'} if best else None


OPENING_IDEAS = [
    ('Sicilian', 'Asymmetrische Bauernstruktur; häufig Gegenangriff auf der Damenflügel- oder c-Linie.'),
    ('French', 'Der Bauer auf e6 stützt d5; der weißfeldrige Läufer von Schwarz braucht oft einen Entwicklungsplan.'),
    ('Caro-Kann', 'Solide Bauernbasis; Schwarz versucht häufig, den weißfeldrigen Läufer vor ...e6 zu entwickeln.'),
    ('Ruy Lopez', 'Weiß erzeugt langfristigen Druck auf e5 und nutzt häufig die Springer- und Läufermanöver.'),
    ('Italian', 'Früher Figurenaufbau und Druck auf f7; der richtige Zeitpunkt für d4 ist häufig entscheidend.'),
    ('Scandinavian', 'Schwarz greift das Zentrum sofort an; Weiß gewinnt oft Entwicklungstempo gegen die Dame.'),
    ('Queen\'s Gambit', 'Konflikt um d5 und c4; Raumvorteil und zentrale Bauernstruktur sind wichtige Themen.'),
    ('London', 'Solider Aufbau; üblich sind Läufer f4, Springer f3 und der Vorstoß e3/c3.'),
    ('Nimzowitsch Defense', 'Schwarz entwickelt flexibel nach c6 und hält ...e5 sowie ...d5 offen, legt sich aber noch nicht auf eine feste Bauernstruktur fest.'),
    ('Nimzo', 'Schwarz kämpft gegen das Zentrum, oft über die Fesselung des Springers c3.'),
    ('King\'s Indian', 'Schwarz lässt oft zunächst Raum im Zentrum zu und sucht später Bauernhebel bzw. Königsflügelspiel.'),
    ('Catalan', 'Läufer auf g2 übt Druck über die lange Diagonale aus; d4 und c4 strukturieren das Zentrum.'),
    ('English', 'Flexible Bauernstrukturen; viele Zugumstellungen in d4- oder umgekehrte Sizilianisch-Stellungen.'),
    ('Dutch', 'Schwarz kontrolliert e4 über ...f5, schwächt aber den Königsflügel.'),
    ('Petrov', 'Symmetrisches Zentrum; präzise Entwicklung und Abtauschreihenfolgen sind typisch.'),
    ('Pirc', 'Schwarz fianchettiert den Königsläufer und versucht das weiße Zentrum später anzugreifen.'),
    ('Slav', 'Schwarz stützt d5 mit ...c6 und behält häufig den weißfeldrigen Läufer beweglich.'),
    ('Scotch', 'Weiß öffnet das Zentrum früh mit d4; Entwicklungstempo und zentrale Taktik sind wichtig.'),
    ('Reti', 'Flexibler Entwicklungsaufbau, oft Druck auf das Zentrum aus der Ferne.'),
]


def opening_note(info: dict[str, Any] | None) -> str | None:
    if not info:
        return None
    for key, note in OPENING_IDEAS:
        if key.lower() in info['name'].lower():
            return note
    return 'Eröffnungsname per Position zugeordnet; konkrete Pläne hängen von Bauernstruktur und Figurenstellung ab.'


PIECE_DE = {
    chess.PAWN: 'Bauer', chess.KNIGHT: 'Springer', chess.BISHOP: 'Läufer',
    chess.ROOK: 'Turm', chess.QUEEN: 'Dame', chess.KING: 'König',
}
PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def position_facts(board: chess.Board) -> list[str]:
    facts: list[str] = []
    material = {c: sum(len(board.pieces(piece, c)) * value for piece, value in PIECE_VALUE.items())
                for c in (chess.WHITE, chess.BLACK)}
    delta = material[chess.WHITE] - material[chess.BLACK]
    if delta:
        facts.append(f'Materialbilanz (vereinfachte Zählung): {"Weiß" if delta > 0 else "Schwarz"} +{abs(delta)} Punkte.')
    else:
        facts.append('Materiell ausgeglichen (vereinfachte Zählung).')

    if board.is_check():
        facts.append('Der am Zug befindliche König steht im Schach: Nur legale Antworten sind möglich.')
    side = board.turn
    enemy = not side
    exposed = []
    for square, piece in board.piece_map().items():
        if piece.color != side or piece.piece_type == chess.KING:
            continue
        if board.is_attacked_by(enemy, square) and not board.is_attacked_by(side, square):
            exposed.append((PIECE_VALUE.get(piece.piece_type, 0), f'{PIECE_DE[piece.piece_type]} auf {chess.square_name(square)}'))
    exposed.sort(reverse=True)
    if exposed:
        facts.append('Möglicherweise ungedeckte angegriffene Figur(en): ' + ', '.join(p for _, p in exposed[:2]) + '. Nur ein geometrischer Hinweis, kein Verlustbeweis.')

    pinned = []
    for square, piece in board.piece_map().items():
        if piece.color == side and piece.piece_type not in (chess.PAWN, chess.KING):
            if board.is_pinned(side, square):
                pinned.append(f'{PIECE_DE[piece.piece_type]} {chess.square_name(square)}')
    if pinned:
        facts.append('An den König gefesselt: ' + ', '.join(pinned[:2]) + '.')

    if board.fullmove_number <= 11:
        home = {chess.WHITE: (chess.B1, chess.G1, chess.C1, chess.F1),
                chess.BLACK: (chess.B8, chess.G8, chess.C8, chess.F8)}
        unmoved = sum(1 for sq in home[side] if (p := board.piece_at(sq)) and p.color == side and p.piece_type in (chess.KNIGHT, chess.BISHOP))
        if unmoved >= 2:
            facts.append('Entwicklung: Mehrere Leichtfiguren stehen noch auf ihren Ausgangsfeldern.')
    return facts[:5]


def find_stockfish() -> str | None:
    env = os.environ.get('STOCKFISH_PATH', CONFIG['stockfish_path']).strip().strip('\"')
    if env:
        return env if Path(env).is_file() else None
    for path in [BASE / 'stockfish.exe', *(BASE / 'engines').glob('stockfish*.exe')]:
        if path.is_file() and (os.name == 'nt' or os.access(path, os.X_OK)):
            return str(path)
    return shutil.which('stockfish')


_ENGINE_LOCK = threading.RLock()
_ENGINE: chess.engine.SimpleEngine | None = None
_ENGINE_BINARY: str | None = None


def _close_stockfish():
    global _ENGINE, _ENGINE_BINARY
    with _ENGINE_LOCK:
        if _ENGINE is not None:
            try:
                _ENGINE.quit()
            except Exception:
                pass
        _ENGINE, _ENGINE_BINARY = None, None


atexit.register(_close_stockfish)


def _get_stockfish(binary: str) -> chess.engine.SimpleEngine:
    global _ENGINE, _ENGINE_BINARY
    # Called under _ENGINE_LOCK; one UCI process reused for every position.
    if _ENGINE is not None and _ENGINE_BINARY != binary:
        _close_stockfish()
    if _ENGINE is None:
        engine = chess.engine.SimpleEngine.popen_uci(binary, timeout=20)
        options = {}
        for key, wanted in (('Threads', CONFIG['stockfish_threads']),
                            ('Hash', CONFIG['stockfish_hash_mb'])):
            if key in engine.options:
                meta = engine.options[key]
                try:
                    options[key] = max(meta.min or 1, min(meta.max or 100000, int(wanted)))
                except (TypeError, ValueError):
                    pass
        if options:
            engine.configure(options)
        _ENGINE, _ENGINE_BINARY = engine, binary
    return _ENGINE


def stockfish_lines(
    board: chess.Board,
    limit_seconds: float = 0.7,
    root_moves: list[str] | None = None,
) -> dict[str, Any]:
    binary = find_stockfish()
    if not binary:
        return {'available': False, 'error': 'Stockfish fehlt. START_HIER.bat richtet ihn automatisch ein.'}
    limit_seconds = max(0.15, min(12.0, float(limit_seconds)))
    constrained: list[chess.Move] | None = None
    if root_moves:
        constrained = []
        for uci in dict.fromkeys(root_moves):
            try:
                move = chess.Move.from_uci(uci)
            except ValueError:
                continue
            if move in board.legal_moves:
                constrained.append(move)
        if not constrained:
            return {'available': False, 'error': 'Keine legalen Allie-Kandidaten für Stockfish.'}
    try:
        with _ENGINE_LOCK:
            engine = _get_stockfish(binary)
            infos = engine.analyse(
                board,
                chess.engine.Limit(time=limit_seconds),
                multipv=len(constrained) if constrained else 3,
                root_moves=constrained,
            )
        if not isinstance(infos, list):
            infos = [infos]
        lines: list[dict[str, Any]] = []
        for info in infos:
            pv = info.get('pv') or []
            if not pv:
                continue
            score = info.get('score')
            pov = score.pov(board.turn) if score else None
            mate = pov.mate() if pov else None
            centipawns = pov.score() if pov else None
            label = (f'Matt {mate:+d}' if mate is not None else
                     f'{centipawns / 100:+.2f}' if centipawns is not None else '?')
            try:
                pv_san = board.variation_san(pv[:8])
                first_san = board.san(pv[0])
            except (ValueError, AssertionError):
                continue
            lines.append({'san': first_san, 'uci': pv[0].uci(), 'score': label,
                          'score_cp': centipawns, 'depth': info.get('depth'), 'variation': pv_san})
        return {
            'available': True,
            'engine': 'Stockfish',
            'scope': 'allie-candidates' if constrained else 'position',
            'lines': lines,
        }
    except (OSError, chess.engine.EngineError, TimeoutError, ValueError) as exc:
        _close_stockfish()
        return {'available': False, 'error': f'Stockfish-Fehler: {str(exc)[:160]}'}


def describe_candidate(board: chess.Board, uci: str) -> str:
    """Cautious, deterministic German coaching note for one *legal* move.

    It describes motifs, not a proof that a move is objectively good.
    """
    try:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            return 'Zug ist in dieser Stellung nicht legal.'
    except ValueError:
        return 'Ungültiger Zug.'
    piece = board.piece_at(move.from_square)
    if piece is None:
        return 'Unbekannte Figur.'
    reasons = []
    if board.is_castling(move):
        reasons.append('Rochade: Königssicherheit und Verbindung der Türme')
    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        victim_name = PIECE_DE.get(victim.piece_type, 'Bauer') if victim else 'Bauer (en passant)'
        reasons.append(f'Schlagzug: nimmt {victim_name}')
    if board.gives_check(move):
        reasons.append('setzt den gegnerischen König unter Schach')
    if move.promotion:
        reasons.append('Bauernumwandlung')
    if piece.piece_type in (chess.BISHOP, chess.KNIGHT) and chess.square_rank(move.from_square) in (0, 7):
        reasons.append('entwickelt eine Leichtfigur')
    if piece.piece_type == chess.PAWN and chess.square_name(move.to_square) in ('d4', 'e4', 'd5', 'e5'):
        reasons.append('besetzt ein zentrales Feld')
    if piece.piece_type == chess.ROOK:
        reasons.append('aktiviert einen Turm')
    if piece.piece_type == chess.QUEEN and board.fullmove_number <= 7:
        reasons.append('früher Damenzug: auf Entwicklungstempo achten')
    if not reasons:
        reasons.append('verbessert die Figurenkoordination oder verändert die Bauernstruktur; konkrete Fortsetzung prüfen')
    return '; '.join(reasons[:3]).capitalize() + '.'


def make_brief(result: dict[str, Any]) -> list[str]:
    """Concise display-ready facts; never dress Stockfish scores up as probabilities."""
    if result.get('plan_messages'):
        return [str(message) for message in result['plan_messages'][:7]]
    brief: list[str] = []
    opening = result.get('opening')
    if opening:
        label = f"{opening.get('name', 'Eröffnung')} ({opening.get('eco', '?')})"
        if opening.get('source') == 'position':
            label += ' [Stellungsabgleich, kein vollständiges PGN]'
        brief.append('Eröffnung: ' + label)
        if opening.get('idea'):
            brief.append('Plan: ' + str(opening['idea']))
    else:
        brief.append('Eröffnung: noch nicht eindeutig zuordenbar.')

    candidates = result.get('moves') or []
    if candidates:
        for idx, move in enumerate(candidates[:2]):
            brief.append(f"Allie 2.1, Zug {idx + 1}: {move['san']} · {move['probability'] * 100:.1f} % menschliche Zugwahl")
        reply = (result.get('opponent_moves') or [])[:1]
        if reply:
            brief.append(f"Wahrscheinlichste Antwort auf Wahl 1: {reply[0]['san']} · {reply[0]['probability'] * 100:.1f} %")
    else:
        lines = (result.get('stockfish') or {}).get('lines') or []
        for idx, line in enumerate(lines[:2]):
            brief.append(f"Stockfish, Variante {idx + 1}: {line.get('san')} · Bewertung {line.get('score')}")

    warning = (result.get('tactical_warnings') or [])[:1]
    facts = (result.get('position_facts') or [])[:1]
    if warning:
        brief.append('Gefahr: ' + str(warning[0]))
    elif facts:
        brief.append('Stellung: ' + str(facts[0]))
    if result.get('allie_skip_reason'):
        brief.append('Allie derzeit nicht verfügbar: vollständige Zuggeschichte ab Zug 1 erforderlich oder Modellfehler.')
    return brief[:7]
