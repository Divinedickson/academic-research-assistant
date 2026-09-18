import hashlib
import json
import sys
import urllib.request
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = BACKEND_ROOT / 'embedding-artifacts.json'


def main():
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else BACKEND_ROOT / '.models' / 'minilm')
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    repository = manifest['repository']
    revision = manifest['revision']

    for relative_path, expected_hash in manifest['artifacts'].items():
        target = destination / Path(relative_path).name
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://huggingface.co/{repository}/resolve/{revision}/{relative_path}'
        if not target.exists() or sha256(target) != expected_hash:
            urllib.request.urlretrieve(url, target)
        actual_hash = sha256(target)
        if actual_hash != expected_hash:
            target.unlink(missing_ok=True)
            raise RuntimeError(f'Checksum verification failed for {relative_path}.')
        print(f'verified {target.name}: {actual_hash}')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


if __name__ == '__main__':
    main()
