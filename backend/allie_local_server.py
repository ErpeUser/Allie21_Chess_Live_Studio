#!/usr/bin/env python3
"""Local-only Allie 2.1 chess training analysis endpoint.

Uses the real yimingzhang/allie-2.1 model; no Stockfish substitute or
hard-coded fake 'human move' distribution. Requires standard chess move history.
"""
from __future__ import annotations

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
from typing import Any

import chess
import chess.pgn
from chess_extras import (
    describe_candidate,
    make_brief,
    opening_for_position,
    opening_note,
    position_facts,
    repertoire_move_for,
    standard_repertoire,
    stockfish_lines,
)
from config import MODEL_ID, MODEL_REVISION, time_profile

HOST = "127.0.0.1"
PORT = int(os.environ.get("ALLIE_PORT", "8765"))
MODEL_NAME = MODEL_ID
MAX_BODY = 64 * 1024
_model = None
_ANALYSIS_CACHE: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
_ANALYSIS_CACHE_LOCK = threading.RLock()
_ANALYSIS_CACHE_TTL = 30.0
_ANALYSIS_CACHE_MAX = 24
_model_lock = threading.RLock()


def get_model():
    global _model
    with _model_lock:
        if _model is None:
            # Remote code is the model author's official API implementation.
            # Review Hugging Face repository source before enabling remote code.
            from transformers import AutoModel
            print(f"Loading actual model {MODEL_NAME} (CPU int8 weights use about 9.8 GB)...", flush=True)
            options = {"active_experts": 8}
            if sys.platform == "win32":
                # Allie's native Rust engine is officially Linux x86-64 only.
                # Avoid a failed probe and use the supported Windows backend.
                options["backend"] = "torch"
            _model = AutoModel.from_pretrained(
                MODEL_NAME, revision=MODEL_REVISION, trust_remote_code=True, **options
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
        game = chess.pgn.read_game(io.StringIO(raw))
        if not game:
            raise ValueError("Cannot read PGN")
        if game.errors:
            raise ValueError(f"PGN invalid: {game.errors[0]}")
        if game.board().fen() != chess.STARTING_FEN:
            raise ValueError("Allie 2.1 requires standard chess from the initial position")
        if game.headers.get("Variant", "Standard") not in ("Standard", "Chess", ""):
            raise ValueError("This variant is not supported by the Allie 2.1 model")
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


def rank_allie_candidates(
    board: chess.Board, candidates: list[dict[str, Any]], play_style: str
) -> list[dict[str, Any]]:
    """Rerank Allie's legal candidates for direct king pressure only on request."""
    if play_style == 'normal':
        return candidates
    if play_style != 'aggressive':
        raise ValueError("play_style must be normal or aggressive")

    def pressure(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int, int, float, int]:
        index, candidate = item
        flags = candidate.get('flags') or []
        after = board.copy(stack=False)
        after.push_uci(candidate['uci'])
        own_mate = int('Schachmatt' in flags)
        opponent_can_mate = False
        if not own_mate:
            for reply in after.legal_moves:
                probe = after.copy(stack=False)
                probe.push(reply)
                if probe.is_checkmate():
                    opponent_can_mate = True
                    break
        king = after.king(after.turn)
        ring = chess.SquareSet(chess.BB_KING_ATTACKS[king]) if king is not None else ()
        attacker = not after.turn
        attacked = sum(after.is_attacked_by(attacker, square) for square in ring)
        return (
            own_mate,
            int(not opponent_can_mate),
            int('Schach' in flags),
            attacked,
            float(candidate.get('probability', 0.0)),
            -index,
        )

    return [candidate for _, candidate in sorted(enumerate(candidates), key=pressure, reverse=True)]


def safe_aggressive_order(
    candidates: list[dict[str, Any]], stockfish: dict[str, Any] | None,
    margin_cp: int = 150,
) -> list[dict[str, Any]]:
    """Keep aggressive king pressure from overriding a clear engine safety gap.

    Allie still determines the candidates and their pressure order. Stockfish
    only demotes a move that is materially far below the best Allie candidate;
    missing engine lines are left in their original Allie order.
    """
    if not candidates or not stockfish or not stockfish.get('available'):
        return candidates
    scores = {
        str(line.get('uci')): int(line['score_cp'])
        for line in stockfish.get('lines', [])
        if line.get('uci') and isinstance(line.get('score_cp'), int)
    }
    known = [scores[move['uci']] for move in candidates if move.get('uci') in scores]
    if not known:
        return candidates
    floor = max(known) - max(50, int(margin_cp))
    safe = [move for move in candidates if move.get('uci') not in scores or scores[move['uci']] >= floor]
    unsafe = [move for move in candidates if move.get('uci') in scores and scores[move['uci']] < floor]
    return safe + unsafe


def risk_weighted_premove(branches: list[tuple[float, list[dict[str, Any]]]]) -> dict[str, Any] | None:
    """Pick one Allie move that survives the most likely alternative branches.

    The score uses only Allie's human move probabilities. Missing support in a
    branch is treated as risk instead of being silently replaced by Stockfish.
    """
    branches = [(max(0.0, float(weight)), moves[:5]) for weight, moves in branches if moves]
    total_weight = sum(weight for weight, _ in branches)
    if total_weight <= 0:
        return None
    candidates: dict[str, dict[str, Any]] = {}
    for weight, moves in branches:
        seen: set[str] = set()
        for move in moves:
            uci = move.get('uci')
            if not uci or uci in seen:
                continue
            seen.add(uci)
            item = candidates.setdefault(uci, {'move': move, 'weighted': 0.0, 'covered': 0.0})
            item['weighted'] += weight * max(0.0, float(move.get('probability', 0.0)))
            item['covered'] += weight
    if not candidates:
        return None
    def score(item):
        coverage = item['covered'] / total_weight
        likelihood = item['weighted'] / total_weight
        # A pre-move that disappears in another likely branch is materially
        # riskier than a normal recommendation, so coverage gets a strong penalty.
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
    repertoire = output.get('repertoire') or {}
    if output.get('move_count', 0) <= 2 and repertoire.get('primary'):
        messages.append(
            f"Standardrepertoire: {repertoire['primary']} · Alternative: {repertoire['alternative']}"
            f" · Weitere Option: {repertoire.get('additional', 'keine')}."
        )
        if repertoire.get('expected_move'):
            messages.append('Allie-Kandidat aus dem Repertoire: ' +
                            str(repertoire.get('expected_san') or repertoire['expected_move']) + '.')
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
    elif finished_game:
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
    if play_style not in ('normal', 'aggressive'):
        raise ValueError('play_style must be normal or aggressive')

    opening = opening_for_position(board, moves)
    if opening:
        opening = {**opening, 'idea': opening_note(opening)}
    candidate_moves: list[dict[str, Any]] = []
    wdl = None
    expected_think_time = None
    prediction_top: list[dict[str, Any]] = []
    prediction_second: list[dict[str, Any]] = []
    premove_branches: list[tuple[float, list[dict[str, Any]]]] = []
    warnings: list[str] = []
    allie_skip_reason: str | None = None
    player_side = str(payload.get('player_side', 'white' if board.turn else 'black')).lower()
    if player_side not in ('white', 'black'):
        player_side = 'white' if board.turn else 'black'
    player_to_move = player_side == ('white' if board.turn else 'black')
    requested_opening = payload.get('opening_white' if player_side == 'white' else 'opening_black')
    repertoire: dict[str, Any] = standard_repertoire(player_side, requested_opening)
    repertoire['expected_move'] = None
    if player_to_move:
        repertoire['expected_move'] = repertoire_move_for(moves, player_side, repertoire['selection'])
    if repertoire['expected_move']:
        try:
            expected = chess.Move.from_uci(repertoire['expected_move'])
            if expected in board.legal_moves:
                repertoire['expected_san'] = board.san(expected)
        except ValueError:
            pass
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
                    # The public API already returns most-likely-first and keeps
                    # its own game cache. Do not sort the probabilities again.
                    choices = list(result['moves'].items())[:5]
                    candidate_moves = [describe_move(board, uci, prob) for uci, prob in choices]
                    if player_to_move:
                        candidate_moves = rank_allie_candidates(board, candidate_moves, play_style)
                        expected = repertoire.get('expected_move')
                        if expected:
                            match = next((move for move in candidate_moves if move['uci'] == expected), None)
                            if match and (not candidate_moves or
                                          float(candidate_moves[0].get('probability', 0.0)) -
                                          float(match.get('probability', 0.0)) <= .18):
                                candidate_moves = [match] + [move for move in candidate_moves if move is not match]
                    wdl = [round(float(x), 5) for x in result['wdl']] if result.get('wdl') is not None else None
                    if result.get('think_time') is not None:
                        expected_think_time = round(float(result['think_time']), 2)
            except Exception as exc:  # noqa: BLE001 - optional model boundary must fail soft
                allie_skip_reason = ('Allie 2.1 konnte nicht geladen oder ausgefuehrt werden: '
                                     + str(exc)[:220])
            if candidate_moves and payload.get('preview', True):
                try:
                    with _model_lock:
                        # On our turn only the top choice needs an opponent
                        # preview. Computing a reply to our second choice is
                        # unused and costs a complete model step.
                        preview_choices = candidate_moves[:1 if player_to_move else 2]
                        for index, choice in enumerate(preview_choices):
                            after = board.copy(stack=False)
                            after.push_uci(choice['uci'])
                            if after.is_game_over():
                                continue
                            replies = list(model.predict(
                                moves + [choice['uci']], white_elo=white_elo,
                                black_elo=black_elo, time_control=tc,
                                clocks=clocks + [None],
                            ).items())[:3]
                            shown = [describe_move(after, uci, prob) for uci, prob in replies]
                            if not player_to_move:
                                shown = rank_allie_candidates(after, shown, play_style)
                            if index == 0:
                                prediction_top = shown
                                for reply in after.legal_moves:
                                    probe = after.copy(stack=False)
                                    probe.push(reply)
                                    if probe.is_checkmate():
                                        warnings.append('Achtung: Gegner kann nach dieser Wahl sofort mattsetzen: ' + after.san(reply))
                                        if len(warnings) >= 2:
                                            break
                                if not warnings and shown:
                                    if 'Schach' in shown[0]['flags']:
                                        warnings.append('Die wahrscheinlichste Gegnerantwort setzt Schach: ' + shown[0]['san'])
                                    if 'Schlagzug' in shown[0]['flags']:
                                        warnings.append('Die wahrscheinlichste Gegnerantwort schlaegt eine Figur: ' + shown[0]['san'])
                            else:
                                prediction_second = shown
                        if player_to_move and candidate_moves and prediction_top:
                            # The blue arrow is the best continuation after
                            # the single most likely opponent reply. A second
                            # speculative branch doubled latency without
                            # changing the requested top-reply pre-move.
                            for reply in prediction_top[:1]:
                                after_reply = board.copy(stack=False)
                                after_reply.push_uci(candidate_moves[0]['uci'])
                                after_reply.push_uci(reply['uci'])
                                if after_reply.is_game_over():
                                    continue
                                continuation = model.predict(
                                    moves + [candidate_moves[0]['uci'], reply['uci']],
                                    white_elo=white_elo, black_elo=black_elo,
                                    time_control=tc, clocks=clocks + [None, None])
                                ranked = list(continuation.items())[:5]
                                described = [describe_move(after_reply, uci, prob) for uci, prob in ranked]
                                premove_branches.append((reply['probability'], described))
                except Exception as exc:  # noqa: BLE001 - optional prediction branch must fail soft
                    warnings.append('Allie-Gegnerprognose derzeit nicht verfuegbar: ' + str(exc)[:150])

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
                    })
            for item in sf.get('lines', []):
                item['explanation'] = describe_candidate(board, item['uci'])
            if play_style == 'aggressive':
                candidate_moves = safe_aggressive_order(candidate_moves, sf)

    engine_moves = []
    if selection == 'stockfish' and sf and sf.get('available'):
        engine_moves = [{**item, 'source': 'stockfish'} for item in sf.get('lines', [])[:2]]
    if fen_only and not allie_skip_reason:
        allie_skip_reason = ('Allie wartet auf die vollständige Partiegeschichte; '
                             'bis dahin zeigt Stockfish die sicheren Stellungszüge.')

    if player_to_move:
        my_moves = candidate_moves[:2] or engine_moves
        opponent_moves = prediction_top[:2]
        premove = risk_weighted_premove(premove_branches)
    else:
        opponent_moves = candidate_moves[:2] or engine_moves
        my_moves = prediction_top[:2]
        reply_branches = []
        if candidate_moves:
            reply_branches.append((candidate_moves[0]['probability'], prediction_top))
        if len(candidate_moves) > 1:
            reply_branches.append((candidate_moves[1]['probability'], prediction_second))
        premove = risk_weighted_premove(reply_branches)

    output = {
        'model': MODEL_NAME if selection in ('allie', 'both') and not fen_only and candidate_moves else None,
        'reviewed_finished_game': bool(last_move), 'final_played_move': last_move,
        'rating_white': white_elo, 'rating_black': black_elo,
        'mode': mode, 'play_style': play_style, 'time_control': tc, 'move_count': len(moves),
        'side_to_move': 'white' if board.turn else 'black', 'fen': board.fen(),
        'fen_only': fen_only, 'opening': opening, 'position_facts': position_facts(board),
        'moves': candidate_moves, 'wdl': wdl, 'expected_think_time_s': expected_think_time,
        'player_side': player_side, 'player_to_move': player_to_move,
        'repertoire': repertoire,
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
    key = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
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
