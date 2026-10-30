"""Search/Live UI regressions with synthetic API and archive data; no external API calls.
Run: python -u tests/search_live_ui.py
"""
import copy
import json
import os
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import KEY, QuietHandler, SEED, stored, record, edit, save, assert_hearts, assert_stars, GOLD


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    seed = copy.deepcopy(SEED)
    seed['live'] = [dict(entryId=f'live-{i}', title=f'Live {value}', rating=value, venue='Tokyo', date='2026-01-02', memo='Keep')
                    for i, value in enumerate(['', '0', '8.4', '8.5', '8.6', '9', '10', None])]
    rows = [dict(id=f'work-{i}', title='Title Live', **{'primary-type': ['Album', 'EP', 'Single', 'Other'][i % 4],
            'first-release-date': str(1900+i), 'artist-credit': [dict(name='Synthetic Artist')]}) for i in range(105)]
    rows[101].update(title='ＴＩＴＬＥ', **{'first-release-date': '2020'})
    rows[102].update(title='Title', **{'first-release-date': ''})
    rows[103]['first-release-date'] = ''
    rows[104].pop('primary-type')
    calls, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM', '/usr/bin/chromium'), args=['--no-sandbox'])
        context = browser.new_context(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True, locale='ja-JP', accept_downloads=True)

        def api(route):
            from urllib.parse import urlparse, parse_qs
            u = urlparse(route.request.url)
            if u.hostname != 'musicbrainz.org':
                route.abort(); return
            params = parse_qs(u.query)
            calls.append(params)
            if '/artist/' in u.path:
                result = dict(artists=[dict(id='artist', name='Synthetic Artist', aliases=[])])
            elif 'artist' in params:
                result = {'release-group-count': 3, 'release-groups': [rows[2], rows[1], rows[0]]}
            else:
                offset = int(params.get('offset', ['0'])[0])
                result = dict(count=len(rows), **{'release-groups': rows[offset:offset+100]})
            route.fulfill(json=result)

        context.route('https://**/*', api)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: d.accept())
        page.goto(base)
        page.evaluate('([key,data])=>localStorage.setItem(key,JSON.stringify(data))', [KEY, seed])
        page.reload()
        for lang in ['ja', 'en']:
            ja = lang == 'ja'
            page.locator('#ui-language').select_option(lang)
            page.locator('[data-section=live]').click()
            expect(page.locator('#add-live-trigger')).to_have_text('＋ ライブを追加' if ja else '＋ Add Live')
            page.locator('#add-live-trigger').click()
            expect(page.locator('label[for=live-rating]')).to_contain_text('スコア' if ja else 'Score')
            slider = page.locator('[data-target=live-rating] .star-rating')
            expect(slider).to_have_attribute('aria-label', 'ハートをなぞってスコアを設定（5点満点）' if ja else 'Slide across hearts to set score out of 5')
            expect(slider).to_have_attribute('aria-valuetext', '未評価' if ja else 'Unrated')
            assert_hearts(slider, final_fraction=0)
            slider.press('End'); slider.press('ArrowLeft')
            expect(page.locator('#live-rating')).to_have_value('9.8')
            # Pointer and keyboard operate the same fractional input.
            box = slider.bounding_box()
            page.mouse.click(box['x']+box['width']/2, box['y']+box['height']/2)
            expect(page.locator('#live-rating')).to_have_value('5.0')
            page.locator('#close-live-create').click()
            for mode in ['grid', 'list']:
                page.locator(f'#{mode}-tab').click()
                rated = record(page, 'Live 8.4')
                assert_hearts(rated, final_fraction=20)
                expect(rated.locator('.rating-readout')).to_have_attribute('aria-label', 'スコア 4.2／5点' if ja else 'Score 4.2 out of 5')
                if mode == 'list':
                    expect(rated).to_contain_text('スコア' if ja else 'Score')
                assert record(page, 'Live ').locator('.heart-symbol').count() == 0
            for value in ['0', '8.4', '8.5', '8.6', '9', '10', None]:
                record(page, f'Live {value}').click()
                expect(page.locator('#view-content .k').filter(has_text='スコア' if ja else 'Score')).to_have_count(1)
                if value is not None:
                    assert_hearts(page.locator('#view-content'))
                page.locator('#view-edit').click()
                expect(page.locator('label[for=e-live-rating]')).to_contain_text('スコア' if ja else 'Score')
                expect(page.locator('#e-live-rating')).to_have_value('' if value is None else value)
                assert_hearts(page.locator('[data-target=e-live-rating]'))
                page.locator('#close').click()
            expect(page.locator('#sort option[value=rating-desc]')).to_have_text('スコア：高い順' if ja else 'Score: High to Low')
            for section in ['listening', 'collection']:
                page.locator(f'[data-section={section}]').click()
                expect(page.locator('#sort option[value=rating-desc]')).to_have_text('スコア：高い順' if ja else 'Score: High to Low')
                edit(page, 'Score 4.2' if section == 'listening' else 'C 4.2')
                expect(page.locator('label[for=rating]')).to_contain_text('スコア' if ja else 'Score')
                assert_stars(page.locator('[data-target=rating]'), GOLD, 20)
                assert page.locator('[data-target=rating] .heart-symbol').count() == 0
                page.locator('#close').click()
        assert stored(page) == seed
        print('PASS 1: JA/EN create/edit/detail/list/grid/sort labels, Live coral/gold hearts, keyboard/pointer, unrated/null, legacy precision, album stars; no data writes')

        page.locator('[data-section=listening]').click()
        page.locator('[data-search-mode=title]').click()
        page.locator('#query').fill('Title')
        page.locator('#search-btn').click()
        expect(page.locator('#results .result')).to_have_count(30)
        assert page.locator('#results .title').first.text_content() == 'Title Live'
        for count in [60, 90, 105]:
            page.locator('#more-results').click()
            expect(page.locator('#results .result')).to_have_count(count)
        names = page.locator('#results .title').all_text_contents()
        assert names[:2] == ['ＴＩＴＬＥ', 'Title']
        dates = page.locator('#results .result .grow').evaluate_all('(els)=>els.map(e=>e.lastElementChild.textContent)')
        assert dates[0].startswith('2020') and dates[1].startswith('Release date unknown')
        assert dates[2].startswith('2004') and dates[-1].startswith('Release date unknown')
        assert sum('offset' in c for c in calls) == 2
        for typ in ['Album', 'EP', 'Single']:
            assert any(d.endswith(' · '+typ) for d in dates)
        assert not any('Other' in d or 'undefined' in d for d in dates)
        expect(page.locator('#more-results')).to_be_hidden()
        page.locator('#results .result').first.locator('button').click()
        expect(page.locator('#manual-title')).to_have_value('ＴＩＴＬＥ')
        expect(page.locator('#manual-artist')).to_have_value('Synthetic Artist')
        save(page)
        added = stored(page)['listening'][0]
        assert added['id'] == 'work-101' and added['release'] == '2020'
        assert 'primary-type' not in added  # UI-only metadata does not enter the backup format.
        print('PASS 2: two raw pages, four display batches, global re-sort, exact/partial dates/unknown, all types/unclassified, add album metadata and unchanged saved schema')

        page.locator('[data-search-mode=artist]').click()
        page.locator('#query').fill('Synthetic Artist')
        page.locator('#search-btn').click()
        expect(page.locator('#results .result')).to_have_count(3)
        meta = page.locator('#results .result .grow').evaluate_all('(els)=>els.map(e=>e.lastElementChild.textContent)')
        assert [d.split(' · ')[-1] for d in meta] == ['Album', 'EP', 'Single']
        print('PASS 3: artist mode retains Album/EP/Single priority and displays type beside release date')

        current = stored(page)
        with page.expect_download() as dl:
            page.locator('#export-json').click()
        payload = Path(dl.value.path()).read_bytes()
        assert json.loads(payload) == current
        page.locator('#import-json').set_input_files(dict(name='backup.json', mimeType='application/json', buffer=payload))
        expect(page.locator('#import-json')).to_have_value('')
        assert stored(page) == current
        page.reload()
        assert stored(page) == current and current['live'] == seed['live']
        page.locator('[data-section=live]').click()
        page.screenshot(path='/tmp/mma-search-live-ui.png', full_page=True)
        assert not errors, errors
        print('PASS 4: exact JSON export/restore/reload and all original Live rating values; no JS errors')
        browser.close()
    server.shutdown()


if __name__ == '__main__':
    main()
