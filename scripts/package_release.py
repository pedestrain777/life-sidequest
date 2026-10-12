#!/usr/bin/env python3
"""Package only explicitly reviewed public files. Python 3.9+, no network."""

import argparse
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_PARTS = {'.git', '.sidequest', 'private-skills', 'personal-data',
                 '__pycache__', '.venv', 'dist', '.env'}


def public_files(root=ROOT):
    root = Path(root).resolve()
    manifest = json.loads((root / 'release-manifest.json').read_text(encoding='utf-8'))
    if not isinstance(manifest, list) or not manifest:
        raise ValueError('Release manifest must be a non-empty list')
    seen, files = set(), []
    for name in manifest:
        if not isinstance(name, str) or not name or '\\' in name:
            raise ValueError('Manifest paths must be relative POSIX paths')
        relative = PurePosixPath(name)
        if (relative.is_absolute() or any(part in ('', '.', '..') for part in name.split('/'))
                or name in seen):
            raise ValueError(f'Unsafe or repeated release path: {name}')
        if (PRIVATE_PARTS.intersection(relative.parts)
                or any(part.startswith('.env.') for part in relative.parts)
                or name.endswith(('.local.json', '.pyc', '.pyo'))):
            raise ValueError(f'Private/local files cannot be packaged: {name}')
        source = root.joinpath(*relative.parts)
        if any(path.is_symlink() for path in (source, *source.parents) if path != root):
            raise ValueError(f'Symlinks cannot be packaged: {name}')
        try:
            source.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError(f'Release path escapes repository: {name}') from exc
        if not source.is_file():
            raise ValueError(f'Missing release file: {name}')
        seen.add(name)
        files.append((name, source))
    return sorted(files)


def package(output, root=ROOT):
    files = public_files(root)
    output = Path(output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: never replace an existing archive or follow its symlink.
    with output.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, source in files:
                info = zipfile.ZipInfo('life-sidequest/' + name, (2026, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, source.read_bytes())
    return output.resolve(), len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        output, count = package(args.output)
    except (OSError, ValueError) as exc:
        print(f'Packaging failed: {exc}', file=sys.stderr)
        return 1
    print(f'Packaged {count} public files: {output}')
    print('Local archive only; nothing uploaded or published.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
