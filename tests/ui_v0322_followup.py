"""Follow-up regressions: python -u tests/ui_v0322_followup.py.
Reuses v0.3.22 UI helpers; isolated synthetic data, no external requests.
"""
import copy
import json
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import (SEED, KEY, GOLD, ROSE, QuietHandler, album, stored, options,
                     unset_value, open_filters, choose, titles, record, edit, save, assert_stars, assert_hearts)


def main():
    seed = copy.deepcopy(SEED)
    seed['listening'][0]['store'] = 'Listening only store'
    seed['collection'] = [
        album('DU 1', label='Merge', tags=['Electronic'], store='ディスクユニオン'),
        album('DU 2', label='Merge', tags=['Other'], store=' ディスクユニオン '),
        album('DU 3', label='4AD', tags=['Electronic'], store='ディスクユニオン'),
        album('Tower 1', label='Merge', tags=[], store='タワーレコード'),
        album('Tower 2', label='4AD', tags=[], store='タワーレコード'),
        album('HMV 1', label='4AD', tags=[], store='HMV'),
        album('Blank store', label='', tags=[], store=''),
        album('Whitespace store', label='', tags=[], store=' \t '),
        album('Null store', label='', tags=[], store=None),
        album('Missing store', label='', tags=[]),
        album('Literal sentinel', label='', tags=[], store='__unset__'),
        album('Literal unset', label='', tags=[], store='店舗未設定'),
    ]
    seed['live'] = [dict(entryId=f'live-{score}', title=f'Live {score}', date='2026-01-02',
                         venue='Tokyo', rating=raw, memo='preserve')
                    for score, raw in [('0.0', '0'), ('4.2', '8.4'), ('4.3', '8.6'), ('4.5', '9'), ('5.0', '10'), ('unrated', '')]]
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    errors, external = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=os.environ.get('MMA_CHROMIUM', '/usr/bin/chromium'), args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, locale='ja-JP', accept_downloads=True)
        context.route('https://**/*', lambda route: (external.append(route.request.url), route.abort()))
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(base)
        page.evaluate('([key,seed])=>localStorage.setItem(key,JSON.stringify(seed))', [KEY, seed])
        page.reload()
        assert stored(page) == seed
        expect(page.locator('#manual-add-trigger')).to_have_text('＋ 手動で追加')
        # Persisted language, both tabs, repeated changes, and reload must all translate.
        for language in ['en', 'ja', 'en', 'ja']:
            page.locator('#ui-language').select_option(language)
            expected = '＋ 手動で追加' if language == 'ja' else '＋ Add Manually'
            for section in ['listening', 'collection']:
                page.locator(f'[data-section={section}]').click()
                expect(page.locator('#manual-add-trigger')).to_have_text(expected)
                page.locator('#manual-add-trigger').click()
                expect(page.locator('#modal')).to_have_class('modal open')
                page.locator('#close').click()
            page.reload()
            expect(page.locator('#manual-add-trigger')).to_have_text(expected)
        assert stored(page) == seed and not external
        print('PASS Japanese/English manual action on both tabs, repeated language changes, persisted language/reload, unchanged modal route/data')

        page.locator('[data-section=collection]').click()
        stores = options(page, 'store')
        assert stores[''] == 'すべての購入店舗'
        for name, count in [('ディスクユニオン', 3), ('タワーレコード', 2), ('HMV', 1), ('__unset__', 1), ('店舗未設定', 1)]:
            assert stores[name] == f'{name} ({count})'
        unset = unset_value(page, 'store')
        assert unset != '__unset__'
        assert stores[unset] == '店舗未設定 (4)'
        assert 'Listening only store' not in stores
        choose(page, 'store', 'ディスクユニオン')
        assert set(titles(page)) == {'DU 1', 'DU 2', 'DU 3'}
        choose(page, 'label', 'Merge')
        choose(page, 'tag', 'Electronic')
        choose(page, 'artist', 'Artist A')
        page.locator('#year-filter').fill('2026')
        page.locator('#release-year-filter').fill('2025')
        assert titles(page) == ['DU 1']
        assert options(page, 'store') == stores
        for field in ['artist', 'label', 'tag']:
            choose(page, field, '')
        page.locator('#year-filter').fill('')
        page.locator('#release-year-filter').fill('')
        choose(page, 'store', unset)
        assert set(titles(page)) == {'Blank store', 'Whitespace store', 'Null store', 'Missing store'}
        choose(page, 'label', unset_value(page, 'label'))
        choose(page, 'tag', unset_value(page, 'tag'))
        assert len(titles(page)) == 4
        page.locator('#list-tab').click()
        page.locator('[data-section=live]').click()
        page.locator('[data-section=collection]').click()
        expect(page.locator('#store-filter option:checked')).to_have_attribute('data-unset', 'true')
        assert len(titles(page)) == 4
        page.locator('#ui-language').select_option('en')
        assert options(page, 'store')[unset_value(page, 'store')] == 'Store not set (4)'
        assert len(titles(page)) == 4
        for field in ['label', 'tag']:
            choose(page, field, '')
        for name, expected in [('HMV', {'HMV 1'}), ('__unset__', {'Literal sentinel'}), ('店舗未設定', {'Literal unset'})]:
            choose(page, 'store', name)
            assert set(titles(page)) == expected
        choose(page, 'store', '')
        assert stored(page) == seed
        print('PASS Collection-only counts, blanks/null/missing stores, raw values/collisions, compound filters, stable counts and tab/view/language selection')

        # Save, rename, clear and delete through the unchanged registration/edit forms.
        page.locator('#manual-add-trigger').click()
        page.locator('#manual-artist').fill('New Artist')
        page.locator('#manual-title').fill('Store update')
        page.locator('#store').fill('ディスクユニオン')
        save(page)
        assert options(page, 'store')['ディスクユニオン'] == 'ディスクユニオン (4)'
        choose(page, 'store', 'ディスクユニオン')
        edit(page, 'Store update')
        page.locator('#store').fill('New store')
        save(page)
        expect(page.locator('#store-filter')).to_have_value('ディスクユニオン')
        assert options(page, 'store')['ディスクユニオン'] == 'ディスクユニオン (3)'
        choose(page, 'store', 'New store')
        edit(page, 'Store update')
        page.locator('#store').fill('  ')
        save(page)
        expect(page.locator('#store-filter')).to_have_value('New store')
        assert options(page, 'store')['New store'] == 'New store (0)'
        assert titles(page) == []
        page.locator('[data-section=listening]').click()
        page.locator('[data-section=collection]').click()
        expect(page.locator('#store-filter')).to_have_value('New store')
        choose(page, 'store', unset_value(page, 'store'))
        assert options(page, 'store')[unset_value(page, 'store')] == 'Store not set (5)'
        assert len(titles(page)) == 5
        # Renaming into the current unset identifier cannot change the selected condition.
        old_unset = unset_value(page, 'store')
        edit(page, 'Store update')
        page.locator('#store').fill(old_unset)
        save(page)
        assert unset_value(page, 'store') != old_unset
        expect(page.locator('#store-filter option:checked')).to_have_attribute('data-unset', 'true')
        assert options(page, 'store')[unset_value(page, 'store')] == 'Store not set (4)'
        assert len(titles(page)) == 4
        choose(page, 'store', old_unset)
        assert titles(page) == ['Store update']
        edit(page, 'Store update')
        page.locator('#delete').click()
        page.locator('#delete-accept').click()
        expect(page.locator('#modal')).not_to_have_class('modal open')
        expect(page.locator('#store-filter')).to_have_value(old_unset)
        assert options(page, 'store')[old_unset] == old_unset+' (0)'
        choose(page, 'store', '')
        assert stored(page) == seed
        print('PASS store counts refresh on registration/edit/delete, unset updates, zero-count selection/tab preservation and dynamic identifier collisions')

        page.locator('[data-section=live]').click()
        cases = [('0.0', ROSE, 0), ('4.2', ROSE, 20), ('4.3', ROSE, 30), ('4.5', ROSE, 50), ('5.0', ROSE, 100)]
        for mode in ['grid', 'list']:
            page.locator(f'#{mode}-tab').click()
            for score, color, fraction in cases:
                assert_hearts(record(page, f'Live {score}'), color, fraction)
            assert record(page, 'Live unrated').locator('.star-symbol').count() == 0
        for score, color, fraction in cases:
            record(page, f'Live {score}').click()
            assert_hearts(page.locator('#view-content'), color, fraction)
            page.locator('#view-edit').click()
            assert_hearts(page.locator('[data-target=e-live-rating] .star-rating'), color, fraction)
            page.locator('#close').click()
        record(page, 'Live unrated').click()
        assert page.locator('#view-content .star-symbol').count() == 0
        page.locator('#view-edit').click()
        slider = page.locator('[data-target=e-live-rating] .star-rating')
        assert_hearts(slider, ROSE, 0)
        expect(slider).to_have_attribute('aria-valuetext', 'Unrated')
        page.locator('#close').click()
        edit(page, 'Live 4.2')
        slider.press('ArrowRight')
        expect(slider).to_have_attribute('aria-valuenow', '4.3')
        assert_hearts(slider, ROSE, 30)
        save(page)
        assert_hearts(record(page, 'Live 4.2'), ROSE, 30)
        assert next(r for r in stored(page)['live'] if r['title'] == 'Live 4.2')['rating'] == '8.6'
        edit(page, 'Live 4.2')
        slider.press('ArrowLeft')
        assert_hearts(slider, ROSE, 20)
        save(page)
        assert_hearts(record(page, 'Live 4.2'), ROSE, 20)
        # Creation UI shares the same criterion, including clearing back to unrated.
        page.locator('#add-live-trigger').click()
        slider = page.locator('[data-target=live-rating] .star-rating')
        slider.press('End')
        assert_hearts(slider, ROSE, 100)
        page.locator('[data-target=live-rating] .rating-clear').click()
        assert_hearts(slider, ROSE, 0)
        page.locator('#close-live-create').click()
        assert stored(page) == seed
        print('PASS Live 0/4.2/4.3/4.5/5 in grid/list/detail/edit, unchanged fractional masks/unrated, 0.1 edit/save pink hearts and creation UI')

        # No saved data changes remain; JSON round-trip must preserve every record exactly.
        with page.expect_download() as download:
            page.locator('#export-json').click()
        exported = Path(download.value.path()).read_text()
        assert json.loads(exported) == seed
        page.on('dialog', lambda dialog: dialog.accept())
        page.locator('#import-json').set_input_files(dict(name='backup.json', mimeType='application/json', buffer=exported.encode()))
        expect(page.locator('#import-json')).to_have_value('')
        page.reload()
        assert stored(page) == seed
        page.locator('[data-section=collection]').click()
        assert options(page, 'store')['ディスクユニオン'] == 'ディスクユニオン (3)'
        page.locator('#ui-language').select_option('ja')
        open_filters(page)
        page.screenshot(path='/tmp/mma-v0322-followup-collection.png', full_page=True)
        page.locator('[data-section=live]').click()
        page.screenshot(path='/tmp/mma-v0322-followup-live.png', full_page=True)
        assert not errors, errors
        assert not external, external
        print('PASS exact original records/storage and JSON backup/restore/reload, refreshed counts; no external requests or JavaScript errors')
        browser.close()
    server.shutdown()


if __name__ == '__main__':
    main()
