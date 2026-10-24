"""Group 1: isolated synthetic browser data and injected storage exceptions.
Run from repo root: python -u tests/data_preservation.py
No production test API: closure access is added only to the intercepted test document.
"""
import copy
import json
import os
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, stored, edit, record

OLD = 'my-music-archive-pilot-v1'
PHOTO = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='
SEAM = "window.testDB=()=>JSON.parse(JSON.stringify(db));window.testSave=saveDB;"


def seed_data(missing=False):
    result = dict(version=3, listening=[], collection=[], live=[])
    for section in ['listening', 'collection', 'live']:
        r = dict(entryId=section, id='', title=section, artist='Synthetic', date='2026-01-02', release='2025',
                 memo='Original', photo=PHOTO, rating='8.4', tags=['Tag'], genre='Jazz', label='Label',
                 store='Store', format='LP', price='100', condition='Used', venue='Venue', extra={'keep': [1, 2]})
        if missing:
            for key in ['memo', 'photo', 'genre', 'label', 'tags', 'store', 'format', 'price', 'condition', 'venue', 'rating']:
                r.pop(key, None)
        result[section] = [r, dict(r, entryId=section+'-second', title=section+' second')]
    return result


def backup(page):
    with page.expect_download() as dl:
        page.locator('#export-json').evaluate('(e)=>e.onclick()')
    return json.loads(Path(dl.value.path()).read_text())


