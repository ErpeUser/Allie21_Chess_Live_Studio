"""Chess recognition via published chessvision API; optional RapidOCR for visible move lists."""
from __future__ import annotations

import math
import re
import time


def sanitize_ocr_history(text: str) -> str:
    """Conservatively keep numbered moves, not stream chat. Legal PGN is checked later."""
    text = (text.replace('×', 'x').replace('–', '-').replace('—', '-')
                 .translate(str.maketrans({
                     '♔': 'K', '♕': 'Q', '♖': 'R', '♗': 'B', '♘': 'N',
                     '♚': 'K', '♛': 'Q', '♜': 'R', '♝': 'B', '♞': 'N',
                 })))
    # Lichess often renders move numbers in a separate column without a
    # trailing period (for example: 1 e4 e5 2 Nf3). Normalize only numbers
    # directly followed by a SAN token; clocks and board coordinates remain untouched.
    san_token = (r'(?:O-O-O[+#]?|O-O[+#]?|0-0-0[+#]?|0-0[+#]?|'
                 r'[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?)')
    text = re.sub(
        rf'(?<![A-Za-z0-9.])(\d{{1,4}})(?=\s+{san_token}(?:\s|$))',
        r'\1.',
        text,
    )
    text = re.sub(r'(?<!\w)[Il]\.(?=\s*[a-hKQRBN])', '1.', text)
    match = re.search(r'(?<!\d)1\s*\.', text)
    if match is None:
        return ''
    text = text[match.start():]
    tokens = re.findall(
        r'(?<![A-Za-z0-9])(?:\d+\s*\.{1,3}|O-O-O[+#]?|O-O[+#]?|0-0-0[+#]?|0-0[+#]?|'
        r'[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]?)(?![a-z0-9])', text)
    if len(tokens) < 3 or tokens[0].replace(' ', '') != '1.':
        return ''
    return ' '.join(tokens)


class BoardVision:
    """Reuse a single chessvision detector/classifier across video frames."""
    def __init__(self):
        from chessvision import BoardDetector, BoardPredictor
        self.detector = BoardDetector(min_size_ratio=0.08)
        self.predictor = BoardPredictor()
        self.previous_box = None
        self.ocr = None
        self.ocr_unavailable = False
        self.last_ocr = 0.0

    def recognize(self, frame):
        detected = self.detector.detect(frame)
        if not detected:
            return None
        def score(candidate):
            x, y, w, h = candidate.box
            prior = self.previous_box
            closeness = 0.0
            if prior:
                px, py, pw, ph = prior
                distance = ((x+w/2-px-pw/2)**2 + (y+h/2-py-ph/2)**2)**0.5
                closeness = max(0.0, 1 - distance/max(w, h, 1))
            return w*h*(1+closeness) + candidate.score*100
        board = max(detected, key=score)
        prediction = self.predictor.predict(board)
        if not math.isfinite(float(prediction.confidence)) or prediction.confidence < .65:
            return None
        box = tuple(map(int, board.box))
        if box[2] < 96 or box[3] < 96 or box[2] <= 0 or box[3] <= 0:
            return None
        self.previous_box = box
        return {'fen': prediction.fen, 'box': list(box),
                'orientation': prediction.orientation.name.lower(),
                'confidence': round(float(prediction.confidence), 3)}

    def read_notation(self, frame, box):
        if self.ocr_unavailable or time.monotonic() - self.last_ocr < 7:
            return ''
        self.last_ocr = time.monotonic()
        if self.ocr is None:
            try:
                from rapidocr import RapidOCR
                self.ocr = RapidOCR()
            except (ImportError, OSError):
                self.ocr_unavailable = True
                return ''
        x, y, w, h = (int(value) for value in box)
        fw, fh = frame.size
        if w <= 0 or h <= 0 or fw <= 0 or fh <= 0:
            return ''

        # The move list is commonly rendered beside the board.  A fixed
        # right-side guard used to reject a valid panel when the board was
        # close to the frame edge, then the fallback compared ``x`` with the
        # *board width* instead of the frame width.  That made the crop side
        # depend on the board size and missed histories on responsive layouts.
        top = max(0, int(y - .20 * h))
        bottom = min(fh, int(y + 1.15 * h))
        gap = max(4, int(round(.03 * w)))
        reach = max(96, int(2.1 * w))
        candidates: list[tuple[int, int, int, int]] = []

        # Keep both sides as candidates.  The OCR result is accepted only
        # after conservative PGN sanitization below, so scanning the opposite
        # side cannot fabricate a history from board pieces or chat text.
        right_start = min(fw, x + w + gap)
        right_end = min(fw, max(right_start, x + reach))
        if right_end - right_start >= 16:
            candidates.append((right_start, top, right_end, bottom))

        left_end = max(0, x - gap)
        left_start = max(0, min(left_end, x - reach))
        if left_end - left_start >= 16:
            candidates.append((left_start, top, left_end, bottom))

        if not candidates:
            return ''
        import numpy as np
        best = ''
        for bounds in candidates:
            try:
                result = self.ocr(np.asarray(frame.crop(bounds)))
            except Exception:  # noqa: BLE001 - optional OCR failure yields no text
                continue
            rows = []
            if result is None or any(getattr(result, name, None) is None
                                     for name in ('txts', 'boxes', 'scores')):
                continue
            for polygon, text, confidence in zip(result.boxes, result.txts, result.scores):
                try:
                    if float(confidence) >= .66:
                        rows.append((sum(p[1] for p in polygon)/len(polygon),
                                     sum(p[0] for p in polygon)/len(polygon), str(text)))
                except (ValueError, IndexError, TypeError, ZeroDivisionError):
                    continue
            rows.sort()
            notation = sanitize_ocr_history(' '.join(row[2] for row in rows))
            if len(notation.split()) > len(best.split()):
                best = notation
        return best
