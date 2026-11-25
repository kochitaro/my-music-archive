"""Publication boundary tests. Run: python tests/static_build.py (Node 22+ required)."""
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ['index.html', 'insights.css', 'archive-toolbar.css', 'insights.js',
        'search.js', 'photo-store.js', 'archive-toolbar.js', 'mobile-navigation.js',
        'archive-store.js', 'recovery-export.js', 'photo-lifecycle.js', '404.html']
LEGAL = ['terms.html', 'privacy.html', 'legal.css', 'legal.js']


class StaticBuild(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        shutil.copy2(ROOT / 'scripts/build-static.cjs', self.root / 'scripts')
        for file in CORE:
            shutil.copy2(ROOT / file, self.root / file)

    def tearDown(self):
        self.temp.cleanup()

    def build(self, success=True):
        result = subprocess.run(['node', str(self.root / 'scripts/build-static.cjs')],
                                cwd='/tmp', capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

    def digest(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.root / 'dist').iterdir()}

    def test_clean_reproducible_allowlist(self):
        for name in ['backup.json', 'CNAME', '_redirects', '.env', 'screenshot.png']:
            (self.root / name).write_text('must not ship')
        for name in ['docs', 'tests']:
            (self.root / name).mkdir()
            (self.root / name / 'private.json').write_text('must not ship')
        self.build()
        first = self.digest()
        self.assertEqual(set(first), set(CORE + ['.nojekyll']))
        for name in CORE:
            self.assertEqual((self.root / name).read_bytes(), (self.root / 'dist' / name).read_bytes())
        (self.root / 'dist/stale-backup.json').write_text('stale')
        self.build()
        self.assertEqual(first, self.digest())

    def test_legal_bundle_all_or_none(self):
        (self.root / 'terms.html').write_text('<a href="privacy.html#en">Privacy</a><a href="./">MLA</a>')
        self.build(False)
        self.assertFalse((self.root / 'dist').exists())
        for name in LEGAL[1:]:
            (self.root / name).write_text('')
        self.build()
        self.assertEqual(set(self.digest()), set(CORE + LEGAL + ['.nojekyll']))
        for name in LEGAL:
            (self.root / name).unlink()
        self.build()
        self.assertEqual(set(self.digest()), set(CORE + ['.nojekyll']))

    def test_missing_dependency_removes_stale_output(self):
        self.build()
        (self.root / 'search.js').unlink()
        self.build(False)
        self.assertFalse((self.root / 'dist').exists())

    def test_unlisted_and_root_absolute_dependencies_fail(self):
        for ref in ['new-module.js', '/search.js', '//example.org/a.js']:
            with self.subTest(ref=ref):
                (self.root / 'index.html').write_text('<script src="' + ref + '"></script>')
                self.build(False)

    def test_symlinks_cannot_publish_or_redirect_output(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'keep').write_text('keep')
        (self.root / 'dist').symlink_to(outside, target_is_directory=True)
        self.build(False)
        self.assertEqual((outside / 'keep').read_text(), 'keep')
        (self.root / 'dist').unlink()
        (self.root / 'search.js').unlink()
        (self.root / 'search.js').symlink_to(ROOT / 'search.js')
        self.build(False)


if __name__ == '__main__':
    unittest.main()