def fail_writes(page, fail):
    page.evaluate('(v)=>window.failWrite=v', fail)


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM', '/usr/bin/chromium'), args=['--no-sandbox'])
        context = browser.new_context(locale='ja-JP', accept_downloads=True)
        html = (ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();", SEAM+"setSection('listening');showStorageState();")
        context.route(base+'/', lambda route: route.fulfill(body=html, content_type='text/html'))
        context.route('https://**/*', lambda route: route.abort())
        context.add_init_script("""const get=Storage.prototype.getItem,set=Storage.prototype.setItem;
        window.originalGet=get;window.writes=[];window.failRead=JSON.parse(get.call(localStorage,'testReadFailure')||'false');
        Storage.prototype.getItem=function(k){if(window.failRead && (k==='my-music-archive-pilot-v03'||window.failRead==='all'))throw new DOMException('Injected read','SecurityError');return get.call(this,k)};
        Storage.prototype.setItem=function(k,v){window.writes.push(k);if(window.failWrite && k==='my-music-archive-pilot-v03')throw new DOMException('Injected quota','QuotaExceededError');return set.call(this,k,v)};""")
        page = context.new_page()
        errors, alerts = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: (alerts.append(d.message), d.accept()))
        page.goto(base)

        def reset(seed):
            page.evaluate('([k,v])=>{failRead=false;failWrite=false;localStorage.setItem(k,JSON.stringify(v))}', [KEY, seed])
            page.reload()

        def preserved(seed):
            assert stored(page) == seed
            assert page.evaluate('testDB()') == seed  # includes exact property presence and order
            assert backup(page) == seed

        def later_save(seed, section):
            other = 'collection' if section != 'collection' else 'listening'
            page.locator(f'[data-section={other}]').click()
            edit(page, other)
            page.locator('#memo').fill('Later successful save')
            page.locator('#save').click()
            assert stored(page)[section] == seed[section]
            assert page.evaluate('testDB()')[section] == seed[section]
            assert backup(page)[section] == seed[section]
            page.reload()
            assert stored(page)[section] == seed[section]

        for section in ['listening', 'collection', 'live']:
            seed = seed_data()
            reset(seed)
            page.locator(f'[data-section={section}]').click()
            edit(page, section)
            fail_writes(page, True)
            page.locator('#delete').click(); page.locator('#delete-accept').click()
            preserved(seed)
            expect(page.locator('#modal')).to_have_class('modal open')
            page.locator('#close').click()
            record(page, section).click()
            expect(page.locator('#view-content')).to_contain_text('Original')
            page.locator('#view-close').click()
            assert '変更は反映されていません' in alerts[-1]
            fail_writes(page, False)
            later_save(seed, section)
            print('PASS A delete failure, exact data/order, details, backup, later other archive save/reload:', section)

        for missing in [False, True]:
            for section in ['listening', 'collection', 'live']:
                seed = seed_data(missing)
                reset(seed)
                page.locator(f'[data-section={section}]').click()
                edit(page, section)
                page.locator('#memo').fill('FAILED memo')
                photo_input = '#e-live-photo' if section == 'live' else '#album-photo'
                page.locator(photo_input).set_input_files(dict(name='synthetic.png', mimeType='image/png', buffer=__import__('base64').b64decode(PHOTO.split(',')[1])))
                fail_writes(page, True)
                page.locator('#save').click()
                preserved(seed)
                expect(page.locator('#memo')).to_have_value('FAILED memo')
                page.locator('#close').click()
                edit(page, section)
                expect(page.locator('#memo')).to_have_value('' if missing else 'Original')
                # Photo removal, including absent-property path via direct handler.
                remove = '#remove-photo' if section == 'live' else '#remove-album-photo'
                page.locator(remove).evaluate('(e)=>e.onclick()')
                preserved(seed)
                page.locator('#close').click()
                fail_writes(page, False)
                later_save(seed, section)
                # Retry the failed edit and real image resize, then successful removal.
                page.locator(f'[data-section={section}]').click(); edit(page, section)
                page.locator('#memo').fill('Retry saved')
                page.locator(photo_input).set_input_files(dict(name='synthetic.png', mimeType='image/png', buffer=__import__('base64').b64decode(PHOTO.split(',')[1])))
                page.locator('#save').click()
                expect(page.locator('#modal')).not_to_have_class('modal open')
                saved = stored(page)[section][0]
                assert saved['memo'] == 'Retry saved' and saved['photo'].startswith('data:image/jpeg')
                assert saved['entryId'] == seed[section][0]['entryId'] and saved['extra'] == seed[section][0]['extra']
                assert backup(page) == stored(page)
                page.reload(); assert stored(page)[section][0] == saved
                page.locator(f'[data-section={section}]').click(); edit(page, section)
                page.locator(remove).evaluate('(e)=>e.onclick()')
                assert stored(page)[section][0]['photo'] == ''
                page.locator('#close').click()
                print('PASS B/E edit/photo/remove failure, exact property presence, later save, retry and photo persistence:', section, 'missing=', missing)

        for raw, read_error in [('{broken\r\n 日本語', False), ('{ "unrecognized": true }\n', False), ('', False), (json.dumps(seed_data()), True), (json.dumps(seed_data()), 'all')]:
            page.evaluate('([k,v,old,data])=>{failRead=false;localStorage.setItem(k,v);localStorage.setItem(old,JSON.stringify(data))}', [KEY, raw, OLD, seed_data()])
            page.evaluate('(v)=>localStorage.setItem("testReadFailure",JSON.stringify(v))', read_error)
            page.reload()
            expect(page.locator('#storage-state')).to_be_visible()
            expect(page.locator('#storage-reason')).to_contain_text('現在の状態で新しい記録を保存できません')
            assert page.evaluate('(k)=>originalGet.call(localStorage,k)', KEY) == raw
            before = page.evaluate('writes.length')
            assert page.evaluate('testSave({version:3,listening:[],collection:[],live:[]})') is False
            for control in ['save', 'delete', 'manual-add-trigger', 'add-live-trigger', 'remove-photo', 'remove-album-photo', 'export-json', 'export-csv']:
                page.locator('#'+control).evaluate('(e)=>e.onclick()')
            page.locator('#import-json').evaluate('(e)=>e.onchange({target:e})')
            assert page.evaluate('writes.length') == before
            assert page.evaluate('(k)=>originalGet.call(localStorage,k)', KEY) == raw
            if read_error:
                expect(page.locator('#recover-source')).to_be_disabled()
                expect(page.locator('#recovery-info')).to_contain_text('回収できません')
            else:
                with page.expect_download() as dl:
                    page.locator('#recover-source').click()
                assert Path(dl.value.path()).read_bytes() == raw.encode('utf-8')
            assert page.evaluate('writes.length') == before
            for section in ['live', 'collection', 'listening']:
                page.locator(f'[data-section={section}]').click()
                expect(page.locator('#library')).to_contain_text('保存を停止')
            for lang in ['en', 'ja']:
                page.locator('#ui-language').select_option(lang)
                expect(page.locator('#storage-reason')).to_contain_text('Saving is stopped' if lang == 'en' else '保存を停止')
            page.reload()
            expect(page.locator('#storage-state')).to_be_visible()
            assert page.evaluate('(k)=>originalGet.call(localStorage,k)', KEY) == raw
            print('PASS C/D read failure, common/entry guards, no fallback/overwrite, exact recovery or unavailable, reload:', repr(raw[:20]), read_error)
        assert not errors, errors
        browser.close()
    server.shutdown()
    print('PASS all group 1 injected-exception tests; real device quota and iPhone Safari NOT tested')

if __name__ == '__main__':
    main()
