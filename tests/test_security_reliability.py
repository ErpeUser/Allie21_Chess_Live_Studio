"""Behavioral regressions for authorization and bounded rate-limit windows."""
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException, Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from security import (
    CAPABILITY_TOKEN,
    INSTANCE_ID,
    RequestRateLimiter,
    require_capability,
)


def request_with(token, instance=INSTANCE_ID):
    return Request({'type': 'http', 'headers': [
        (b'authorization', b'Bearer ' + token),
        (b'x-allie-instance', instance.encode('ascii')),
    ]})


class SecurityReliabilityTests(unittest.TestCase):
    def test_non_ascii_token_is_unauthorized_not_internal_error(self):
        with self.assertRaises(HTTPException) as error:
            require_capability(request_with(b'\xffmalformed'))
        self.assertEqual(error.exception.status_code, 401)

    def test_valid_token_and_instance_still_authorize(self):
        require_capability(request_with(CAPABILITY_TOKEN.encode('ascii')))

    def test_wrong_instance_is_rejected(self):
        with self.assertRaises(HTTPException) as error:
            require_capability(request_with(CAPABILITY_TOKEN.encode('ascii'), 'old-instance'))
        self.assertEqual(error.exception.status_code, 401)

    def test_duplicate_authorization_or_instance_headers_are_rejected(self):
        for header in (b'authorization', b'x-allie-instance'):
            request = request_with(CAPABILITY_TOKEN.encode('ascii'))
            duplicate = next(pair for pair in request.scope['headers'] if pair[0] == header)
            request.scope['headers'].append(duplicate)
            with self.subTest(header=header), self.assertRaises(HTTPException) as failure:
                require_capability(request)
            self.assertEqual(failure.exception.status_code, 401)

    def test_short_policy_does_not_expire_long_policy(self):
        now = [0.0]
        limiter = RequestRateLimiter(clock=lambda: now[0])
        self.assertTrue(limiter.allow('slow', 1, 60.0))
        now[0] = 2.0
        self.assertTrue(limiter.allow('fast', 10, 1.0))
        self.assertFalse(limiter.allow('slow', 1, 60.0))
        now[0] = 60.0
        self.assertTrue(limiter.allow('slow', 1, 60.0))

    def test_new_ids_cannot_evict_a_live_exhausted_budget(self):
        limiter = RequestRateLimiter(clock=lambda: 0.0, max_keys=2)
        self.assertTrue(limiter.allow('victim', 1, 60.0))
        self.assertTrue(limiter.allow('other', 1, 60.0))
        self.assertFalse(limiter.allow('new', 1, 60.0))
        self.assertFalse(limiter.allow('victim', 1, 60.0))
        self.assertLessEqual(limiter.key_count, 2)

    def test_expired_buckets_make_room_without_waiting_for_access(self):
        now = [0.0]
        limiter = RequestRateLimiter(clock=lambda: now[0], max_keys=2)
        limiter.allow('a', 1, 1.0)
        limiter.allow('b', 1, 1.0)
        now[0] = 1.0
        self.assertTrue(limiter.allow('c', 1, 60.0))
        self.assertEqual(limiter.key_count, 1)

    def test_invalid_policies_are_rejected(self):
        limiter = RequestRateLimiter()
        for limit, window in [(0, 1), (-1, 1), (1, 0), (1, -1), (1, float('nan')), (1, float('inf'))]:
            with self.subTest(limit=limit, window=window), self.assertRaises(ValueError):
                limiter.allow('bad', limit, window)

    def test_same_key_policies_are_independent(self):
        now = [0.0]
        limiter = RequestRateLimiter(clock=lambda: now[0])
        self.assertTrue(limiter.allow('combined', 1, 60.0))
        self.assertTrue(limiter.allow('combined', 2, 1.0))
        self.assertTrue(limiter.allow('combined', 2, 1.0))
        self.assertFalse(limiter.allow('combined', 2, 1.0))
        self.assertFalse(limiter.allow('combined', 1, 60.0))


if __name__ == '__main__':
    unittest.main()
