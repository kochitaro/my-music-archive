"""Rejected restore can be dismissed without losing records, photos or recovery.
Synthetic data only; localhost; no production hooks. Run: python tests/restore_failure_navigation.py
"""
import copy
import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from data_preservation import seed_data
from unified_archive import STATE

ROOT = Path(__file__).resolve().parents[1]


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}'
    seam = "window.navigationTest={section:()=>section,busy:()=>operationBusy||saving||settingsBusy,draft:()=>draft};"
    source = (ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();", seam+"setSection('listening');showStorageState();")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
            for lang in ['ja', 'en']:
                ctx = browser.new_context(locale=lang, viewport={'width': 390, 'height': 844}, accept_downloads=True)
                ctx.route('https://**/*', lambda r: r.abort())
                ctx.route(url+'/', lambda r: r.fulfill(body=source, content_type='text/html'))
                page = ctx.new_page()
                alerts, errors = [], []
                page.on('dialog', lambda d: (alerts.append(d.message), d.accept()))
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto(url)
                page.evaluate('MLAReady')
                page.locator('#ui-language').select_option(lang)

                def ready():
                    page.wait_for_function('!navigationTest.busy()')

                def restore(raw):
                    page.locator('#import-json').set_input_files(dict(name='synthetic.json', mimeType='application/json', buffer=raw.encode()))
                    ready()

                def export(selector):
                    with page.expect_download() as event:
                        page.locator(selector).click()
                    return json.loads(Path(event.value.path()).read_text())

                # Real restores create a pinned pre-restore copy. Match the iPhone counts.
                original = seed_data()
                original['listening'].append(dict(original['listening'][0], entryId='listening-third'))
                original['collection'] = []
                original['live'] = original['live'][:1]
                restore(json.dumps(original))
                current = copy.deepcopy(original)
                current['listening'][0]['memo'] = 'Current synthetic record'
                restore(json.dumps(current))
                page.locator('#restore-recovery-title').click()
                assert export('#export-before-restore') == original
                before = page.evaluate(STATE)
                broken = copy.deepcopy(current)
                broken['live'][0]['photo'] = 'data:image/png;base64,NOT_AN_IMAGE'
                invalid = copy.deepcopy(current)
                del invalid['live'][0]['title']
                for name, raw, panel, start in [('corrupt-photo', json.dumps(broken), True, 'listening'),
                                                ('syntax', '{', False, 'collection'),
                                                ('validation', json.dumps(invalid), False, 'live'),
                                                ('new-corrupt-photo', json.dumps(broken), True, 'live')]:
                    page.locator(f'#sections [data-section={start}]').click()
                    restore(raw)
                    if panel:
                        expect(page.locator('#save-notice')).to_be_visible()
                        assert 'live / live' in page.locator('#save-notice-reason').inner_text()
                        assert ('変更はありません' if lang == 'ja' else 'did not change') in page.locator('#save-notice-info').inner_text()
                        page.locator('#save-return').click()
                    else:
                        assert alerts[-1] and page.locator('#save-notice').is_hidden()
                    expect(page.locator('#save-notice')).to_be_hidden()
                    assert page.evaluate('navigationTest.section()') == start
                    for area in ['collection', 'live', 'listening', 'live', 'collection', 'listening']:
                        page.locator(f'#sections [data-section={area}]').click()
                        assert page.evaluate('navigationTest.section()') == area, (lang, name, area)
                        expect(page.locator('#save-notice')).to_be_hidden()
                        expect(page.locator('#discard-input')).to_be_hidden()
                        assert page.locator(f'#sections [data-section={area}]').evaluate("e=>e.classList.contains('active')")
                        if area == 'live':
                            page.wait_for_function("[...document.querySelectorAll('#library img')].length===1 && [...document.querySelectorAll('#library img')].every(x=>x.complete&&x.naturalWidth>0)")
                    assert page.evaluate(STATE) == before
                    assert export('#export-json') == current
                    assert export('#export-before-restore') == original
                    assert page.locator('#import-json').input_value() == ''
                    print('PASS', lang, name, 'dismiss/tab navigation, exact stores/photos/current/recovery, no reload', flush=True)
                # Failed edit inputs still require protection; Close must not discard them.
                page.locator('#manual-add-trigger').click()
                page.locator('#manual-title').fill('Retained synthetic input')
                page.locator('#manual-artist').fill('')
                page.locator('#save').click()
                ready()
                expect(page.locator('#save-notice')).to_be_visible()
                draft = page.evaluate('navigationTest.draft()')
                page.locator('#save-return').click()
                assert page.locator('#manual-title').input_value() == 'Retained synthetic input'
                page.locator('#sections [data-section=live]').evaluate('e=>e.click()')
                expect(page.locator('#save-notice')).to_be_visible()
                assert page.evaluate('navigationTest.section()') == 'listening'
                assert page.evaluate('navigationTest.draft()') == draft
                assert page.evaluate(STATE) == before
                assert not errors, errors
                print('PASS', lang, 'failed edit retains draft and tab protection', flush=True)
                ctx.close()
            browser.close()
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
