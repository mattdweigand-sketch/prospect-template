"""Local setup primitives. Paths and hashes are integrity checks, never authorization."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILES = ('policy.yaml', 'icp.md', 'signals.md', 'talk-track.md', 'providers.yaml', 'sources.json', 'voice.md')


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative_path(root, value):
    root = Path(root).resolve()
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or str(path) == '.':
        raise ValueError('expected a file or directory below the repository')
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('symlinked setup paths are not allowed: ' + str(current))
    current.resolve().relative_to(root)
    return current


def run_path(root, run_id):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', run_id):
        raise ValueError('run id must use lowercase letters, digits, and hyphens')
    return relative_path(root, '.local/setup/' + run_id)


def hashes(folder, missing=False):
    folder = Path(folder)
    result = {}
    for name in FILES:
        file = relative_path(folder, name)
        if not file.is_file():
            if missing and not file.exists():
                result[name] = None
                continue
            raise ValueError('missing configuration file: ' + name)
        result[name] = digest(file)
    return result


def git(root, *args):
    # Read-only callers use pinned blobs, never mutable working-tree content.
    command = ['git', '--no-replace-objects', '--literal-pathspecs', '-c', 'core.hooksPath=' + os.devnull, '-c', 'core.fsmonitor=false',
               '-c', 'core.attributesFile=' + os.devnull, '-C', str(root), *args]
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors='replace').strip() or 'Git read failed')
    return result.stdout


def source_root(doc, root=ROOT):
    raw = doc.get('source')
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError('sources.json needs a local source repository')
    path = Path(raw).expanduser()
    return path.resolve() if path.is_absolute() else relative_path(root, raw).resolve()


def source_ref(value):
    if not isinstance(value, str) or not value or value.startswith('-'):
        raise ValueError('invalid source file reference')
    p = Path(value)
    if p.is_absolute() or '..' in p.parts or any(x.lower() == '.git' for x in p.parts):
        raise ValueError('source file reference must stay inside its source repository')
    if p.as_posix() != value or value == '.':
        raise ValueError('source file reference must be a normalized file path')
    return value


def source_blob(doc, ref, root=ROOT):
    ref = source_ref(ref)
    revision = doc.get('revision', '')
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', revision):
        raise ValueError('source revision must be a full commit hash')
    repo = source_root(doc, root)
    resolved = git(repo, 'rev-parse', '--verify', revision + '^{commit}').decode().strip()
    if resolved != revision:
        raise ValueError('source revision does not resolve exactly')
    entries = git(repo, 'ls-tree', '-z', revision, '--', ref).split(b'\0')
    matches = [e for e in entries if e and e.split(b'\t', 1)[-1].decode() == ref]
    if len(matches) != 1 or matches[0].split()[0] not in (b'100644', b'100755'):
        raise ValueError('source is missing or is not a regular committed file: ' + ref)
    return git(repo, 'show', revision + ':' + ref)
