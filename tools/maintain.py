"""Checked main/PR maintenance and staged local Windows deployment.

Requires Python 3.10+, git and gh; Windows builds also need uv/uvx. No reset,
unchecked merge, unmerged-branch deletion, or browser-profile edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

REPO = 'ErpeUser/Allie21_Chess_Live_Studio'
BUNDLE_NAME = 'Allie21 Chess Live Studio'
BUILD_DIRS = ('backend/', 'browser/', 'viewer/', 'assets/', 'beispiele/')
BUILD_FILES = {'pyproject.toml', 'uv.lock', 'tools/launcher.py',
               'tools/build_exe.ps1', 'tools/release_smoke.py'}
REQUIRED_CHECKS = {'windows-tests', 'maintenance-tests', 'Secret scan',
                   'CodeQL (javascript-typescript)', 'CodeQL (python)'}


def local_state_dir() -> Path:
    """Keep persistent update metadata and recoverable backups outside the checkout."""
    base = os.environ.get('LOCALAPPDATA') or os.environ.get('XDG_STATE_HOME')
    if base:
        return Path(base) / 'Allie21' / 'maintenance'
    return Path.home() / '.local' / 'state' / 'Allie21' / 'maintenance'


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name, suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, ensure_ascii=True)
            stream.write('\n')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def fingerprint(root: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(set(paths)):
        if name == 'browser/allie-build.json':
            continue
        if name not in BUILD_FILES and not name.startswith(BUILD_DIRS):
            continue
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f'Build input missing or symlink: {name}')
        digest.update(name.encode('utf-8') + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def pr_block_reason(pr: dict, checks: list[str], reviews: list[dict]) -> str:
    if pr.get('state') != 'open' or pr.get('draft'):
        return 'closed or draft'
    if pr.get('base', {}).get('ref') != 'main':
        return 'base is not main'
    if (pr.get('head', {}).get('repo') or {}).get('full_name') != REPO:
        return 'external fork requires manual review'
    if pr.get('mergeable') is not True or pr.get('mergeable_state') != 'clean':
        return 'conflict, outdated base, or mergeability not ready'
    if not checks or any(state != 'success' for state in checks):
        return 'checks absent, pending, skipped, or failed'
    latest = {}
    for review in sorted(reviews, key=lambda item: item.get('id', 0)):
        if review.get('state') in {'APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'}:
            latest[review.get('user', {}).get('login', '')] = review['state']
    if 'CHANGES_REQUESTED' in latest.values():
        return 'changes requested by reviewer'
    return ''


def cleanup_candidate(name: str, protected: bool, open_heads: set[str]) -> bool:
    return (not protected and name not in open_heads
            and name not in {'main', 'master', 'develop', 'dev', 'HEAD'}
            and not name.startswith(('release/', 'releases/')))


def replace_directory(stage: Path, target: Path, backup: Path) -> None:
    """Same-filesystem promotion with rollback if the second rename fails."""
    if not stage.is_dir() or stage.is_symlink():
        raise FileNotFoundError(f'Invalid staged directory: {stage}')
    if target.is_symlink() or backup.exists():
        raise RuntimeError('Unsafe deployment target or existing backup')
    target.parent.mkdir(parents=True, exist_ok=True)
    backup.parent.mkdir(parents=True, exist_ok=True)
    existed = target.exists()
    if existed:
        target.rename(backup)
    try:
        stage.rename(target)
    except OSError:
        if existed:
            backup.rename(target)
        raise


class Maintenance:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.state_dir = local_state_dir()
        self.report: dict = {'merged': [], 'blocked': [], 'deleted': [], 'kept': []}
        self.env = {**os.environ, 'ALLIE_UPDATE_ACTIVE': '1', 'GH_PROMPT_DISABLED': '1',
                    'GIT_TERMINAL_PROMPT': '0'}

    def run(self, *args: str, timeout: int = 120, live: bool = False) -> str:
        result = subprocess.run(args, cwd=self.root, env=self.env, text=True,
                                encoding='utf-8', errors='replace',
                                capture_output=not live, timeout=timeout, check=False)
        if result.returncode:
            raise RuntimeError(f'{args[0]} failed ({result.returncode}): '
                               f'{(result.stderr or "see command output")[-1200:]}')
        return result.stdout or ''

    def git(self, *args: str) -> str:
        return self.run('git', *args).strip()

    def api(self, endpoint: str, method: str = 'GET', **values):
        args = ['gh', 'api', f'repos/{REPO}/{endpoint}', '--method', method]
        if method == 'GET':
            args.extend(['--paginate', '--slurp'])
        for key, value in values.items():
            args.extend(['-f', f'{key}={value}'])
        raw = self.run(*args)
        data = json.loads(raw) if raw.strip() else {}
        if method == 'GET':
            if data and isinstance(data[0], list):
                return [item for page in data for item in page]
            return data[0] if len(data) == 1 else data
        return data

    def preflight(self):
        if Path(self.git('rev-parse', '--show-toplevel')).resolve() != self.root:
            raise RuntimeError('Run from the Allie repository root')
        if self.git('branch', '--show-current') != 'main':
            raise RuntimeError('Switch to main first; no automatic branch switch')
        origin = self.git('remote', 'get-url', 'origin').rstrip('/').removesuffix('.git')
        if origin not in {f'https://github.com/{REPO}', f'git@github.com:{REPO}',
                          f'ssh://git@github.com/{REPO}'}:
            raise RuntimeError('origin is not the expected Allie repository')
        if self.git('status', '--porcelain'):
            raise RuntimeError('Local changes present. Commit or save them first; nothing was discarded.')
        self.git('fetch', '--prune', 'origin')
        self.git('merge-base', '--is-ancestor', 'HEAD', 'origin/main')

    def install_hooks(self):
        existing = subprocess.run(['git', 'config', '--get', 'core.hooksPath'], cwd=self.root,
                                  capture_output=True, text=True, check=False).stdout.strip()
        if existing and existing != '.githooks':
            raise RuntimeError(f'Existing hooksPath preserved: {existing}. Integrate hooks manually.')
        hooks = Path(self.git('rev-parse', '--git-path', 'hooks'))
        if not hooks.is_absolute():
            hooks = self.root / hooks
        if not existing and any(p.is_file() and not p.name.endswith('.sample') for p in hooks.glob('*')):
            raise RuntimeError('Existing Git hooks preserved. Integrate .githooks manually.')
        self.git('config', '--local', 'core.hooksPath', '.githooks')
        for name in ('post-merge', 'post-rewrite'):
            (self.root / '.githooks' / name).chmod(0o755)

    def process_prs(self):
        for brief in self.api('pulls?state=open&base=main&per_page=100'):
            number = int(brief['number'])
            try:
                self.process_pr(number)
            except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
                self.report['blocked'].append({'pr': number, 'reason': str(exc)})

    def process_pr(self, number: int):
        pr = self.api(f'pulls/{number}')
        sha = pr['head']['sha']
        compare = self.api(f'compare/{pr["base"]["sha"]}...{sha}')
        outdated = compare.get('merge_base_commit', {}).get('sha') != pr['base']['sha']
        trusted = (pr['head'].get('repo') or {}).get('full_name') == REPO
        if outdated and trusted and not pr.get('draft') and pr.get('mergeable') is True:
            self.api(f'pulls/{number}/update-branch', 'PUT', expected_head_sha=sha)
            self.report['blocked'].append({'pr': number, 'reason': 'base updated; new checks required'})
            return
        pages = self.api(f'commits/{sha}/check-runs?per_page=100&filter=latest')
        pages = pages if isinstance(pages, list) else [pages]
        runs = [check for page in pages for check in page.get('check_runs', [])]
        checks = [(c.get('conclusion') if c.get('status') == 'completed' else 'pending') for c in runs]
        latest_statuses = {}
        for status in self.api(f'commits/{sha}/statuses?per_page=100'):
            latest_statuses.setdefault(status['context'], status['state'])
        checks.extend(latest_statuses.values())
        reviews = self.api(f'pulls/{number}/reviews?per_page=100')
        reason = pr_block_reason(pr, checks, reviews)
        missing = REQUIRED_CHECKS - {c.get('name') for c in runs}
        if missing:
            reason = 'required workflows absent: ' + ', '.join(sorted(missing))
        if outdated:
            reason = 'head does not contain current main'
        if reason:
            self.report['blocked'].append({'pr': number, 'reason': reason})
            return
        fresh = self.api(f'pulls/{number}')
        if fresh['head']['sha'] != sha or fresh['base']['sha'] != pr['base']['sha']:
            self.report['blocked'].append({'pr': number, 'reason': 'head/base changed; retry next run'})
            return
        merged = self.api(f'pulls/{number}/merge', 'PUT', sha=sha, merge_method='merge')
        if not merged.get('merged'):
            raise RuntimeError(f'PR #{number} was not merged: {merged}')
        self.report['merged'].append({'pr': number, 'sha': merged['sha']})

    def cleanup(self):
        open_heads = {p['head']['ref'] for p in self.api('pulls?state=open&per_page=100')}
        self.git('fetch', '--prune', 'origin')
        branches = self.git('for-each-ref', '--format=%(refname:strip=3)%09%(objectname)', 'refs/remotes/origin')
        for line in branches.splitlines():
            name, sha = line.split('\t', 1)
            if not cleanup_candidate(name, False, open_heads):
                continue
            try:
                info = self.api('branches/' + quote(name, safe=''))
                if not cleanup_candidate(name, info.get('protected', True), open_heads):
                    continue
                self.git('merge-base', '--is-ancestor', sha, 'origin/main')
                self.git('push', f'--force-with-lease=refs/heads/{name}:{sha}', 'origin', f':refs/heads/{name}')
                self.report['deleted'].append(name)
                # -d refuses unmerged work and branches in any linked worktree.
                subprocess.run(['git', 'branch', '-d', '--', name], cwd=self.root,
                               capture_output=True, check=False)
            except RuntimeError as exc:
                self.report['kept'].append({'branch': name, 'reason': str(exc)})
        self.git('fetch', '--prune', 'origin')

    def deploy(self, force: bool = False):
        if os.name != 'nt':
            raise RuntimeError('Windows deployment requires local Windows; use --git-only in Codex cloud')
        revision = self.git('rev-parse', 'HEAD')
        paths = [p for p in self.git('ls-files', '-z').split('\0') if p]
        build_hash = fingerprint(self.root, paths)
        ext_hash = fingerprint(self.root, [p for p in paths if p.startswith('browser/')])
        state_path = self.state_dir / 'update-state.json'
        try:
            state = json.loads(state_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            state = {}
        bundle = self.root / 'release' / BUNDLE_NAME
        manifest = json.loads((self.root / 'browser' / 'manifest.json').read_text(encoding='utf-8'))
        stamp = {'revision': ext_hash, 'commit': revision, 'version': manifest['version']}
        rebuild = force or state.get('fingerprint') != build_hash or not (bundle / f'{BUNDLE_NAME}.exe').is_file()
        if not rebuild:
            try:
                self.run(sys.executable, 'tools/release_smoke.py', '--bundle', str(bundle), timeout=120, live=True)
            except RuntimeError:
                rebuild = True
        if rebuild:
            work_dir = self.state_dir
            if self.root.drive.casefold() != work_dir.drive.casefold():
                # Directory promotion via rename requires the same Windows volume.
                work_dir = self.root / '.build'
            work_dir.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix='update-', dir=work_dir))
            self.run('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                     'tools/build_exe.ps1', '-DistPath', str(stage), timeout=7200, live=True)
            candidate = stage / BUNDLE_NAME
            self.run(sys.executable, 'tools/release_smoke.py', '--bundle', str(candidate), timeout=120, live=True)
            replace_directory(candidate, bundle, stage / 'previous-release')
            self.report['previous_bundle'] = str(stage / 'previous-release')
        # Announce a finished deployment only after the server bundle passes.
        write_json(self.root / 'browser' / 'allie-build.json', stamp)
        target = Path(os.environ['LOCALAPPDATA']) / 'Allie21' / 'EdgeOverlay'
        target.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='edge-update-', dir=target.parent))
        shutil.copytree(self.root / 'browser', stage / 'extension', ignore=shutil.ignore_patterns('__pycache__'))
        replace_directory(stage / 'extension', target, stage / 'previous-extension')
        self.run('powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                 'tools/desktop_shortcut.ps1', '-Bundle', str(bundle), live=True)
        write_json(state_path, {'fingerprint': build_hash, 'commit': revision,
                               'extension': str(target), 'updated_at': time.time()})
        self.report.update({'commit': revision, 'rebuilt': rebuild, 'extension': str(target)})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git-only', action='store_true')
    parser.add_argument('--deploy-only', action='store_true')
    parser.add_argument('--after-pull', action='store_true')
    parser.add_argument('--process-prs', action='store_true')
    parser.add_argument('--cleanup', action='store_true')
    parser.add_argument('--install-hooks', action='store_true')
    parser.add_argument('--force-build', action='store_true')
    args = parser.parse_args(argv)
    if os.environ.get('ALLIE_UPDATE_ACTIVE') == '1':
        return 0
    root = Path(__file__).resolve().parents[1]
    worker = Maintenance(root)
    lock = local_state_dir() / 'maintenance.lock'
    lock.parent.mkdir(exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        print(f'Another update is running. Verify no updater remains before removing {lock}.', file=sys.stderr)
        return 1
    os.write(fd, str(os.getpid()).encode('ascii'))
    os.close(fd)
    try:
        worker.preflight()
        if not args.deploy_only:
            if args.install_hooks:
                worker.install_hooks()
            if args.process_prs:
                worker.process_prs()
            worker.git('pull', '--ff-only', 'origin', 'main')
            if args.cleanup:
                worker.cleanup()
        else:
            if worker.git('rev-parse', 'HEAD') != worker.git('rev-parse', 'origin/main'):
                raise RuntimeError('main changed during update; run UPDATE_ALLIE.cmd again')
            report_file = local_state_dir() / 'maintenance-report.json'
            if report_file.exists():
                worker.report.update(json.loads(report_file.read_text(encoding='utf-8')))
                worker.report.pop('error', None)
        if not args.git_only:
            worker.deploy(args.force_build)
        worker.report['head'] = worker.git('rev-parse', 'HEAD')
        write_json(local_state_dir() / 'maintenance-report.json', worker.report)
        print(json.dumps(worker.report, indent=2))
        return 2 if worker.report['blocked'] and not args.deploy_only else 0
    except (RuntimeError, OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
        worker.report['error'] = str(exc)
        write_json(local_state_dir() / 'maintenance-report.json', worker.report)
        print(f'UPDATE STOPPED: {exc}', file=sys.stderr)
        return 1
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    raise SystemExit(main())
