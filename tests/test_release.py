"""Check the public package, local links, and fictional sample reproducibility."""

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('packager', ROOT / 'scripts/package_release.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class ReleaseTests(unittest.TestCase):
    def test_manifest_files_exist_and_local_links_resolve_in_package(self):
        files = packager.public_files()
        included = {source.resolve() for _, source in files}
        for name, source in files:
            if source.suffix != '.md':
                continue
            # Templates intentionally link to the future generated package.
            if name == 'skills/sidequest/assets/personal-skill.md':
                continue
            content = source.read_text(encoding='utf-8')
            links = re.findall(r'\]\(([^)\s]+)\)', content)
            links += re.findall(r'<img\b[^>]*\bsrc="([^"]+)"', content)
            for link in links:
                if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', link) or link.startswith('#'):
                    continue
                target = (source.parent / unquote(link.split('#', 1)[0])).resolve()
                with self.subTest(file=name, link=link):
                    self.assertTrue(target.exists(), 'broken local link')
                    self.assertTrue(target in included or
                                    (target.is_dir() and any(target in p.parents for p in included)),
                                    'linked resource is not in the public package')

    def test_sample_is_exactly_reproducible_from_fictional_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / 'skills/sidequest/scripts/build_personal_skill.py'),
                 '--plan', str(ROOT / 'examples/slow-living-plan.json'), '--output', directory],
                text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            generated = Path(directory) / 'sidequest-slow-living'
            checked_in = ROOT / 'examples/generated/sidequest-slow-living'
            self.assertEqual({p.relative_to(generated): p.read_bytes()
                              for p in generated.rglob('*') if p.is_file()},
                             {p.relative_to(checked_in): p.read_bytes()
                              for p in checked_in.rglob('*') if p.is_file()})

    def test_zip_contains_exact_public_manifest_and_is_repeatable(self):
        expected = {'life-sidequest/' + name for name, _ in packager.public_files()}
        with tempfile.TemporaryDirectory() as directory:
            first, count = packager.package(Path(directory) / 'one.zip')
            second, _ = packager.package(Path(directory) / 'two.zip')
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(count, len(expected))
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(set(archive.namelist()), expected)
                self.assertIsNone(archive.testzip())
                for name in archive.namelist():
                    self.assertNotIn('.sidequest', name)

    def test_existing_archive_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'existing.zip'
            target.write_bytes(b'keep this')
            with self.assertRaises(FileExistsError):
                packager.package(target)
            self.assertEqual(target.read_bytes(), b'keep this')

    def test_manifest_rejects_private_traversal_duplicate_and_missing_files(self):
        cases = [['.sidequest/confirmed-plan.json'], ['.env.production'],
                 ['../private.md'], ['/private.md'], ['a/./b.md'], ['a//b.md'],
                 ['README.md', 'README.md'], ['missing.md']]
        for manifest in cases:
            with self.subTest(manifest=manifest), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'release-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
                (root / 'README.md').write_text('public example', encoding='utf-8')
                with self.assertRaises(ValueError):
                    packager.public_files(root)

    def test_symlink_cannot_smuggle_other_files_into_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'release-manifest.json').write_text('["public.md"]', encoding='utf-8')
            (root / 'private.txt').write_text('do not package', encoding='utf-8')
            try:
                (root / 'public.md').symlink_to(root / 'private.txt')
            except OSError:
                self.skipTest('symlink creation is not available')
            with self.assertRaises(ValueError):
                packager.public_files(root)

    def test_unlisted_file_does_not_enter_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'release-manifest.json').write_text('["public.txt"]', encoding='utf-8')
            (root / 'public.txt').write_text('example', encoding='utf-8')
            (root / 'private.txt').write_text('not for release', encoding='utf-8')
            output, _ = packager.package(root / 'package.zip', root)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist(), ['life-sidequest/public.txt'])


if __name__ == '__main__':
    unittest.main()
