"""Preview authentication test branch only: build boundary and local Chromium checks; no deployment."""
import functools
import hashlib
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ['.nojekyll', '404.html', 'index.html']

def build(root, success=True):
    result = subprocess.run(['node', 'scripts/build-static.cjs'], cwd=root, capture_output=True, text=True)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    return result

def manifest(root):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'dist').iterdir())}

def main():
    print(build(ROOT).stdout.strip())
    assert sorted(p.name for p in (ROOT/'dist').iterdir()) == EXPECTED
    first = manifest(ROOT)
    (ROOT/'dist'/'stale-private.json').write_text('synthetic stale data')
    build(ROOT)
    assert manifest(ROOT) == first
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root/'scripts').mkdir()
        for name in ['index.html', '404.html', 'scripts/build-static.cjs']:
            shutil.copyfile(ROOT/name, root/name)
        # Existing app files, optional legal bundle, backups and host configuration
        # must never expand the Preview publication boundary.
        for name in ['archive-store.js', 'index.json', '.env', 'CNAME', '_redirects',
                     'terms.html', 'privacy.html', 'legal.css', 'legal.js']:
            (root/name).write_text('SYNTHETIC_DO_NOT_PUBLISH')
        build(root)
        assert manifest(root) == first
        (root/'index.html').unlink()
        build(root, False)
        assert not (root/'dist').exists()
        (root/'index.html').symlink_to(ROOT/'index.html')
        build(root, False)
        assert not (root/'dist').exists()
        (root/'index.html').unlink()
        shutil.copyfile(ROOT/'index.html', root/'index.html')
        outside = root/'outside'
        outside.mkdir()
        (outside/'keep').write_text('keep')
        (root/'dist').symlink_to(outside, target_is_directory=True)
        build(root, False)
        assert (outside/'keep').read_text() == 'keep'
    print('PASS exact allowlist; deterministic rebuild; stale cleanup; app/legal/private decoys excluded; missing/symlink inputs fail safely')

    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    handler = functools.partial(Quiet, directory=str(ROOT/'dist'))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            for js in [True, False]:
                for width in [320, 390, 1280]:
                    context = browser.new_context(java_script_enabled=js, viewport={'width': width, 'height': 844})
                    context.add_init_script('''
                      window.storageAttempts = [];
                      for (const key of ['indexedDB', 'localStorage', 'sessionStorage']) {
                        Object.defineProperty(window, key, {get() {
                          storageAttempts.push(key); throw Error('Unexpected storage access');
                        }});
                      }
                      Object.defineProperty(document, 'cookie', {get() {
                        storageAttempts.push('cookie'); throw Error('Unexpected cookie read');
                      }, set() { storageAttempts.push('cookie write'); }});
                    ''')
                    context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(origin + '/') else route.abort())
                    page = context.new_page()
                    requests, errors = [], []
                    page.on('request', lambda r: requests.append(r.url))
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    for path in ['/', '/404.html']:
                        requests.clear()
                        response = page.goto(origin + path)
                        assert response.status == 200
                        assert page.locator('h1').inner_text() == 'MLA Preview 認証テスト中'
                        assert page.locator('h1').is_visible()
                        assert page.locator('script, iframe, form, input, img, link').count() == 0
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        assert requests == [origin + path], requests
                        if js:
                            assert page.evaluate('storageAttempts') == []
                        assert not errors, errors
                        if not js and width == 390:
                            page.screenshot(path='/tmp/mla-preview-' + ('index' if path == '/' else '404') + '.png', full_page=True)
                    context.close()
                    print(f'PASS Chromium width={width} JavaScript={js}: both pages visible; no overflow, extra requests or storage access')
            browser.close()
    finally:
        server.shutdown()
    print('SHA256 ' + json.dumps(first, sort_keys=True))

if __name__ == '__main__':
    main()
