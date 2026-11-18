"""Local-only Allie 2.1 chess training analysis endpoint.

Uses the real yimingzhang/allie-2.1 model; no Stockfish substitute or
hard-coded fake 'human move' distribution. Requires standard chess move history.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import threading
import time
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from typing import Any

import chess
import chess.pgn
from chess_extras import (
    adaptive_repertoire_candidates,
    describe_candidate,
    make_brief,
    opening_for_position,
    opening_note,
    position_facts,
    standard_repertoire,
    stockfish_lines,
    tactical_hints,
)
from config import MODEL_ID, MODEL_REVISION, parse_port, time_profile

HOST = "127.0.0.1"
PORT = parse_port(os.environ.get("ALLIE_PORT", "8765"))
MODEL_NAME = MODEL_ID
BACKEND_DIR = Path(__file__).resolve().parent
VENDOR_BASE = BACKEND_DIR / "vendor"
if BACKEND_DIR.parent.parent.name == "source":
    VENDOR_BASE = BACKEND_DIR.parents[2] / "generated" / "dependencies" / "vendor"
    vendor_package_root = VENDOR_BASE.parent
    if str(vendor_package_root) not in sys.path:
        sys.path.insert(0, str(vendor_package_root))
VENDOR_DIR = VENDOR_BASE / "allie_model"
VENDOR_MANIFEST = VENDOR_BASE / "allie_model.sha256.csv"
_model = None
_ANALYSIS_CACHE: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
_ANALYSIS_CACHE_LOCK = threading.RLock()
_ANALYSIS_CACHE_TTL = 30.0
_ANALYSIS_CACHE_MAX = 24
_model_lock = threading.RLock()


def verify_vendor_integrity(
    vendor_dir: Path = VENDOR_DIR, manifest: Path = VENDOR_MANIFEST
) -> None:
    """Fail closed unless every vendored Python module matches its SHA-256 manifest."""
    if not manifest.is_file():
        raise RuntimeError(f"vendor manifest missing: {manifest}")
    try:
        with manifest.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, csv.Error) as exc:
        raise RuntimeError(f"vendor manifest unreadable: {manifest}") from exc
    expected = {str(row.get("path", "")): str(row.get("sha256", "")).lower() for row in rows}
    actual = {path.relative_to(vendor_dir).as_posix() for path in vendor_dir.rglob("*.py")}
    if set(expected) != actual:
        missing = sorted(set(expected) - actual)
        extra = sorted(actual - set(expected))
        detail = ", ".join([*(f"missing {path}" for path in missing), *(f"unexpected {path}" for path in extra)])
        raise RuntimeError(f"vendor manifest file set mismatch: {detail}")
    for relative, expected_hash in expected.items():
        if not expected_hash or len(expected_hash) != 64:
            raise RuntimeError(f"invalid vendor hash for {relative}")
        path = vendor_dir / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected_hash:
            raise RuntimeError(f"vendor hash mismatch: {relative}")


def _register_local_allie_classes() -> None:
    """Register the reviewed vendored classes for Transformers' non-remote loader."""
    import transformers

    AutoConfig = getattr(transformers, "AutoConfig", None)
    AutoModel = getattr(transformers, "AutoModel", None)
    if AutoConfig is None or AutoModel is None:
        # Lightweight test doubles may expose only AutoModel; real Transformers
        # installations always provide AutoConfig for the registration below.
        return
    from vendor.allie_model.configuration_allie import AllieConfig
    from vendor.allie_model.modeling_allie import AllieModel

    try:
        AutoConfig.register(AllieConfig.model_type, AllieConfig)
    except ValueError:
        pass
    try:
        AutoModel.register(AllieConfig, AllieModel)
    except ValueError:
        pass


def _safe_error_id(scope: str, exc: BaseException) -> str:
    """Log the diagnostic detail locally while returning only an opaque id."""
    digest = hashlib.sha256(
        f"{scope}|{type(exc).__name__}|{exc}".encode("utf-8", "replace")
    ).hexdigest()[:12]
    print(f"{scope} ({digest}):", repr(exc), flush=True)
    return digest


def get_model():
    global _model
    with _model_lock:
        if _model is None:
            verify_vendor_integrity()
            _register_local_allie_classes()
            from transformers import AutoModel
            print(f"Loading actual model {MODEL_NAME} (CPU int8 weights use about 9.8 GB)...", flush=True)
            options = {"active_experts": 8}
            if sys.platform == "win32":
                # Allie's native Rust engine is officially Linux x86-64 only.
                # Avoid a failed probe and use the supported Windows backend.
                options["backend"] = "torch"
            _model = AutoModel.from_pretrained(
                MODEL_NAME,
                revision=MODEL_REVISION,
                trust_remote_code=False,
                local_files_only=True,
                **options,
            )
        return _model


