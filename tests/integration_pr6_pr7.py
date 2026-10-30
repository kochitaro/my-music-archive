"""Combined PR6 storage guards and PR7 satisfaction regressions.
Isolated synthetic data; intercepted test document exposes closure functions only in tests.
Run from repo root: python -u tests/integration_pr6_pr7.py
"""
import json
import os
import threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, stored, edit, record, save, assert_hearts
from data_preservation import seed_data, backup, fail_writes


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    seam = 'window.integrationDB=()=>JSON.parse(JSON.stringify(db));window.integrationOpenEdit=openEdit;window.integrationSave=saveDB;'
    original = (ROOT/'index.html').read_text()
    anchor = "setSection('listening');showStorageState();"
    assert original.count(anchor) == 1
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM', '/usr/bin/chromium'), args=['--no-sandbox'])
        context = browser.new_context(locale='ja-JP', accept_downloads=True)
        context.route(base+'/', lambda route: route.fulfill(body=original.replace(anchor, seam+anchor), content_type='text/html'))
        context.route('https://**/*', lambda route: route.abort())
        context.add_init_script("""const get=Storage.prototype.getItem,set=Storage.prototype.setItem;
        window.originalGet=get;window.writes=[];window.failRead=get.call(localStorage,'integration-read-error')==='true';
        Storage.prototype.getItem=function(k){if(window.failRead&&k==='my-music-archive-pilot-v03')throw new DOMException('Synthetic read failure','SecurityError');return get.call(this,k)};
        Storage.prototype.setItem=function(k,v){window.writes.push(k);if(window.failWrite&&k==='my-music-archive-pilot-v03')throw new DOMException('Synthetic write failure','QuotaExceededError');return set.call(this,k,v)};""")
        page = context.new_page()
        errors, alerts = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: (alerts.append(d.message), d.accept()))
        page.goto(base)

        def same_as(seed):
            assert stored(page) == seed
            assert page.evaluate('integrationDB()') == seed
            assert backup(page) == seed

        for lang in ['ja', 'en']:
            ja = lang == 'ja'
            seed = seed_data()
            page.evaluate('([k,v,lang])=>{failRead=false;failWrite=false;localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",lang)}', [KEY, seed, lang])
            page.reload()
            # Each creation path must leave both original DB and exported JSON unchanged after write failure.
            for section in ['listening', 'collection', 'live']:
                page.locator(f'[data-section={section}]').click()
                if section == 'live':
                    page.locator('#add-live-trigger').click()
                    page.locator('#live-title').fill('Failed Live')
                    slider = page.locator('[data-target=live-rating] .star-rating')
                    slider.press('End')
                    assert_hearts(slider, final_fraction=100)
                else:
                    page.locator('#manual-add-trigger').click()
                    page.locator('#manual-title').fill('Failed Album')
                    page.locator('#manual-artist').fill('Synthetic')
                fail_writes(page, True)
                page.locator('#live-form > button' if section == 'live' else '#save').click()
                expect(page.locator('#live-create-modal' if section == 'live' else '#modal')).to_have_class('modal open')
                assert ('変更は反映されていません' if ja else 'Changes have not been applied') in alerts[-1]
                same_as(seed)
                page.locator('#close-live-create' if section == 'live' else '#close').click()
                fail_writes(page, False)
            print('PASS create failures preserve all original values/JSON in three archives:', lang)

            page.locator('[data-section=live]').click()
            edit(page, 'live')
            expect(page.locator('label[for=e-live-rating]')).to_contain_text('スコア' if ja else 'Score')
            slider = page.locator('[data-target=e-live-rating] .star-rating')
            assert_hearts(slider, final_fraction=20)
            before_writes = page.evaluate('writes.length')
            page.locator('#e-live-rating').evaluate('(e)=>e.value="11"')
            page.locator('#save').click()
            assert alerts[-1] == ('スコアは0.0〜5.0の範囲で0.1刻みで指定してください。' if ja else 'Score must be between 0.0 and 5.0 in steps of 0.1.')
            assert page.evaluate('writes.length') == before_writes
            same_as(seed)
            page.locator('#close').click()
            edit(page, 'live')
            slider.press('ArrowRight')
            expect(page.locator('#e-live-rating')).to_have_value('8.6')
            fail_writes(page, True)
            page.locator('#save').click()
            expect(page.locator('#e-live-rating')).to_have_value('8.6')
            same_as(seed)  # the attempted 8.6 did not replace original 8.4 in memory/storage/backup
            page.locator('#close').click()
            fail_writes(page, False)
            # Successful save elsewhere must not later commit the failed Live edit.
            page.locator('[data-section=collection]').click()
            edit(page, 'collection')
            page.locator('#memo').fill('Other archive saved')
            save(page)
            assert stored(page)['live'] == seed['live']
            page.reload()
            assert stored(page)['live'] == seed['live']
            print('PASS Live validation messages, failed heart edit preserves exact rating/JSON after later save and reload:', lang)

            page.locator('[data-section=live]').click()
            edit(page, 'live')
            slider.press('ArrowRight')
            save(page)
            assert stored(page)['live'][0]['rating'] == '8.6'
            edit(page, 'live')
            expect(page.locator('#e-live-rating')).to_have_value('8.6')
            page.locator('[data-target=e-live-rating] .rating-clear').click()
            save(page)
            assert stored(page)['live'][0]['rating'] == ''
            assert record(page, 'live').locator('.heart-symbol').count() == 0
            page.locator('#add-live-trigger').click()
            page.locator('#live-title').fill('New Score')
            page.locator('[data-target=live-rating] .star-rating').press('End')
            page.locator('#live-form > button').click()
            expect(page.locator('#live-create-modal')).not_to_have_class('modal open')
            assert stored(page)['live'][0]['rating'] == '10.0'
            assert_hearts(record(page, 'New Score'), final_fraction=100)
            current = stored(page)
            exported = backup(page)
            assert exported == current
            page.locator('#import-json').set_input_files(dict(name='combined.json', mimeType='application/json', buffer=json.dumps(exported).encode()))
            expect(page.locator('#import-json')).to_have_value('')
            page.reload()
            same_as(current)
            print('PASS normal Live heart create/edit/re-edit/clear and full JSON restore/reload:', lang)

            # Test render and openEdit guards after corrupt JSON and a startup SecurityError.
            for read_error in [False, True]:
                raw = json.dumps(seed) if read_error else '{broken\r\n日本語'
                page.evaluate('([k,raw,fail])=>{failRead=false;localStorage.setItem(k,raw);localStorage.setItem("integration-read-error",String(fail))}', [KEY, raw, read_error])
                page.reload()
                for section in ['live', 'listening', 'collection']:
                    page.locator(f'[data-section={section}]').click()
                    expect(page.locator('#storage-state')).to_be_visible()
                    expect(page.locator('#library')).to_contain_text('保存を停止' if ja else 'Saving is stopped')
                writes_before = page.evaluate('writes.length')
                alerts_before = len(alerts)
                page.evaluate('integrationOpenEdit("live")')
                assert len(alerts) == alerts_before+1  # verifies canSave runs even before record lookup
                assert ('保存を停止' if ja else 'Saving is stopped') in alerts[-1]
                expect(page.locator('#modal')).not_to_have_class('modal open')
                assert page.evaluate('integrationSave({version:3,listening:[],collection:[],live:[]})') is False
                page.locator('#live-form').evaluate('(e)=>e.onsubmit({preventDefault(){}})')
                page.locator('#save').evaluate('(e)=>e.onclick()')
                assert page.evaluate('writes.length') == writes_before
                assert page.evaluate('(k)=>originalGet.call(localStorage,k)', KEY) == raw
                if read_error:
                    expect(page.locator('#recover-source')).to_be_disabled()
                else:
                    with page.expect_download() as dl:
                        page.locator('#recover-source').click()
                    assert __import__('pathlib').Path(dl.value.path()).read_bytes() == raw.encode()
                page.evaluate('localStorage.setItem("integration-read-error","false")')
            print('PASS stopped render/edit/create/common-save guards and original recovery/no writes:', lang)
        assert not errors, errors
        browser.close()
    server.shutdown()


if __name__ == '__main__':
    main()
