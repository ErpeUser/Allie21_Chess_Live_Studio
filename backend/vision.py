"""Chess recognition via published chessvision API; optional RapidOCR for visible move lists."""
from __future__ import annotations
import re
import time
import math


def sanitize_ocr_history(text: str) -> str:
    """Conservatively keep numbered moves, not stream chat. Legal PGN is checked later."""
    text = text.replace('×', 'x').replace('–', '-').replace('—', '-')
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
        x, y, w, h = box
        fw, fh = frame.size
        if x+w+90 < fw:
            bounds = (x+w, max(0, int(y-.20*h)), min(fw, int(x+2.1*w)), min(fh, int(y+1.15*h)))
        elif x > w*.50:
            bounds = (max(0, x-w), max(0, int(y-.20*h)), x, min(fh, int(y+1.15*h)))
        else:
            return ''
        import numpy as np
        try:
            result = self.ocr(np.asarray(frame.crop(bounds)))
        except Exception:
            return ''
        rows = []
        if result is None or any(getattr(result, name, None) is None for name in ('txts', 'boxes', 'scores')):
            return ''
        for polygon, text, confidence in zip(result.boxes, result.txts, result.scores):
            try:
                if float(confidence) >= .66:
                    rows.append((sum(p[1] for p in polygon)/len(polygon),
                                 sum(p[0] for p in polygon)/len(polygon), str(text)))
            except (ValueError, IndexError, TypeError, ZeroDivisionError):
                continue
        rows.sort()
        return sanitize_ocr_history(' '.join(row[2] for row in rows))