def parse_history(raw: str) -> tuple[list[str], chess.Board, list[float | None]]:
    """Convert standard PGN or SAN/UCI moves into canonical UCI history."""
    raw = raw.strip()
    board = chess.Board()
    if not raw:
        return [], board, []
    if len(raw) > 40000:
        raise ValueError("PGN is too long")
    if " / " in raw and re.search(r"\b[wb]\b", raw):
        raise ValueError("FEN-only positions are not supported. Paste the moves from the start.")
    if "[" in raw or re.search(r"\b\d+\s*\.", raw):
        stream = io.StringIO(raw)
        game = chess.pgn.read_game(stream)
        if not game:
            raise ValueError("Cannot read PGN")
        if game.errors:
            raise ValueError(f"PGN invalid: {game.errors[0]}")
        if game.board().fen() != chess.STARTING_FEN:
            raise ValueError("Allie 2.1 requires standard chess from the initial position")
        if game.headers.get("Variant", "Standard") not in ("Standard", "Chess", ""):
            raise ValueError("This variant is not supported by the Allie 2.1 model")
        # ``read_game`` intentionally consumes only one game.  Silently
        # analysing the first game from a pasted multi-game PGN is dangerous:
        # the displayed result can belong to a different game than the user
        # intended.  Reject a second parsed game explicitly.
        second = chess.pgn.read_game(stream)
        if second is not None:
            raise ValueError("Multiple games are not supported; paste one PGN")
        history: list[str] = []
        clocks: list[float | None] = []
        for node in game.mainline():
            history.append(node.move.uci())
            clocks.append(node.clock())
            board.push(node.move)
        return history, board, clocks

    moves = []
    for word in raw.replace("\n", " ").split():
        if word in ("*", "1-0", "0-1", "1/2-1/2"):
            continue
        try:
            move = chess.Move.from_uci(word)
            if move not in board.legal_moves:
                raise ValueError("not legal")
        except ValueError:
            try:
                move = board.parse_san(word)
            except ValueError as exc:
                raise ValueError(f"Unrecognized move '{word}'. Paste a valid PGN.") from exc
        board.push(move)
        moves.append(move.uci())
    return moves, board, [None] * len(moves)


def validate_clock_history(value: object, move_count: int) -> list[float | None]:
    """Validate trusted remaining-clock samples without inventing timings."""
    if not isinstance(value, list) or len(value) != move_count:
        raise ValueError('clock_history muss exakt so lang wie die Zugfolge sein')
    result: list[float | None] = []
    for item in value:
        if item is None:
            result.append(None)
            continue
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(float(item)):
            raise ValueError('clock_history enthält keine gültige Uhrzeit')
        seconds = float(item)
        if seconds < 0 or seconds > 604800:
            raise ValueError('clock_history enthält eine unrealistische Uhrzeit')
        result.append(seconds)
    return result


def describe_move(board: chess.Board, uci: str, probability: float) -> dict[str, Any]:
    try:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            raise ValueError("illegal")
    except ValueError:
        raise ValueError(f"Model returned non-legal move: {uci}")
    if not math.isfinite(float(probability)) or not 0 <= float(probability) <= 1:
        raise ValueError("Allie returned an invalid probability")
    flags = []
    if board.is_capture(move):
        flags.append("Schlagzug")
    if board.gives_check(move):
        flags.append("Schach")
    after = board.copy(stack=False)
    after.push(move)
    if after.is_checkmate():
        flags.append("Schachmatt")
    if after.is_stalemate():
        flags.append("Patt")
    return {
        "uci": uci,
        "san": board.san(move),
        "probability": round(float(probability), 7),
        "flags": flags,
        "explanation": describe_candidate(board, uci),
    }


