"""Application/userscript and independently versioned extension consistency."""
import base64
import hashlib
import json
import re
from pathlib import Path


def check(root: Path) -> dict:
    project = re.search(r'(?m)^version\s*=\s*"([^"]+)"', (root / 'pyproject.toml').read_text())
    userscript = re.search(r'@version\s+([^\r\n]+)', (root / 'browser/allie21_overlay.user.js').read_text(encoding='utf-8'))
    if not project or not userscript or project[1] != userscript[1].strip():
        raise ValueError('Application/userscript version mismatch')
    manifest = json.loads((root / 'browser/manifest.json').read_text(encoding='utf-8'))
    version = manifest.get('version', '')
    if not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', version):
        raise ValueError('Extension needs a four-component browser version')
    if manifest.get('version_name') != '.'.join(version.split('.')[:3]):
        raise ValueError('Extension version_name mismatch')
    digest = hashlib.sha256(base64.b64decode(manifest['key'], validate=True)).hexdigest()[:32]
    extension_id = ''.join(chr(97 + int(c, 16)) for c in digest)
    if extension_id != 'omboihgfgofgmidefcpkihgglhkiielo':
        raise ValueError('Pinned extension identity changed; pairing would break')
    return {'application': project[1], 'extension': version, 'extension_id': extension_id}


if __name__ == '__main__':
    print(json.dumps(check(Path(__file__).resolve().parents[1]), indent=2))
