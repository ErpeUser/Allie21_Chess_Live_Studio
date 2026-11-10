import sys
import types
import unittest

from backend.vision import BoardVision, sanitize_ocr_history


class _Crop:
    def __init__(self, bounds):
        self.bounds = bounds


class _Frame:
    size = (1920, 1080)

    def crop(self, bounds):
        return _Crop(bounds)


class _OCR:
    def __init__(self, expected_side):
        self.expected_side = expected_side

    def __call__(self, image):
        left_of_board = image.bounds[2] <= 960
        match = left_of_board if self.expected_side == 'left' else not left_of_board
        text = '1 e4 e5 2 Nf3 Nc6' if match else 'stream chat'
        return types.SimpleNamespace(
            boxes=[[(0, 0), (10, 0), (10, 10), (0, 10)]],
            txts=[text],
            scores=[0.99],
        )


class VisionOCRTests(unittest.TestCase):
    def test_sanitizer_accepts_columnized_move_numbers_without_periods(self):
        self.assertEqual(
            sanitize_ocr_history('1 e4 e5 2 Nf3 Nc6'),
            '1. e4 e5 2. Nf3 Nc6',
        )

    def test_read_notation_uses_left_crop_when_board_is_on_right(self):
        vision = BoardVision.__new__(BoardVision)
        vision.ocr_unavailable = False
        vision.last_ocr = -100
        vision.ocr = _OCR('left')
        sys.modules.setdefault('numpy', types.SimpleNamespace(asarray=lambda image: image))
        self.assertEqual(
            vision.read_notation(_Frame(), (1100, 120, 640, 640)),
            '1. e4 e5 2. Nf3 Nc6',
        )

    def test_read_notation_uses_right_crop_when_board_is_on_left(self):
        vision = BoardVision.__new__(BoardVision)
        vision.ocr_unavailable = False
        vision.last_ocr = -100
        vision.ocr = _OCR('right')
        sys.modules.setdefault('numpy', types.SimpleNamespace(asarray=lambda image: image))
        self.assertEqual(
            vision.read_notation(_Frame(), (120, 120, 640, 640)),
            '1. e4 e5 2. Nf3 Nc6',
        )


if __name__ == '__main__':
    unittest.main()
