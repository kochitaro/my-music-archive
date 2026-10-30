"""MLA: synthetic album editing, partial dates, bilingual score labels and legacy storage."""
import copy
import json
import os
import re
import threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, stored, record, edit, save, SEED, assert_stars, GOLD, ROSE
from data_preservation import backup, seed_data


def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM', '/usr/bin/chromium'), args=['--no-sandbox'])
        context = browser.new_context(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True, accept_downloads=True)
        context.route('https://**/*', lambda r: r.abort())
        context.add_init_script("""const set=Storage.prototype.setItem;
        Storage.prototype.setItem=function(k,v){if(window.failWrite&&k==='my-music-archive-pilot-v03')throw new DOMException('Synthetic','QuotaExceededError');return set.call(this,k,v)};""")
        page = context.new_page()
        errors, alerts = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: (alerts.append(d.message), d.accept()))
        page.goto(base)

        def reset(seed, lang='en'):
            page.evaluate('([k,v,l])=>{failWrite=false;localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",l)}', [KEY, seed, lang])
            page.reload()

        def parts(value):
            y, m, d = (value.split('-') + ['', ''])[:3]
            wrap = page.locator('#release-edit-parts')
            wrap.locator('input').fill(y)
            if len(y) == 4 and y.isdigit() and int(y) > 0:
                wrap.locator('select').nth(0).select_option(m)
                if m:
                    wrap.locator('select').nth(1).select_option(d)

        for lang in ['ja', 'en']:
            reset(SEED, lang)
            expect(page).to_have_title('My Listening Archive')
            expect(page.locator('h1')).to_have_text('My Listening Archive')
            assert stored(page) == SEED
            for width in [320, 390, 768]:
                page.set_viewport_size(dict(width=width, height=844))
                assert page.locator('.brand').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
            page.set_viewport_size(dict(width=390, height=844))
            for section in ['listening', 'collection', 'live']:
                page.locator(f'[data-section={section}]').click()
                term = ('評価' if lang == 'ja' else 'Rating') if section == 'collection' else ('スコア' if lang == 'ja' else 'Score')
                expect(page.locator('#sort option[value=rating-desc]')).to_contain_text(term)
                title = {'listening':'Score 4.2','collection':'C 4.2','live':'Existing Live'}[section]
                record(page, title).click()
                expect(page.locator('#view-content .k').filter(has_text=term)).to_have_count(1)
                expect(page.locator('#view-content .rating-readout')).to_have_attribute('aria-label', re.compile(term))
                page.locator('#view-edit').click()
                target = 'e-live-rating' if section == 'live' else 'rating'
                expect(page.locator(f'label[for={target}]')).to_contain_text(term)
                expect(page.locator(f'[data-target={target}] .star-rating')).to_have_attribute('aria-label', re.compile(term.lower()))
                if section != 'collection':
                    slider = page.locator(f'[data-target={target}] .star-rating')
                    slider.scroll_into_view_if_needed()
                    box = slider.bounding_box()
                    x, y = box['x'], box['y']+box['height']/2
                    page.touchscreen.tap(x+box['width']*.4, y)
                    expect(page.locator('#'+target)).to_have_value('4.0')
                    page.mouse.move(x+box['width']*.4, y)
                    page.mouse.down()
                    page.mouse.move(x+box['width']*.86, y, steps=5)
                    page.mouse.up()
                    expect(page.locator('#'+target)).to_have_value('8.6')
                    page.locator(f'[data-target={target}] .rating-clear').click()
                    expect(slider).to_have_attribute('aria-valuetext', '未評価' if lang == 'ja' else 'Unrated')
                page.locator('#close').click()
            page.locator('[data-section=listening]').click()
            for title, color, fraction in [('Score 4.2', GOLD, 20), ('Score 4.3', ROSE, 30)]:
                edit(page, title)
                assert_stars(page.locator('[data-target=rating]'), color, fraction)
                page.locator('#close').click()
            # A live language switch and tab switch must not retain the previous archive's label.
            page.locator('#ui-language').select_option('en' if lang == 'ja' else 'ja')
            page.locator('[data-section=collection]').click()
            edit(page, 'C 4.2')
            expect(page.locator('label[for=rating]')).to_contain_text('Rating' if lang == 'ja' else '評価')
            page.locator('#close').click()
            assert stored(page) == SEED
            print('PASS branding, widths, legacy key, bilingual labels/a11y, Collection, star boundaries:', lang)

        for section in ['listening', 'collection']:
            for mb in [False, True]:
                seed = seed_data()
                row = seed[section][0]
                row['id'] = '11111111-2222-3333-4444-555555555555' if mb else ''
                row['genre'] = ''  # existing editor consolidates legacy genres into tags
                row['tags'] = ['Tag']
                reset(seed)
                page.locator(f'[data-section={section}]').click()
                edit(page, section)
                expect(page.locator('#manual-title')).to_be_visible()
                page.locator('#manual-title').fill('  Revised album  ')
                page.evaluate('failWrite=true')
                page.locator('#save').click()
                assert stored(page) == seed == backup(page)
                page.evaluate('failWrite=false')
                save(page)
                expected = copy.deepcopy(seed)
                expected[section][0]['title'] = 'Revised album'
                assert stored(page) == expected
                expect(record(page, 'Revised album')).to_be_visible()
                record(page, 'Revised album').click()
                expect(page.locator('#view-content .title')).to_have_text('Revised album')
                page.locator('#view-close').click()
                page.reload()
                assert stored(page) == expected == backup(page)
                page.locator('#import-json').set_input_files(dict(name='my-music-archive-backup-v0310.json', mimeType='application/json', buffer=json.dumps(expected).encode()))
                assert stored(page) == expected
                page.reload()
                page.locator(f'[data-section={section}]').click()
                edit(page, 'Revised album')
                page.locator('#manual-title').fill('   ')
                page.locator('#save').click()
                expect(page.locator('#modal')).to_have_class('modal open')
                assert stored(page) == expected
                page.locator('#close').click()
                print('PASS title edit, failure/retry, all other fields/IDs, reload, old MMA JSON, blank validation:', section, mb)

            for value in ['2024', '2024-02', '2024-02-29', '', '2023-02-28', '2000-02-29', '1900-02-28']:
                seed = seed_data()
                seed[section][0]['release'] = value
                reset(seed)
                page.locator(f'[data-section={section}]').click()
                edit(page, section)
                displayed = page.locator('#release-edit-parts .date-part').evaluate_all('(els)=>els.map(e=>e.value).filter(Boolean).join("-")')
                assert displayed == value
                parts(value)
                save(page)
                assert stored(page)[section][0]['release'] == value
                page.reload()
                assert stored(page)[section][0]['release'] == value
            reset(seed_data())
            page.locator(f'[data-section={section}]').click()
            edit(page, section)
            for invalid in ['123', '0000', 'abcd']:
                parts(invalid)
                before = stored(page)
                page.locator('#save').click()
                assert stored(page) == before
                expect(page.locator('#modal')).to_have_class('modal open')
            for year, count in [('2023', 28), ('2024', 29), ('1900', 28), ('2000', 29)]:
                parts(year+'-02')
                days = page.locator('#release-edit-parts select').nth(1)
                expect(days.locator('option')).to_have_count(count+1)
                assert days.locator('option[value="30"]').count() == 0
            parts('2024-01-31')
            page.locator('#release-edit-parts select').nth(0).select_option('02')
            expect(page.locator('#release-edit-parts select').nth(1)).to_have_value('')
            save(page)
            assert stored(page)[section][0]['release'] == '2024-02'
            print('PASS release precision, empty, re-edit/reload, invalid years/days, leap centuries, no invented day:', section)
        page.goto(base+'/search-test/')
        expect(page).to_have_title('MLA Search Lab')
        expect(page.locator('h1')).to_have_text('My Listening Archive / Search Lab')
        page.screenshot(path='/tmp/mla-search-lab.png', full_page=True)
        print('PASS Search Lab branding; unchanged search.js and no storage access (source review)')
        assert not errors, errors
        browser.close()
    server.shutdown()


if __name__ == '__main__':
    main()
