"""Tests use real policy/file operations; network boundaries are isolated."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('maintain', Path(__file__).resolve().parents[2] / 'source/automation/maintain.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def pr(**changes):
    value = {'number': 7, 'state': 'open', 'draft': False, 'base': {'ref': 'main', 'sha': 'b' * 40},
             'head': {'sha': 'a' * 40, 'repo': {'full_name': m.REPO}},
             'mergeable': True, 'mergeable_state': 'clean'}
    value.update(changes)
    return value


class PolicyTests(unittest.TestCase):
    def test_deployment_decisions_refresh_only_stale_outputs(self):
        unchanged = m.deployment_decisions(
            force=False, rebuild=False, state={'fingerprint': 'build',
                                                'extension_revision': 'ext'},
            extension_hash='ext',
            stamp_matches=True, extension_matches=True, shortcut_matches=True)
        self.assertEqual(unchanged, {
            'rebuild': False, 'write_stamp': False,
            'update_extension': False, 'update_shortcut': False,
        })
        rebuilt = m.deployment_decisions(
            force=False, rebuild=True, state={},
            extension_hash='ext', stamp_matches=False,
            extension_matches=False, shortcut_matches=True)
        self.assertTrue(rebuilt['rebuild'])
        self.assertTrue(rebuilt['write_stamp'])
        self.assertTrue(rebuilt['update_extension'])
        self.assertTrue(rebuilt['update_shortcut'])
        docs_only = m.deployment_decisions(
            force=False, rebuild=False, state={'extension_revision': 'ext'},
            extension_hash='ext', stamp_matches=False,
            extension_matches=True, shortcut_matches=True)
        self.assertFalse(docs_only['update_extension'])
        self.assertFalse(docs_only['update_shortcut'])

    def test_update_relation_prefers_newer_main_or_combines_diverged_fixes(self):
        self.assertEqual(m.update_relation('fix/security', 0, 2), 'candidate-newer')
        self.assertEqual(m.update_relation('fix/security', 3, 2), 'combine-fix-with-main')
        self.assertEqual(m.update_relation('feature/ui', 3, 2), 'combine-review')
        self.assertEqual(m.update_relation('old', 3, 0), 'already-integrated')

    def test_install_hooks_includes_direct_main_push_guard(self):
        self.assertIn('pre-push', m.HOOK_NAMES)

    def test_remote_branch_scan_reports_prs_and_combination_action(self):
        worker = m.Maintenance(Path('.'))
        def api(endpoint, method='GET', **kwargs):
            self.assertEqual(method, 'GET')
            if endpoint.startswith('pulls?'):
                return [{'number': 4, 'state': 'open', 'head': {'ref': 'fix/security'}}]
            if endpoint.startswith('branches?'):
                return [{'name': 'fix/security', 'commit': {'sha': 'a' * 40}}]
            if endpoint == 'compare/main...fix%2Fsecurity':
                return {'behind_by': 3, 'ahead_by': 2}
            raise AssertionError(endpoint)
        with patch.object(worker, 'api', side_effect=api):
            worker.inspect_remote_branches()
        self.assertEqual(worker.report['pull_requests'][0]['action'], 'review-candidate')
        self.assertEqual(worker.report['branch_candidates'][0]['action'], 'combine-fix-with-main')

    def test_successful_trusted_pr_is_eligible(self):
        self.assertEqual(m.pr_block_reason(pr(), ['success'], []), '')

    def test_failed_pending_absent_checks_block(self):
        for checks in [[], ['failure'], ['pending'], ['success', 'cancelled'], ['skipped']]:
            with self.subTest(checks=checks):
                self.assertTrue(m.pr_block_reason(pr(), checks, []))

    def test_draft_conflict_fork_and_unknown_mergeability_block(self):
        for value in [pr(draft=True), pr(mergeable=False), pr(mergeable=None),
                      pr(mergeable_state='behind'), pr(state='closed'),
                      pr(head={'sha': 'a' * 40, 'repo': {'full_name': 'other/repo'}})]:
            with self.subTest(value=value):
                self.assertTrue(m.pr_block_reason(value, ['success'], []))

    def test_latest_review_per_author_is_used(self):
        reviews = [{'user': {'login': 'x'}, 'state': 'CHANGES_REQUESTED', 'id': 1},
                   {'user': {'login': 'x'}, 'state': 'COMMENTED', 'id': 2}]
        self.assertTrue(m.pr_block_reason(pr(), ['success'], reviews))
        reviews.append({'user': {'login': 'x'}, 'state': 'APPROVED', 'id': 3})
        self.assertFalse(m.pr_block_reason(pr(), ['success'], reviews))

    def test_protected_and_open_pr_branches_are_not_cleanup_candidates(self):
        for name in ['main', 'master', 'develop', 'release/v1', 'fix/open']:
            self.assertFalse(m.cleanup_candidate(name, False, {'fix/open'}))
        self.assertFalse(m.cleanup_candidate('fix/done', True, set()))
        self.assertTrue(m.cleanup_candidate('fix/done', False, set()))

    def test_maintenance_state_is_protected_inside_generated(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'LOCALAPPDATA': folder}):
            self.assertEqual(m.local_state_dir(), Path(__file__).resolve().parents[2] / 'generated' / 'protected' / 'maintenance')

    def test_build_fingerprint_ignores_docs_but_not_backend_or_deleted_files(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / 'source/app/backend').mkdir(parents=True)
            (root / 'source/app/backend/a.py').write_text('one')
            (root / 'README_DE.md').write_text('docs')
            paths = ['source/app/backend/a.py', 'README_DE.md']
            before = m.fingerprint(root, paths)
            (root / 'README_DE.md').write_text('other docs')
            self.assertEqual(before, m.fingerprint(root, paths))
            (root / 'source/app/backend/a.py').write_text('two')
            self.assertNotEqual(before, m.fingerprint(root, paths))
            self.assertNotEqual(before, m.fingerprint(root, ['README_DE.md']))

    def test_extension_stamp_not_part_of_fingerprint(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / 'source/app/browser').mkdir(parents=True)
            (root / 'source/app/browser/manifest.json').write_text('{}')
            (root / 'generated/build').mkdir(parents=True)
            (root / 'generated/build/allie-build.json').write_text('first')
            before = m.fingerprint(root, ['source/app/browser/manifest.json', 'generated/build/allie-build.json'])
            (root / 'generated/build/allie-build.json').write_text('second')
            self.assertEqual(before, m.fingerprint(root, ['source/app/browser/manifest.json', 'generated/build/allie-build.json']))

    def test_directory_replacement_keeps_previous(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            target, stage, backup = [root / name for name in ('target', 'stage', 'backup')]
            target.mkdir()
            stage.mkdir()
            (target / 'value').write_text('old')
            (stage / 'value').write_text('new')
            m.replace_directory(stage, target, backup)
            self.assertEqual((target / 'value').read_text(), 'new')
            self.assertEqual((backup / 'value').read_text(), 'old')

    def test_atomic_json_is_valid(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'state.json'
            m.write_json(path, {'sha': 'a'})
            self.assertEqual(json.loads(path.read_text()), {'sha': 'a'})

    def test_promotion_failure_restores_previous_bundle(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            stage, target, backup = [root / name for name in ('stage', 'target', 'backup')]
            stage.mkdir()
            target.mkdir()
            (target / 'old').write_text('preserve')
            original = Path.rename
            def rename(path, destination):
                if path == stage:
                    raise PermissionError('file locked')
                return original(path, destination)
            with patch.object(Path, 'rename', rename), self.assertRaises(PermissionError):
                m.replace_directory(stage, target, backup)
            self.assertEqual((target / 'old').read_text(), 'preserve')
            self.assertTrue(stage.exists())
            self.assertFalse(backup.exists())

    def test_fingerprint_rejects_symlinks(self):
        if os.name == 'nt':
            self.skipTest('Windows symlink creation requires extra privileges')
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / 'source/app/backend').mkdir(parents=True)
            (root / 'source/app/backend/a.py').symlink_to(root / 'outside')
            with self.assertRaises(RuntimeError):
                m.fingerprint(root, ['source/app/backend/a.py'])

    def test_review_dismissal_unblocks(self):
        reviews = [{'id': 1, 'user': {'login': 'r'}, 'state': 'CHANGES_REQUESTED'},
                   {'id': 2, 'user': {'login': 'r'}, 'state': 'DISMISSED'}]
        self.assertEqual(m.pr_block_reason(pr(), ['success'], reviews), '')

    def test_github_pagination_flattens_array_pages(self):
        worker = m.Maintenance(Path('.'))
        with patch.object(worker, 'run', return_value='[[{"number":1}],[{"number":2}]]'):
            self.assertEqual(worker.api('pulls'), [{'number': 1}, {'number': 2}])

    def test_absent_required_workflows_block_merge_even_with_one_green_check(self):
        worker = m.Maintenance(Path('.'))
        def api(endpoint, method='GET', **kwargs):
            self.assertEqual(method, 'GET', 'unsafe write before all required checks exist')
            if endpoint == 'pulls/7':
                return pr()
            if endpoint.startswith('compare/'):
                return {'merge_base_commit': {'sha': 'b' * 40}}
            if 'check-runs' in endpoint:
                return {'check_runs': [{'name': 'Secret scan', 'status': 'completed', 'conclusion': 'success'}]}
            return []
        with patch.object(worker, 'api', side_effect=api):
            worker.process_pr(7)
        self.assertEqual(worker.report['merged'], [])
        self.assertIn('required workflows absent', worker.report['blocked'][0]['reason'])

    def test_pr_api_failure_does_not_skip_following_pr(self):
        worker = m.Maintenance(Path('.'))
        with patch.object(worker, 'api', return_value=[{'number': 1}, {'number': 2}]), \
             patch.object(worker, 'process_pr', side_effect=[RuntimeError('conflict'), None]) as process:
            worker.process_prs()
        self.assertEqual(process.call_count, 2)
        self.assertEqual(worker.report['blocked'], [{'pr': 1, 'reason': 'conflict'}])


if __name__ == '__main__':
    unittest.main()
