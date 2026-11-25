"""Source/dist parity, real UI CRUD/photos/JSON, legal navigation and 404.
Run: python tests/static_distribution.py [--source /path/to/local-PR52-overlay]
Only localhost and synthetic records; external requests are blocked.
"""
import argparse
import base64
import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect
from data_preservation import seed_data, PHOTO

SNAPSHOT = """async () => {
 const result={};
 for(const {name} of await indexedDB.databases()) {
  const db=await new Promise((ok,no)=>{const r=indexedDB.open(name);r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)});
  result[name]={};
  for(const name of db.objectStoreNames) {
   result[db.name][name]=await new Promise((ok,no)=>{
    const tx=db.transaction(name),s=tx.objectStore(name),keys=s.getAllKeys(),values=s.getAll();
    tx.oncomplete=()=>ok({keys:keys.result,values:values.result});tx.onerror=()=>no(tx.error);
   });
  }
  db.close();
 }
 return {idb:result,local:{...localStorage}};
}"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, root, clean=False, **kwargs):
        self.clean = clean
        super().__init__(*args, directory=str(root), **kwargs)

    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path
        prefix = '/my-music-archive'
        if path.startswith(prefix + '/'):
            path = path[len(prefix):]
        if self.clean and path in ['/terms.html', '/privacy.html']:
            self.send_response(301)
            self.send_header('Location', self.path.replace('.html', '', 1))
            self.end_headers()
            return
        if self.clean and path in ['/terms', '/privacy']:
            path += '.html'
        self.path = path + ('?' + parsed.query if parsed.query else '')
        super().do_GET()

    def send_error(self, code, message=None, explain=None):
        file = Path(self.directory) / '404.html'
        if code == 404 and file.exists():
            data = file.read_bytes()
            self.send_response(404)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().send_error(code, message, explain)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    servers = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            parity = {}
            for kind, clean in [('source', False), ('dist', False), ('dist', True)]:
                root = args.source / 'dist' if kind == 'dist' else args.source
                server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, root=root, clean=clean))
                servers.append(server)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                for prefix in ['/', '/my-music-archive/']:
                    for lang, width in [('ja', 390), ('en', 1280)]:
                        ctx = browser.new_context(locale=lang, viewport={'width': width, 'height': 844}, accept_downloads=True)
                        ctx.route('https://**/*', lambda r: r.abort())
                        page = ctx.new_page()
                        errors, bad_responses = [], []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        page.on('response', lambda r: bad_responses.append(r.url) if r.status >= 400 else None)
                        page.on('dialog', lambda d: d.accept())
                        def restore(name, data):
                            with page.expect_event('dialog', predicate=lambda d: d.type == 'alert') as event:
                                page.locator('#import-json').set_input_files({'name': name, 'mimeType': 'application/json', 'buffer': data})
                            assert 'completed' in event.value.message or '復元が完了' in event.value.message, event.value.message
                        base = f'http://127.0.0.1:{server.server_port}' + prefix
                        page.goto(base)
                        page.evaluate('MLAReady')
                        page.locator('#ui-language').select_option(lang)
                        seed = seed_data()
                        restore('synthetic.json', json.dumps(seed).encode())
                        page.reload()
                        page.evaluate('MLAReady')

                        def export():
                            with page.expect_download() as event:
                                page.locator('#export-json').click()
                            return Path(event.value.path()).read_bytes()

                        assert json.loads(export()) == seed
                        views = {}
                        for area in ['listening', 'collection', 'live']:
                            page.locator(f'[data-section={area}]').click()
                            views[area] = page.locator('#library').inner_html()
                            assert page.locator('#library img').first.evaluate('(e)=>e.complete && e.naturalWidth>0')
                            title = 'Synthetic created ' + area
                            if area == 'live':
                                page.locator('#add-live-trigger').click()
                                page.locator('#live-title').fill(title)
                                photo_selector = '#live-photo'
                            else:
                                page.locator('#manual-add-trigger').click()
                                page.locator('#manual-title').fill(title)
                                page.locator('#manual-artist').fill('Synthetic artist')
                                photo_selector = '#album-photo'
                            page.locator(photo_selector).set_input_files({'name': 'photo.png', 'mimeType': 'image/png', 'buffer': base64.b64decode(PHOTO.split(',')[1])})
                            page.locator('#live-form > button' if area == 'live' else '#save').click()
                            expect(page.locator('#live-create-modal' if area == 'live' else '#modal')).not_to_be_visible()
                            created = json.loads(export())
                            row = next(r for r in created[area] if r['title'] == title)
                            assert row['photo'].startswith('data:image/jpeg;')
                            page.locator('#library .coverbtn').filter(has_text=title).click()
                            page.locator('#view-edit').click()
                            page.locator('#memo').fill('Edited through UI')
                            page.locator('#save').click()
                            expect(page.locator('#modal')).not_to_be_visible()
                            assert next(r for r in json.loads(export())[area] if r['title'] == title)['memo'] == 'Edited through UI'
                            page.locator('#library .coverbtn').filter(has_text=title).click()
                            page.locator('#view-edit').click()
                            page.locator('#delete').click()
                            page.locator('#delete-accept').click()
                            expect(page.locator('#modal')).not_to_be_visible()
                        assert json.loads(export()) == seed
                        key = (prefix, lang)
                        if key in parity:
                            assert views == parity[key], (kind, clean, prefix, lang)
                        else:
                            parity[key] = views
                        before = page.evaluate(SNAPSHOT)
                        if (root / 'terms.html').exists():
                            # Verify the actual app footer, not just direct URLs.
                            page.locator('#terms-link').click()
                            expect(page.locator('#' + lang)).to_be_visible()
                            page.locator('#' + lang + ' header a').click()
                            page.wait_for_url(base)
                            page.wait_for_function('typeof MLAReady !== "undefined"')
                            page.evaluate('MLAReady')
                            for file, count in [('terms', 13), ('privacy', 14)]:
                                page.goto(base + file + '.html#' + lang)
                                expect(page.locator('#' + lang)).to_be_visible()
                                assert page.locator('#' + lang + ' section').count() == count
                                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                                other = 'en' if lang == 'ja' else 'ja'
                                page.locator('[data-language="' + other + '"]').click()
                                expect(page.locator('#' + other)).to_be_visible()
                                page.locator('#' + other + ' header a').click()
                                page.wait_for_url(base)
                                page.wait_for_function('typeof MLAReady !== "undefined"')
                                page.evaluate('MLAReady')
                                assert page.url == base
                            assert page.evaluate(SNAPSHOT) == before
                        saved = export()
                        restore('actual-download.json', saved)
                        page.reload()
                        page.evaluate('MLAReady')
                        assert json.loads(export()) == seed
                        assert not errors, errors
                        assert not bad_responses, bad_responses
                        before = page.evaluate(SNAPSHOT)
                        response = page.goto(base + 'missing/nested/page')
                        assert response.status == 404
                        expect(page.locator('h1')).to_have_text('404 — Page not found')
                        expect(page.locator('#ja-title')).to_have_text('ページが見つかりません')
                        assert page.evaluate(SNAPSHOT) == before
                        assert not errors, errors
                        ctx.close()
                        print('PASS', args.source.name, kind, 'clean' if clean else 'html', prefix, lang, width,
                              'source parity; 3-area CRUD/photos/IDB/JSON; legal; nested 404', flush=True)
            if (args.source / 'dist/terms.html').exists():
                ctx = browser.new_context(java_script_enabled=False)
                page = ctx.new_page()
                base = f'http://127.0.0.1:{servers[-1].server_port}/my-music-archive/'
                for file in ['terms', 'privacy']:
                    page.goto(base + file + '.html')
                    expect(page.locator('#ja')).to_be_visible()
                    expect(page.locator('#en')).to_be_visible()
                ctx.close()
                print('PASS legal Japanese/English without JavaScript', flush=True)
            browser.close()
    finally:
        for server in servers:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