def _candidate_pressure(board: chess.Board, uci: str) -> tuple[int, int, int, int, int]:
    """Measure actual board tactics without replacing a model probability."""
    after = board.copy(stack=False)
    move = after.push_uci(uci)
    own_mate = after.is_checkmate()
    opponent_can_mate = False
    if not own_mate:
        for reply in after.legal_moves:
            probe = after.copy(stack=False)
            probe.push(reply)
            if probe.is_checkmate():
                opponent_can_mate = True
                break
    attacker = not after.turn
    king = after.king(after.turn)
    ring = chess.SquareSet(chess.BB_KING_ATTACKS[king]) if king is not None else ()
    attacked = sum(after.is_attacked_by(attacker, square) for square in ring)
    # A pinned piece does not earn a claim of a direct material threat.
    valuable = 0
    if not after.is_pinned(attacker, move.to_square):
        values = {chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
        for square in after.attacks(move.to_square):
            target = after.piece_at(square)
            if target is not None and target.color == after.turn:
                valuable += values.get(target.piece_type, 0)
    return int(own_mate), int(not opponent_can_mate), int(after.is_check()), attacked, valuable


def rank_allie_candidates(
    board: chess.Board, candidates: list[dict[str, Any]], play_style: str
) -> list[dict[str, Any]]:
    """Rank our moves; opponent predictions retain their original distribution."""
    if play_style == 'normal':
        return candidates
    if play_style not in ('aggressive', 'ragebait'):
        raise ValueError('play_style must be normal, aggressive or ragebait')

    def pressure(item: tuple[int, dict[str, Any]]) -> tuple:
        index, candidate = item
        mate, survives, check, ring, valuable = _candidate_pressure(board, candidate['uci'])
        probability = float(candidate.get('probability', 0.0))
        if play_style == 'ragebait':
            return (mate, survives, int(bool(candidate.get('repertoire'))),
                    check, valuable, ring, probability, -index)
        return mate, survives, check, ring, probability, -index

    return [candidate for _, candidate in sorted(enumerate(candidates), key=pressure, reverse=True)]


def _repertoire_context(
    moves: list[str], side: str, selection: str | None,
    probabilities: dict[str, float] | None = None, *, allow_book: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    repertoire: dict[str, Any] = standard_repertoire(side, selection)
    repertoire.update({'active_selection': None, 'active_primary': None,
                       'compatible_openings': [], 'applied': False,
                       'expected_move': None, 'expected_san': None,
                       'adaptation_reason': 'Keine passende Buchfortsetzung; freie Stellungsanalyse.'})
    if not allow_book:
        repertoire['adaptation_reason'] = 'Eröffnungsabgleich benötigt einen verifizierten vollständigen Zugverlauf.'
        return repertoire, []
    options = adaptive_repertoire_candidates(moves, side, repertoire['selection'])
    supported = [option for option in options if probabilities is not None
                 and option['uci'] in probabilities
                 and math.isfinite(float(probabilities[option['uci']]))
                 and 0 <= float(probabilities[option['uci']]) <= 1]
    chosen = max(supported, key=lambda option: (
        bool(option['preferred']), int(option['matched_plies']), option['match'] == 'exact',
        float((probabilities or {})[option['uci']]),
    )) if supported else (options[0] if options else None)
    if chosen is not None:
        repertoire['expected_move'] = chosen['uci']
        repertoire['expected_san'] = chosen['san']
        repertoire['compatible_openings'] = list(dict.fromkeys(
            option['primary'] for option in options if option['uci'] == chosen['uci']))
        if supported:
            repertoire['active_selection'] = chosen['selection']
            repertoire['active_primary'] = chosen['primary']
        else:
            repertoire['adaptation_reason'] = (
                f"Buchidee {chosen['san']} ist legal, aber kein verfügbarer Allie-Kandidat; freie Analyse.")
    return repertoire, supported


def _finish_repertoire(repertoire: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
    """Describe whether the possible book move actually became our main choice."""
    if not repertoire.get('active_selection'):
        return
    applied = bool(candidates and candidates[0]['uci'] == repertoire['expected_move'])
    repertoire['applied'] = applied
    active = repertoire['active_primary']
    if repertoire['active_selection'] == repertoire['selection']:
        reason = f"Gewähltes Repertoire: {active} · {repertoire['expected_san']}."
    else:
        reason = f"Angepasst: {repertoire['primary']} → {active} · {repertoire['expected_san']}."
    if len(repertoire['compatible_openings']) > 1:
        reason += ' Gemeinsamer Zug mehrerer passender Eröffnungen.'
    if not applied:
        reason += ' Der Buchzug bleibt eine Alternative; die aktuelle Empfehlung hat Vorrang.'
    repertoire['adaptation_reason'] = reason


def _own_move_candidates(
    board: chess.Board, moves: list[str], probabilities: dict[str, float],
    side: str, opening_selection: str | None, play_style: str, *, allow_book: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Select from actual inference, retaining rare supported repertoire moves."""
    repertoire, supported = _repertoire_context(
        moves, side, opening_selection, probabilities, allow_book=allow_book)
    choices = dict(list(probabilities.items())[:12 if play_style == 'ragebait' else 5])
    expected = repertoire['expected_move'] if repertoire['active_selection'] else None
    book_moves = [option['uci'] for option in supported] if play_style == 'ragebait' else [expected]
    for uci in book_moves:
        if uci is not None:
            choices[uci] = probabilities[uci]
    if play_style == 'ragebait':
        # Even a rare mate beyond the bounded ordinary pool must beat a prank.
        for uci, probability in probabilities.items():
            if uci in choices:
                continue
            after = board.copy(stack=False)
            after.push_uci(uci)
            if after.is_checkmate():
                choices[uci] = probability
    candidates = [describe_move(board, uci, probability) for uci, probability in choices.items()]
    for candidate in candidates:
        if candidate['uci'] == expected:
            candidate['repertoire'] = True
    candidates = rank_allie_candidates(board, candidates, play_style)
    if (play_style == 'ragebait' and candidates
            and not _candidate_pressure(board, candidates[0]['uci'])[1]):
        # Do not overlook a rare real escape when every ordinary candidate
        # allows mate in one. Add only the first supported safe escape.
        for uci, probability in probabilities.items():
            if uci not in choices and _candidate_pressure(board, uci)[1]:
                candidates.insert(0, describe_move(board, uci, probability))
                break
    if play_style != 'ragebait' and expected and candidates:
        match = next((move for move in candidates if move['uci'] == expected), None)
        if match and candidates[0]['probability'] - match['probability'] <= .18:
            # The soft book preference cannot undo mate/survival protection.
            best_tier = max(_candidate_pressure(board, move['uci'])[:2] for move in candidates)
            if _candidate_pressure(board, match['uci'])[:2] == best_tier:
                candidates = [match] + [move for move in candidates if move is not match]
    _finish_repertoire(repertoire, candidates)
    return candidates, repertoire


def safe_aggressive_order(
    candidates: list[dict[str, Any]], stockfish: dict[str, Any] | None,
    margin_cp: int = 150,
) -> list[dict[str, Any]]:
    """Keep aggressive king pressure from overriding a clear engine safety gap.

    Allie still supplies every candidate and its probability. Stockfish can
    demote a material gap or a forced mate loss and promote a forced mate win;
    missing engine lines retain their relative order.
    """
    if not candidates or not stockfish or not stockfish.get('available'):
        return candidates
    scores = {
        str(line.get('uci')): int(line['score_cp'])
        for line in stockfish.get('lines', [])
        if line.get('uci') and isinstance(line.get('score_cp'), int)
    }
    known = [scores[move['uci']] for move in candidates if move.get('uci') in scores]
    mates = {str(line.get('uci')): line['score_mate'] for line in stockfish.get('lines', [])
             if line.get('uci') and isinstance(line.get('score_mate'), int)}
    floor = max(known) - max(50, int(margin_cp)) if known else None
    wins, safe, unsafe = [], [], []
    for move in candidates:
        uci = move['uci']
        if 'Schachmatt' in (move.get('flags') or []) or mates.get(uci, 0) > 0:
            wins.append(move)
        elif (uci in mates and mates[uci] <= 0
              or floor is not None and uci in scores and scores[uci] < floor):
            unsafe.append(move)
        else:
            safe.append(move)
    return wins + safe + unsafe


def risk_weighted_premove(
    branches: list[tuple[float, list[dict[str, Any]]]], *, prefer_order: bool = False,
    branch_boards: list[chess.Board] | None = None,
) -> dict[str, Any] | None:
    """Pick one Allie move that survives the most likely alternative branches.

    Likelihood and coverage use only Allie's human move probabilities. An
    explicit own-move policy may choose by branch coverage and preference;
    that preference never becomes a probability or an invented engine score.
    """
    # A terminal branch still contributes its weight: no available reply is
    # not evidence that another branch's plan has universal coverage.
    branches = [(max(0.0, float(weight)), moves if prefer_order else moves[:5])
                for weight, moves in branches if prefer_order or moves]
    total_weight = sum(weight for weight, _ in branches)
    if total_weight <= 0:
        return None
    candidates: dict[str, dict[str, Any]] = {}
    for weight, moves in branches:
        seen: set[str] = set()
        for index, move in enumerate(moves):
            uci = move.get('uci')
            if not uci or uci in seen:
                continue
            seen.add(uci)
            item = candidates.setdefault(uci, {'move': move, 'weighted': 0.0,
                                               'covered': 0.0, 'preference': 0.0,
                                               'unsafe': False, 'mate_weight': 0.0})
            item['weighted'] += weight * max(0.0, float(move.get('probability', 0.0)))
            item['covered'] += weight
            item['preference'] += weight / (index + 1)
    if not candidates:
        return None
    if prefer_order and branch_boards:
        for uci, item in candidates.items():
            chess_move = chess.Move.from_uci(uci)
            for (weight, _branch), board in zip(branches, branch_boards, strict=True):
                if weight <= 0 or chess_move not in board.legal_moves:
                    continue
                mate, survives = _candidate_pressure(board, uci)[:2]
                item['unsafe'] = item['unsafe'] or not survives
                item['mate_weight'] += weight * mate
    def score(item):
        coverage = item['covered'] / total_weight
        likelihood = item['weighted'] / total_weight
        # A pre-move that disappears in another likely branch is materially
        # riskier than a normal recommendation, so coverage gets a strong penalty.
        if prefer_order:
            # Known immediate losses in any branch take precedence over a
            # mate chance in another. Tactical facts never change the actual
            # branch weights, conditional likelihood, or reported coverage.
            return (int(not item['unsafe']), item['mate_weight'] / total_weight,
                    coverage, item['preference'] / total_weight, likelihood)
        return likelihood - 0.65 * (1.0 - coverage), coverage, likelihood
    best = max(candidates.values(), key=score)
    likelihood, coverage = best['weighted'] / total_weight, best['covered'] / total_weight
    result = dict(best['move'])
    result.update({'probability': round(likelihood, 7), 'coverage': round(coverage, 4),
                   'risk': round(1.0 - coverage, 4), 'source': 'allie'})
    return result


def make_plan_messages(output: dict[str, Any]) -> list[str]:
    """Add information that is not already obvious from arrows and labels."""
    messages: list[str] = []
    unknown_history = (output.get('uncertainty') or {}).get('level') == 'warning'
    if unknown_history:
        messages.append('Verlauf unbekannt: Pfeile bleiben ausgeblendet; PGN ab Zug 1 importieren.')
    # Tactical bubbles are the most time-sensitive context and must remain
    # visible in the native HUD, which intentionally carries only two lines.
    for hint in (output.get('tactical_hints') or []):
        messages.append('⚡ ' + str(hint))
    for warning in (output.get('tactical_warnings') or []):
        if str(warning).startswith('Achtung:'):
            messages.append(str(warning))
            break
    repertoire = output.get('repertoire') or {}
    adaptation = str(repertoire.get('adaptation_reason') or '')
    if not unknown_history:
        if output.get('play_style') == 'ragebait':
            messages.append('Ragebait: provozierende Buchzüge und konkrete Drohungen; Matt geht vor. ' + adaptation)
        elif adaptation:
            messages.append(adaptation)
    selected = output.get('opening_selection') or {}
    white = selected.get('white') or {}
    black = selected.get('black') or {}
    if white.get('primary') and black.get('primary'):
        messages.append(f"Ausgewählte Eröffnungen · Weiß: {white['primary']} · Schwarz: {black['primary']}")
    if not unknown_history and output.get('move_count', 0) <= 2 and repertoire.get('primary'):
        messages.append(
            f"Standardrepertoire: {repertoire['primary']} · Alternative: {repertoire['alternative']}"
            f" · Weitere Option: {repertoire.get('additional', 'keine')}."
        )
    opening = output.get('opening') or {}
    if opening.get('name'):
        eco = f" ({opening['eco']})" if opening.get('eco') else ''
        text = f"Gespielt wird {opening['name']}{eco}."
        if opening.get('idea'):
            text += ' ' + opening['idea']
        messages.append(text)

    facts = output.get('position_facts') or []
    for fact in facts:
        # At the beginning, "material equal" adds no useful information.
        if fact.startswith('Materiell ausgeglichen') and output.get('move_count', 0) < 16:
            continue
        messages.append('Zur Stellung: ' + fact)
        if len(messages) >= 2:
            break

    opponent = output.get('opponent_moves') or []
    if opponent:
        first = opponent[0]
        engine_fallback = first.get('source') == 'stockfish'
        explanation = str(first.get('explanation') or '').strip()
        if explanation:
            prefix = 'Stockfish-Hinweis: ' if engine_fallback else 'Wahrscheinliche gegnerische Absicht: '
            messages.append(prefix + explanation)
        flags = first.get('flags') or []
        if 'Schachmatt' in flags:
            messages.append('Konkrete Gefahr: Der rote Hauptzug wäre matt.')
        elif 'Schach' in flags:
            messages.append('Konkrete Gefahr: Der rote Hauptzug kommt mit Schach und erzwingt eine Antwort.')
        elif 'Schlagzug' in flags:
            messages.append('Konkrete Gefahr: Der rote Hauptzug verändert sofort die Materiallage.')
        if len(opponent) > 1 and not engine_fallback:
            gap = float(first.get('probability', 0.0)) - float(opponent[1].get('probability', 0.0))
            if gap >= .18:
                messages.append('Spielverhalten: Allie sieht hier einen klaren gegnerischen Hauptplan statt vieler gleichwertiger Ideen.')
            elif gap <= .07:
                messages.append('Spielverhalten: Mehrere natürliche Pläne liegen eng beieinander; der Gegner ist hier schwer vorherzusagen.')

    premove = output.get('premove')
    if premove and float(premove.get('risk', 0.0)) >= .25:
        messages.append('Pre-Move-Risiko: Der blaue Plan hängt stark von der tatsächlichen Gegnerantwort ab; nicht blind ausführen.')
    for warning in (output.get('tactical_warnings') or [])[:1]:
        if warning not in messages:
            messages.append(warning)
    return messages[:6]


def _analyse_position_uncached(payload: dict[str, Any], model=None) -> dict[str, Any]:
    raw = payload.get("pgn", "")
    fen = payload.get("fen", "")
    if not isinstance(raw, str) or not isinstance(fen, str):
        raise TypeError("pgn and fen must be strings")
    if len(fen) > 200:
        raise ValueError("FEN is too long")
    if fen.strip() and raw.strip():
        raise ValueError('Bitte entweder PGN oder FEN angeben, nicht beide gleichzeitig.')
    moves, board, clocks = parse_history(raw)
    supplied_clocks = payload.get('clock_history')
    if supplied_clocks is not None:
        clocks = validate_clock_history(supplied_clocks, len(moves))
    fen_only = bool(fen.strip() and not raw.strip())
    if fen_only:
        try:
            board = chess.Board(fen.strip())
        except ValueError as exc:
            raise ValueError("Ungültige FEN: " + str(exc)) from exc
        if not board.is_valid():
            raise ValueError("FEN ist keine reguläre Standardschachstellung")
    if not board.is_valid():
        raise ValueError("Unplausible Schachstellung (Figuren/Zugrecht nicht konsistent)")
    if len(moves) >= 1014:
        raise ValueError("Too many half-moves for Allie 2.1")
    finished_game = board.is_game_over()
    last_move = None
    if finished_game and payload.get('review_finished', False) and moves:
        # End-of-game review: show the final decision BEFORE the last move.
        # The live tracker never requests this, since arrows must match the visible board.
        last_move = moves.pop()
        board.pop()
        clocks.pop()
    elif not board.legal_moves:
        # Automatic draws can still have legal analysis moves on the visible
        # board. Only mate/stalemate prevents current-position move arrows.
        raise ValueError('Partie beendet. Im PGN-Analysefeld die letzte Entscheidung auswerten (review_finished).')
    try:
        white_elo = int(payload.get("white_elo", 1950))
        black_elo = int(payload.get("black_elo", 1950))
    except (ValueError, TypeError) as exc:
        raise ValueError("Elo must be a whole number") from exc
    if not (600 <= white_elo <= 2800 and 600 <= black_elo <= 2800):
        raise ValueError("Elo must be between 600 and 2800")
    tc = str(payload.get("time_control", "180+2")).strip()
    mode, stockfish_budget = time_profile(tc)
    selection = str(payload.get('analysis_source', 'both'))
    if selection not in ('allie', 'stockfish', 'both'):
        raise ValueError('analysis_source must be allie, stockfish or both')
    play_style = str(payload.get('play_style', 'normal'))
    if play_style not in ('normal', 'aggressive', 'ragebait'):
        raise ValueError('play_style must be normal, aggressive or ragebait')

    opening = opening_for_position(board, moves)
    if opening:
        opening = {**opening, 'idea': opening_note(opening)}
    tactical = tactical_hints(board)
    if fen_only or payload.get('show_moves') is False:
        tactical = [f'Stellungs-Hinweis ohne Zugverlauf: {hint}' for hint in tactical]
    candidate_moves: list[dict[str, Any]] = []
    wdl = None
    expected_think_time = None
    prediction_top: list[dict[str, Any]] = []
    prediction_second: list[dict[str, Any]] = []
    premove_branches: list[tuple[float, list[dict[str, Any]]]] = []
    premove_boards: list[chess.Board] = []
    warnings: list[str] = []
    allie_skip_reason: str | None = None
    player_side = str(payload.get('player_side', 'white' if board.turn else 'black')).lower()
    if player_side not in ('white', 'black'):
        player_side = 'white' if board.turn else 'black'
    player_to_move = player_side == ('white' if board.turn else 'black')
    requested_opening = payload.get('opening_white' if player_side == 'white' else 'opening_black')
    allow_book = (not fen_only and payload.get('show_moves', True) is not False
                  and payload.get('history_complete', True) is not False
                  and payload.get('turn_verified', True) is not False)
    repertoire, _ = _repertoire_context(moves, player_side, requested_opening, allow_book=allow_book)
    opening_selection = {
        'white': standard_repertoire('white', payload.get('opening_white')),
        'black': standard_repertoire('black', payload.get('opening_black')),
    }
    if selection in ('allie', 'both'):
        if fen_only:
            allie_skip_reason = ('Allie 2.1 benötigt die Zugfolge ab Zug 1 und kann nur '
                                 'aus einem FEN-Brettbild keine verlässliche Vorhersage ableiten.')
        else:
            try:
                model = model if model is not None else get_model()
                with _model_lock:
                    result = model.analyze(moves, white_elo=white_elo, black_elo=black_elo,
                                           time_control=tc, clocks=clocks)
                    # Preserve the full real distribution until our selection
                    # can include supported book moves below the usual cutoff.
                    if player_to_move:
                        candidate_moves, repertoire = _own_move_candidates(
                            board, moves, result['moves'], player_side, requested_opening,
                            play_style, allow_book=allow_book)
                    else:
                        candidate_moves = [describe_move(board, uci, probability)
                                           for uci, probability in list(result['moves'].items())[:5]]
                    wdl = [round(float(x), 5) for x in result['wdl']] if result.get('wdl') is not None else None
                    if result.get('think_time') is not None:
                        expected_think_time = round(float(result['think_time']), 2)
            except Exception as exc:  # noqa: BLE001 - optional model boundary must fail soft
                error_id = _safe_error_id('Allie-Analyse fehlgeschlagen', exc)
                allie_skip_reason = (
                    'Allie 2.1 konnte nicht geladen oder ausgefuehrt werden '
                    f'(Fehler-ID {error_id}).'
                )
    sf = None
    if selection in ('stockfish', 'both'):
        roots = ([move['uci'] for move in candidate_moves]
                 if selection == 'both' and candidate_moves else None)
        sf = stockfish_lines(board, stockfish_budget, roots)
        if sf and sf.get('available'):
            scored = {item['uci']: item for item in sf.get('lines', [])}
            for move in candidate_moves:
                if evaluation := scored.get(move['uci']):
                    move.update({
                        'stockfish_score': evaluation.get('score'),
                        'stockfish_depth': evaluation.get('depth'),
                        'stockfish_variation': evaluation.get('variation'),
                        'stockfish_score_mate': evaluation.get('score_mate'),
                    })
            for item in sf.get('lines', []):
                item['explanation'] = describe_candidate(board, item['uci'])
            if player_to_move and play_style in ('aggressive', 'ragebait'):
                candidate_moves = safe_aggressive_order(
                    candidate_moves, sf, margin_cp=300 if play_style == 'ragebait' else 150)
                # Engine annotations cannot override a directly verified mate
                # or the available avoidance of an immediate opponent mate.
                candidate_moves = sorted(candidate_moves, key=lambda move:
                                         _candidate_pressure(board, move['uci'])[:2], reverse=True)
    if player_to_move:
        _finish_repertoire(repertoire, candidate_moves)

    # All root ordering is final before any dependent reply is generated.
    if candidate_moves and selection in ('allie', 'both') and payload.get('preview', True):
        try:
            with _model_lock:
                for index, choice in enumerate(candidate_moves[:1 if player_to_move else 2]):
                    after = board.copy(stack=False)
                    after.push_uci(choice['uci'])
                    if not after.legal_moves:
                        continue
                    reply_history = moves + [choice['uci']]
                    replies = model.predict(
                        reply_history, white_elo=white_elo, black_elo=black_elo,
                        time_control=tc, clocks=clocks + [None])
                    if player_to_move:
                        shown = [describe_move(after, uci, probability)
                                 for uci, probability in list(replies.items())[:3]]
                    else:
                        shown, reply_repertoire = _own_move_candidates(
                            after, reply_history, replies, player_side, requested_opening,
                            play_style, allow_book=allow_book)
                        if index == 0:
                            repertoire = reply_repertoire
                            repertoire['adaptation_reason'] = (
                                f"Nach {choice['san']}: " + repertoire['adaptation_reason'])
                    if index == 0:
                        prediction_top = shown
                        if player_to_move:
                            for legal_reply in after.legal_moves:
                                probe = after.copy(stack=False)
                                probe.push(legal_reply)
                                if probe.is_checkmate():
                                    warnings.append('Achtung: Gegner kann nach dieser Wahl sofort mattsetzen: ' + after.san(legal_reply))
                                    if len(warnings) >= 2:
                                        break
                            if not warnings and shown:
                                if 'Schach' in shown[0]['flags']:
                                    warnings.append('Die wahrscheinlichste Gegnerantwort setzt Schach: ' + shown[0]['san'])
                                if 'Schlagzug' in shown[0]['flags']:
                                    warnings.append('Die wahrscheinlichste Gegnerantwort schlaegt eine Figur: ' + shown[0]['san'])
                    else:
                        prediction_second = shown
                if player_to_move and prediction_top:
                    predicted_reply = prediction_top[0]
                    continuation_history = moves + [candidate_moves[0]['uci'], predicted_reply['uci']]
                    after_reply = board.copy(stack=False)
                    after_reply.push_uci(candidate_moves[0]['uci'])
                    after_reply.push_uci(predicted_reply['uci'])
                    if after_reply.legal_moves:
                        continuation = model.predict(
                            continuation_history, white_elo=white_elo, black_elo=black_elo,
                            time_control=tc, clocks=clocks + [None, None])
                        described, _ = _own_move_candidates(
                            after_reply, continuation_history, continuation, player_side,
                            requested_opening, play_style, allow_book=allow_book)
                        premove_branches.append((predicted_reply['probability'], described))
                        premove_boards.append(after_reply)
        except Exception as exc:  # noqa: BLE001 - optional prediction branch must fail soft
            error_id = _safe_error_id('Allie-Gegnerprognose fehlgeschlagen', exc)
            warnings.append('Allie-Gegnerprognose derzeit nicht verfuegbar ' f'(Fehler-ID {error_id}).')

    engine_moves = []
    if selection in ('stockfish', 'both') and sf and sf.get('available'):
        engine_moves = [{**item, 'source': 'stockfish'} for item in sf.get('lines', [])[:2]]
    if fen_only and not allie_skip_reason:
        allie_skip_reason = ('Allie wartet auf die vollständige Partiegeschichte; '
                             'bis dahin zeigt Stockfish die sicheren Stellungszüge.')

    if player_to_move:
        my_moves = candidate_moves[:2] or engine_moves
        opponent_moves = prediction_top[:2]
        premove = risk_weighted_premove(premove_branches, prefer_order=(
            play_style != 'normal' or any(branch and branch[0].get('repertoire')
                                         for _, branch in premove_branches)),
                                       branch_boards=premove_boards)
    else:
        opponent_moves = candidate_moves[:2] or engine_moves
        my_moves = prediction_top[:2]
        reply_branches = []
        if candidate_moves:
            reply_branches.append((candidate_moves[0]['probability'], prediction_top))
        if len(candidate_moves) > 1:
            reply_branches.append((candidate_moves[1]['probability'], prediction_second))
        for choice in candidate_moves[:2]:
            after = board.copy(stack=False)
            after.push_uci(choice['uci'])
            premove_boards.append(after)
        premove = risk_weighted_premove(reply_branches, prefer_order=(
            play_style != 'normal' or any(branch and branch[0].get('repertoire')
                                         for _, branch in reply_branches)),
                                       branch_boards=premove_boards)

    output = {
        'model': MODEL_NAME if selection in ('allie', 'both') and not fen_only and candidate_moves else None,
        'reviewed_finished_game': bool(last_move), 'final_played_move': last_move,
        'rating_white': white_elo, 'rating_black': black_elo,
        'mode': mode, 'play_style': play_style, 'time_control': tc, 'move_count': len(moves),
        'side_to_move': 'white' if board.turn else 'black', 'fen': board.fen(),
        'fen_only': fen_only, 'show_moves': bool(payload.get('show_moves', True)),
        'opening': opening, 'position_facts': position_facts(board),
        'moves': candidate_moves, 'wdl': wdl, 'expected_think_time_s': expected_think_time,
        'player_side': player_side, 'player_to_move': player_to_move,
        'repertoire': repertoire,
        'opening_selection': opening_selection,
        'tactical_hints': tactical,
        'my_moves': my_moves, 'opponent_moves': opponent_moves, 'premove': premove,
        'tactical_warnings': warnings,
        'stockfish': sf,
        'allie_skip_reason': allie_skip_reason,
        'note': ('Allie-Prozentwerte sind menschliche Zugwahrscheinlichkeiten. '
                 'Stockfish liefert Varianten und Bewertungen, aber keine menschlichen Zugwahrscheinlichkeiten.'),
    }
    if not bool(payload.get('show_moves', True)):
        output['my_moves'] = []
        output['opponent_moves'] = []
        output['premove'] = None
        output['uncertainty'] = {
            'level': 'warning',
            'reasons': ['history_incomplete_or_turn_unverified'],
        }
    else:
        output['uncertainty'] = {'level': 'none', 'reasons': []}
    output['plan_messages'] = make_plan_messages(output)
    output['brief'] = make_brief(output)
    return output


def analyse_position(payload: dict[str, Any], model=None) -> dict[str, Any]:
    """Analyse a position, reusing a short-lived production result cache.

    Tests and callers that inject a model bypass the cache so deterministic
    test doubles never leak state between cases.
    """
    if model is not None:
        return _analyse_position_uncached(payload, model)
    # Session/render metadata controls publication in LiveSession but does not
    # change chess analysis.  Excluding it makes the short-lived cache useful
    # across repeated frames and tabs instead of creating one entry per job.
    cache_payload = {
        key: value for key, value in payload.items()
        if key not in {'session_id', 'generation', 'render_revision', 'analysis_key'}
    }
    # Whitespace-only PGN/FEN changes are semantically identical and should
    # share a cache entry.  Do not rewrite SAN/UCI or headers here because
    # PGN clocks and tags can affect model inputs and must remain intact.
    for field in ('pgn', 'fen'):
        value = cache_payload.get(field)
        if isinstance(value, str):
            cache_payload[field] = value.strip()
            if field == 'fen' and cache_payload[field]:
                try:
                    cache_payload[field] = chess.Board(cache_payload[field]).fen()
                except ValueError:
                    # Preserve the raw invalid value so error responses do
                    # not collide with a valid cached position.
                    pass
    key = json.dumps(cache_payload, sort_keys=True, separators=(',', ':'), default=str)
    now = time.monotonic()
    with _ANALYSIS_CACHE_LOCK:
        cached = _ANALYSIS_CACHE.get(key)
        if cached and now - cached[0] <= _ANALYSIS_CACHE_TTL:
            _ANALYSIS_CACHE.move_to_end(key)
            return deepcopy(cached[1])
        if cached:
            _ANALYSIS_CACHE.pop(key, None)
    result = _analyse_position_uncached(payload)
    with _ANALYSIS_CACHE_LOCK:
        _ANALYSIS_CACHE[key] = (time.monotonic(), deepcopy(result))
        _ANALYSIS_CACHE.move_to_end(key)
        while len(_ANALYSIS_CACHE) > _ANALYSIS_CACHE_MAX:
            _ANALYSIS_CACHE.popitem(last=False)
    return result

