"""Synthetic isolated Live artists/color regressions. Run from repository root."""
import copy
import json
import os
import threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, SEED, QuietHandler, stored, record, edit, save, assert_hearts, LIVE_CORAL, LIVE_GOLD
from data_preservation import backup, fail_writes


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    original = (ROOT/'index.html').read_text()
    anchor = "setSection('listening');showStorageState();"
    html = original.replace(anchor, 'window.testDB=()=>JSON.parse(JSON.stringify(db));'+anchor)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM', '/usr/bin/chromium'), args=['--no-sandbox'])
        context = browser.new_context(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True, accept_downloads=True)
        context.route(base+'/', lambda r: r.fulfill(body=html, content_type='text/html'))
        context.route('https://**/*', lambda r: r.abort())
        context.add_init_script("""const set=Storage.prototype.setItem;
        Storage.prototype.setItem=function(k,v){if(window.failWrite&&k==='my-music-archive-pilot-v03')throw new DOMException('Synthetic quota','QuotaExceededError');return set.call(this,k,v)};""")
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: d.accept())
        page.goto(base)
        for lang in ['ja', 'en']:
            seed = copy.deepcopy(SEED)
            page.evaluate('([k,v,l])=>{failWrite=false;localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",l)}', [KEY, seed, lang])
            page.reload()
            page.locator('[data-section=live]').click()
            # Reading and editing an old title must not infer artists or write on open/cancel.
            edit(page, 'Existing Live')
            expect(page.locator('#e-live-title')).to_have_value('Existing Live')
            expect(page.locator('#e-live-artists input')).to_have_value('')
            page.locator('#close').click()
            assert stored(page) == seed
            edit(page, 'Existing Live')
            save(page)
            assert 'artists' not in stored(page)['live'][0]
            # One artist, then multiple artists, editing/removal, all using the same public UI.
            page.locator('#add-live-trigger').click()
            expect(page.locator('#live-artists input')).to_have_count(1)
            expect(page.locator('#live-artists > button')).to_have_text('＋ 出演者を追加' if lang == 'ja' else '＋ Add Artist')
            expect(page.locator('#live-artists label').first).to_have_text('出演アーティスト（任意）' if lang == 'ja' else 'Performing Artists (optional)')
            page.locator('#live-title').fill('Festival Title')
            page.locator('#live-artists input').fill('  Artist A  ')
            page.locator('[data-target=live-rating] .star-rating').press('End')
            page.locator('#live-form > button').click()
            assert stored(page)['live'][0]['artists'] == ['Artist A']
            edit(page, 'Festival Title')
            page.locator('#e-live-artists > button').click()
            expect(page.locator('#e-live-artists input').nth(1)).to_be_focused()
            page.locator('#e-live-artists input').nth(1).fill('日本語 B / <script>')
            page.locator('#e-live-artists > button').click()
            page.locator('#e-live-artists input').nth(2).fill('Remove me')
            page.locator('#e-live-artists .live-artist-row button').nth(2).click()
            page.locator('#e-live-artists input').first.fill('Artist A edited')
            before = stored(page)
            fail_writes(page, True)
            page.locator('#save').click()
            assert stored(page) == before == page.evaluate('testDB()') == backup(page)
            expect(page.locator('#e-live-artists input')).to_have_count(2)
            fail_writes(page, False)
            save(page)
            artists = ['Artist A edited', '日本語 B / <script>']
            expected = stored(page)
            assert expected['live'][0]['artists'] == artists
            assert expected['live'][0]['title'] == 'Festival Title'
            page.reload(); page.locator('[data-section=live]').click()
            record(page, 'Festival Title').click()
            expect(page.locator('.live-artist-list li')).to_have_text(artists)
            page.locator('#view-close').click()
            # Cancelled removal and failed creation must preserve the complete DB and backup.
            edit(page, 'Festival Title')
            page.locator('#e-live-artists .live-artist-row button').first.click()
            page.locator('#e-live-artists .live-artist-row button').first.click()
            expect(page.locator('#e-live-artists input')).to_have_value('')
            fail_writes(page, True); page.locator('#save').click()
            assert expected == stored(page) == page.evaluate('testDB()') == backup(page)
            page.locator('#close').click(); fail_writes(page, False)
            # A later successful save in another archive must not commit failed artist removals.
            page.locator('[data-section=collection]').click()
            edit(page, 'C 4.3'); page.locator('#memo').fill('Later independent save'); save(page)
            assert stored(page)['live'] == expected['live']
            expected = stored(page)
            page.locator('[data-section=live]').click()
            page.locator('#add-live-trigger').click()
            expect(page.locator('#live-artists input')).to_have_count(1)
            page.locator('#live-title').fill('Failed new')
            page.locator('#live-artists input').fill('Uncommitted')
            fail_writes(page, True); page.locator('#live-form > button').click()
            assert expected == stored(page) == page.evaluate('testDB()') == backup(page)
            page.locator('#close-live-create').click(); fail_writes(page, False)
            # Successful deletion of all names explicitly stores [] and keeps the title.
            edit(page, 'Festival Title')
            for _ in range(2):
                page.locator('#e-live-artists .live-artist-row button').first.click()
            save(page)
            assert stored(page)['live'][0]['artists'] == []
            # Restore a JSON backup containing both new and old records, then reload exactly.
            page.locator('#import-json').set_input_files(dict(name='synthetic.json', mimeType='application/json', buffer=json.dumps(expected).encode()))
            expect(record(page, 'Festival Title')).to_be_visible()
            assert stored(page) == expected == backup(page)
            page.reload(); assert stored(page) == expected
            # Two artists can also be registered together, not only added by editing.
            page.locator('[data-section=live]').click()
            page.locator('#add-live-trigger').click()
            page.locator('#live-title').fill('Two on creation')
            page.locator('#live-artists input').fill('One')
            page.locator('#live-artists > button').click()
            page.locator('#live-artists input').nth(1).fill('Two')
            for width in [320, 390, 768]:
                page.set_viewport_size(dict(width=width, height=844))
                for row in page.locator('#live-artists .live-artist-row').all():
                    assert row.locator('button').bounding_box()['height'] >= 44
                    assert row.locator('input').bounding_box()['width'] > 50
                    assert row.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
            page.set_viewport_size(dict(width=390, height=844))
            page.locator('#live-form > button').click()
            assert stored(page)['live'][0]['artists'] == ['One', 'Two']
            print('PASS artists: legacy/no conversion, one/multiple, add/edit/remove/empty, failure/retry/cancel, detail, reload, JSON:', lang)
            # Boundary values and unrated across all Live displays, save and reload.
            page.locator('[data-section=live]').click()
            for score, color in [(4.4, LIVE_CORAL), (4.5, LIVE_GOLD), (5.0, LIVE_GOLD), (0.0, LIVE_CORAL), (None, LIVE_CORAL)]:
                edit(page, 'Festival Title')
                slider = page.locator('[data-target=e-live-rating] .star-rating')
                if score is None:
                    page.locator('[data-target=e-live-rating] .rating-clear').click()
                else:
                    slider.press('Home')
                    for _ in range(round(score*10)):
                        slider.press('ArrowRight')
                assert_hearts(slider, color)
                save(page); page.reload(); page.locator('[data-section=live]').click()
                for mode in ['grid', 'list']:
                    page.locator(f'#{mode}-tab').click()
                    if score is None:
                        assert record(page, 'Festival Title').locator('.heart-symbol').count() == 0
                    else:
                        assert_hearts(record(page, 'Festival Title'), color)
                record(page, 'Festival Title').click()
                if score is None:
                    assert page.locator('#view-content .heart-symbol').count() == 0
                else:
                    assert_hearts(page.locator('#view-content'), color)
                page.locator('#view-close').click()
            print('PASS colors: 0/4.4/4.5/5/unrated, edit/save/reload/grid/list/detail:', lang)
        assert not errors, errors
        browser.close()
    server.shutdown()


if __name__ == '__main__':
    main()
