import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from overlay_lease import OverlayLeaseConflict, OverlayLeaseManager


class OverlayLeaseTests(unittest.TestCase):
    def test_claim_authorize_release_and_conflict(self):
        now = [100.0]
        manager = OverlayLeaseManager(lambda: now[0])
        first = manager.claim('session-a')
        self.assertTrue(manager.authorize('session-a', first.owner_token))
        with self.assertRaises(OverlayLeaseConflict):
            manager.claim('session-b')
        self.assertFalse(manager.release('session-a', 'wrong-token'))
        self.assertTrue(manager.release('session-a', first.owner_token))
        second = manager.claim('session-b')
        self.assertNotEqual(first.owner_token, second.owner_token)

    def test_same_session_touches_and_expiry_allows_takeover(self):
        now = [0.0]
        manager = OverlayLeaseManager(lambda: now[0], lease_seconds=30)
        first = manager.claim('session-a')
        now[0] = 29
        renewed = manager.claim('session-a')
        self.assertEqual(first.owner_token, renewed.owner_token)
        now[0] = 58.9
        self.assertTrue(manager.authorize('session-a', renewed.owner_token))
        now[0] = 59.1
        second = manager.claim('session-b')
        self.assertNotEqual(first.owner_token, second.owner_token)
        self.assertFalse(manager.authorize('session-a', first.owner_token))

    def test_force_release_clears_ownership(self):
        manager = OverlayLeaseManager(lambda: 0.0)
        lease = manager.claim('session-a')
        manager.force_release()
        self.assertFalse(manager.authorize('session-a', lease.owner_token))

    def test_expiry_notifies_overlay_cleanup(self):
        now = [0.0]
        expired = []
        manager = OverlayLeaseManager(lambda: now[0], lease_seconds=5, on_expire=expired.append)
        lease = manager.claim('session-a')
        now[0] = 5.1
        self.assertFalse(manager.authorize('session-a', lease.owner_token))
        self.assertEqual(expired, [lease])

    def test_renewal_keeps_unchanged_position_alive_for_two_minutes(self):
        now = [0.0]
        manager = OverlayLeaseManager(lambda: now[0], lease_seconds=30)
        lease = manager.claim('unchanged-position')
        for second in range(10, 121, 10):
            now[0] = float(second)
            lease = manager.renew('unchanged-position', lease.owner_token)
            self.assertTrue(manager.authorize('unchanged-position', lease.owner_token))
            self.assertGreater(lease.expires_at, now[0])
        now[0] = 120.5
        self.assertTrue(manager.authorize('unchanged-position', lease.owner_token))


if __name__ == '__main__':
    unittest.main()
