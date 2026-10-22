"""v0.3.22 UI/data regressions. Run: python -u tests/ui_v0322.py.
Uses an isolated Chromium profile and synthetic localStorage; blocks external requests.
"""
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
KEY = 'my-music-archive-pilot-v03'
GOLD, ROSE = '#e9bc78', '#E08AA1'


def album(title, **fields):
    return dict(entryId=title, id='', title=title, artist='Artist A', date='2026-01-02',
                release='2025', rating='', memo='keep me', photo='', **fields)


SEED = dict(version=3, listening=[
    {**album('Score 4.2', label='Merge', tags=['Electronic', 'AOTY2026', 'Electronic'], genre='Electronic'), 'rating': '8.4'},
    {**album('Score 4.3', label=' Merge ', tags='Electronic, AOTY2026, Electronic'), 'rating': '8.6'},
    {**album('Score 4.5', label='4AD', tags=[' AOTY2026 ', 'aoty2026'], genre='Ambient，Electronic'), 'rating': '9'},
    {**album('Score 5.0', label='', tags=[]), 'rating': '10'},
    album('Unrated', label='  ', tags=' ,  '),
    {**album('Score 0.0', tags=[' ', '']), 'rating': '0'},
    album('Legacy genre', label=None, tags=None, genre='Legacy'),
    album('Sentinel one', label='__mma_unset__', tags=['__mma_unset__']),
    album('Sentinel two', label='__mma_unset___', tags=['__mma_unset___']),
    album('Literal unset', label='未設定', tags=['未設定']),
    album('Old sentinel', label='__unset__', tags='__unset__'),
    album('Literal count', label='Merge (2)', tags=['Electronic (5)']),
], collection=[
    {**album('C 4.3', label='Merge', tags=['Electronic'], store='Shop', format='LP'), 'rating': '8.6'},
    {**album('C 4.2', label='4AD', tags=[]), 'rating': '8.4'},
    {**album('C 4.5', label='', tags=None), 'rating': '9'},
    {**album('C 5.0', label='Merge', tags=['AOTY2026'], genre='Legacy'), 'rating': '10'},
    album('C unrated', label='4AD', tags=''),
], live=[dict(entryId='live-old', title='Existing Live', date='2024-02-03', venue='Tokyo', rating='10', memo='keep live')])


class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *_args):
        pass


def stored(page):
    return page.evaluate('(key)=>JSON.parse(localStorage.getItem(key))', KEY)


def options(page, field):
    return page.locator(f'#{field}-filter option').evaluate_all('(els)=>Object.fromEntries(els.map(e=>[e.value,e.textContent]))')


def unset_value(page, field):
    return page.locator(f'#{field}-filter option[data-unset]').get_attribute('value')


def open_filters(page):
    if page.locator('#filters-wrap').is_hidden():
        page.locator('#filters-toggle').click()


def choose(page, field, value):
    open_filters(page)
    page.locator(f'#{field}-filter').select_option(value)


def clear_filters(page):
    for field in ['artist', 'label', 'tag']:
        choose(page, field, '')
    page.locator('#year-filter').fill('')
    page.locator('#release-year-filter').fill('')


def titles(page):
    return page.locator('#library button .title').all_text_contents()


def record(page, title):
    return page.locator('#library button').filter(has=page.get_by_text(title, exact=True))


def edit(page, title):
    record(page, title).click()
    page.locator('#view-edit').click()
    expect(page.locator('#modal')).to_have_class('modal open')


def save(page):
    page.locator('#save').click()
    expect(page.locator('#modal')).not_to_have_class('modal open')


def assert_stars(root, color, final_fraction=None):
    paths = root.locator('.star-fill path')
    assert paths.count() == 5
    assert paths.evaluate_all('(els)=>els.map(e=>e.getAttribute("fill"))') == [color] * 5
    if final_fraction is not None:
        width = root.locator('.star-fill').last.evaluate('(el)=>parseFloat(el.style.width)')
        assert abs(width - final_fraction) < 0.0001, width
    assert root.locator('.star-symbol>svg path').evaluate_all('(els)=>els.map(e=>e.getAttribute("fill"))') == ['#596675'] * 5


def main():
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
        page.evaluate('([key,seed])=>localStorage.setItem(key,JSON.stringify(seed))', [KEY, SEED])
        page.reload()
        assert stored(page) == SEED
        expect(page.locator('meta[name=application-version]')).to_have_attribute('content', '0.3.22')

        # Heading geometry, visual style, stable search controls, and all creation routes.
        for language in ['ja', 'en']:
            page.locator('#ui-language').select_option(language)
            for width in [320, 375, 390, 768, 1030]:
                page.set_viewport_size({'width': width, 'height': 844})
                for section in ['listening', 'collection', 'live']:
                    page.locator(f'[data-section={section}]').click()
                    trigger = page.locator('#add-live-trigger' if section == 'live' else '#manual-add-trigger')
                    heading = page.locator('#library-title' if section == 'live' else '#search-title')
                    t, h = trigger.bounding_box(), heading.bounding_box()
                    assert t['height'] >= 44 and t['width'] >= 44
                    assert h['x'] + h['width'] <= t['x'] - 3, (language, width, section, h, t)
                    assert max(t['y'], h['y']) < min(t['y']+t['height'], h['y']+h['height'])
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    if section != 'live':
                        expect(trigger).to_have_text('＋ 手動で追加' if language == 'ja' else '＋ Add Manually')
                        style = trigger.evaluate('(el)=>({bg:getComputedStyle(el).backgroundColor,border:getComputedStyle(el).borderWidth,color:getComputedStyle(el).color})')
                        assert style == dict(bg='rgba(0, 0, 0, 0)', border='0px', color='rgb(198, 231, 239)')
                        search = page.locator('#search-btn').bounding_box()
                        assert t['y']+t['height']+10 < search['y']
                        assert trigger.evaluate('(el)=>!el.closest("form")')
                        assert page.locator('#search-modes').evaluate('(el)=>el.previousElementSibling.contains(document.getElementById("search-title"))&&el.nextElementSibling.id==="search-form"')
                        page.locator('#query').fill('preserve input')
                        trigger.click()
                        expect(page.locator('#modal')).to_have_class('modal open')
                        page.locator('#close').click()
                        expect(page.locator('#query')).to_have_value('preserve input')
                    else:
                        expect(trigger).to_have_text('＋ 追加' if language == 'ja' else '+ Add')
                        trigger.click()
                        expect(page.locator('#live-create-modal')).to_have_class('modal open')
                        page.locator('#close-live-create').click()
                        expect(page.locator('#search-panel')).to_be_hidden()
        assert stored(page) == SEED and not external
        print('PASS 30 heading layouts (2 languages × 5 widths × 3 tabs), 44px targets, search separation, all creation dialogs; no archive writes')

        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('#ui-language').select_option('ja')
        page.locator('[data-section=listening]').click()
        labels, tags = options(page, 'label'), options(page, 'tag')
        for value, expected in [('Merge', 'Merge (2)'), ('4AD', '4AD (1)'), ('未設定', '未設定 (1)'), ('Merge (2)', 'Merge (2) (1)')]:
            assert labels[value] == expected
        for value, expected in [('Electronic', 'Electronic (3)'), ('AOTY2026', 'AOTY2026 (3)'), ('Ambient', 'Ambient (1)'), ('Legacy', 'Legacy (1)'), ('Electronic (5)', 'Electronic (5) (1)')]:
            assert tags[value] == expected
        assert labels[''] == 'すべてのレーベル' and tags[''] == 'すべてのタグ'
        assert labels[unset_value(page, 'label')] == '未設定 (4)'
        assert tags[unset_value(page, 'tag')] == '未設定 (3)'
        for field in ['label', 'tag']:
            for literal in ['__mma_unset__', '__mma_unset___', '__unset__', '未設定']:
                assert unset_value(page, field) != literal
                choose(page, field, literal)
                assert len(titles(page)) == 1
            choose(page, field, '')
        choose(page, 'label', unset_value(page, 'label'))
        assert set(titles(page)) == {'Score 5.0', 'Unrated', 'Score 0.0', 'Legacy genre'}
        choose(page, 'tag', unset_value(page, 'tag'))
        assert set(titles(page)) == {'Score 5.0', 'Unrated', 'Score 0.0'}
        choose(page, 'label', '')
        assert set(titles(page)) == {'Score 5.0', 'Unrated', 'Score 0.0'}
        choose(page, 'tag', 'Electronic')
        choose(page, 'label', 'Merge')
        choose(page, 'artist', 'Artist A')
        page.locator('#year-filter').fill('2026')
        page.locator('#release-year-filter').fill('2025')
        assert set(titles(page)) == {'Score 4.2', 'Score 4.3'}
        assert options(page, 'tag') == tags and options(page, 'label') == labels
        page.locator('#list-tab').click()
        expect(page.locator('#tag-filter')).to_have_value('Electronic')
        expect(page.locator('#label-filter')).to_have_value('Merge')
        page.locator('[data-section=collection]').click()
        assert options(page, 'tag')['Electronic'] == 'Electronic (1)'
        assert options(page, 'label')['Merge'] == 'Merge (2)'
        assert options(page, 'label')[unset_value(page, 'label')] == '未設定 (1)'
        assert options(page, 'tag')[unset_value(page, 'tag')] == '未設定 (3)'
        choose(page, 'label', unset_value(page, 'label'))
        choose(page, 'tag', unset_value(page, 'tag'))
        assert titles(page) == ['C 4.5']
        page.locator('[data-section=listening]').click()
        assert set(titles(page)) == {'Score 4.2', 'Score 4.3'}
        expect(page.locator('#tag-filter')).to_have_value('Electronic')
        page.locator('[data-section=collection]').click()
        assert titles(page) == ['C 4.5']
        expect(page.locator('#tag-filter option:checked')).to_have_attribute('data-unset', 'true')
        page.locator('#ui-language').select_option('en')
        assert options(page, 'label')[unset_value(page, 'label')] == 'Not set (1)'
        assert titles(page) == ['C 4.5']
        assert stored(page) == SEED
        print('PASS full-archive counts, legacy genres/string tags, duplicate tags, blanks/null/missing fields, collisions, compound filters, tab/view/language preservation')

        # Both view modes, detail view, and keyboard edits across the 4.2/4.3 boundary.
        for section, cases in [('listening', [('Score 0.0', GOLD, 0), ('Score 4.2', GOLD, 20), ('Score 4.3', ROSE, 30), ('Score 4.5', ROSE, 50), ('Score 5.0', ROSE, 100)]),
                               ('collection', [('C 4.2', GOLD, 20), ('C 4.3', ROSE, 30), ('C 4.5', ROSE, 50), ('C 5.0', ROSE, 100)])]:
            page.locator(f'[data-section={section}]').click()
            clear_filters(page)
            for mode in ['grid', 'list']:
                page.locator(f'#{mode}-tab').click()
                for title, color, fraction in cases:
                    assert_stars(record(page, title), color, fraction)
                unrated = record(page, 'Unrated' if section == 'listening' else 'C unrated')
                assert unrated.locator('.star-symbol').count() == 0
            title = cases[1][0] if section == 'listening' else cases[0][0]
            record(page, title).click()
            assert_stars(page.locator('#view-content'), GOLD, 20)
            page.locator('#view-edit').click()
            slider = page.locator('[data-target=rating] .star-rating')
            assert_stars(slider, GOLD, 20)
            slider.press('ArrowRight')
            expect(slider).to_have_attribute('aria-valuenow', '4.3')
            assert_stars(slider, ROSE, 30)
            save(page)
            assert_stars(record(page, title), ROSE, 30)
            assert next(r for r in stored(page)[section] if r['title'] == title)['rating'] == '8.6'
            edit(page, title)
            slider.press('ArrowLeft')
            assert_stars(slider, GOLD, 20)
            save(page)
            edit(page, title)
            page.locator('[data-target=rating] .rating-clear').click()
            assert_stars(slider, GOLD, 0)
            save(page)
            assert record(page, title).locator('.star-symbol').count() == 0
        print('PASS gold at 0/4.2, exact rose at 4.3/4.5/5, fractional masks, both archives/views/details/editing and clearing')

        # Counts refresh on real form saves, edits and deletion, including zero-match selections.
        for section in ['listening', 'collection']:
            page.locator(f'[data-section={section}]').click()
            clear_filters(page)
            before = stored(page)
            page.locator('#manual-add-trigger').click()
            page.locator('#manual-artist').fill('New Artist')
            page.locator('#manual-title').fill('New Entry')
            page.locator('#label').fill('Merge')
            page.locator('#tags').fill('Electronic, New Tag, New Tag')
            save(page)
            assert len(stored(page)[section]) == len(before[section]) + 1
            assert options(page, 'label')['Merge'] == 'Merge (3)'
            assert options(page, 'tag')['New Tag'] == 'New Tag (1)'
            choose(page, 'tag', 'New Tag')
            assert titles(page) == ['New Entry']
            edit(page, 'New Entry')
            page.locator('#label').fill('4AD')
            page.locator('#tags').fill('Changed Tag')
            save(page)
            assert titles(page) == []
            assert options(page, 'tag')['New Tag'] == 'New Tag (0)'
            expect(page.locator('#tag-filter')).to_have_value('New Tag')
            other = 'collection' if section == 'listening' else 'listening'
            page.locator(f'[data-section={other}]').click()
            page.locator(f'[data-section={section}]').click()
            expect(page.locator('#tag-filter')).to_have_value('New Tag')
            choose(page, 'tag', 'Changed Tag')
            edit(page, 'New Entry')
            page.locator('#label').fill('  ')
            page.locator('#tags').fill(' , ')
            save(page)
            assert options(page, 'tag')['Changed Tag'] == 'Changed Tag (0)'
            label_unset, tag_unset = unset_value(page, 'label'), unset_value(page, 'tag')
            assert options(page, 'label')[label_unset] == f'Not set ({5 if section == "listening" else 2})'
            assert options(page, 'tag')[tag_unset] == 'Not set (4)'
            choose(page, 'tag', tag_unset)
            choose(page, 'label', label_unset)
            assert 'New Entry' in titles(page)
            # A real name introduced by editing must not steal an active unset selection.
            edit(page, 'New Entry')
            page.locator('#label').fill(label_unset)
            page.locator('#tags').fill(tag_unset)
            save(page)
            assert unset_value(page, 'label') != label_unset
            assert unset_value(page, 'tag') != tag_unset
            for field in ['label', 'tag']:
                expect(page.locator(f'#{field}-filter option:checked')).to_have_attribute('data-unset', 'true')
            assert 'New Entry' not in titles(page)
            choose(page, 'label', label_unset)
            choose(page, 'tag', tag_unset)
            assert titles(page) == ['New Entry']
            edit(page, 'New Entry')
            page.locator('#delete').click()
            page.locator('#delete-accept').click()
            expect(page.locator('#modal')).not_to_have_class('modal open')
            assert options(page, 'tag')[tag_unset] == tag_unset+' (0)'
            assert options(page, 'label')['Merge'] == 'Merge (2)'
            assert len(stored(page)[section]) == len(before[section])
            clear_filters(page)
        print('PASS manual save/edit/delete in both archives; counts update and zero-match selections survive redraw/tab changes')

        # Live shares album colors, with its existing creation/edit/delete/sort/view controls.
        page.locator('[data-section=live]').click()
        page.locator('#grid-tab').click()
        assert_stars(record(page, 'Existing Live'), ROSE, 100)
        page.locator('#add-live-trigger').click()
        page.locator('#live-title').fill('New Live')
        page.locator('#live-venue').fill('Osaka')
        live_slider = page.locator('[data-target=live-rating] .star-rating')
        live_slider.press('End')
        assert_stars(live_slider, ROSE, 100)
        page.locator('#live-form > button').click()
        expect(page.locator('#live-create-modal')).not_to_have_class('modal open')
        assert len(stored(page)['live']) == 2
        page.locator('#list-tab').click()
        edit(page, 'New Live')
        assert_stars(page.locator('[data-target=e-live-rating] .star-rating'), ROSE, 100)
        page.locator('#e-live-venue').fill('Kyoto')
        save(page)
        assert stored(page)['live'][0]['venue'] == 'Kyoto'
        page.locator('#sort-toggle').click()
        page.locator('#sort').select_option('rating-desc')
        assert set(titles(page)) == {'New Live', 'Existing Live'}
        edit(page, 'New Live')
        page.locator('#delete').click()
        page.locator('#delete-accept').click()
        expect(page.locator('#modal')).not_to_have_class('modal open')
        assert stored(page)['live'] == SEED['live']
        print('PASS Live create/edit/delete, rose at 5.0, list/grid, sorting and existing record intact')

        # JSON round-trip, cancelled import, and CSV export preserve the current storage format.
        current = stored(page)
        with page.expect_download() as info:
            page.locator('#export-json').click()
        exported = Path(info.value.path()).read_text()
        assert json.loads(exported) == current
        with page.expect_download() as info:
            page.locator('#export-csv').click()
        csv = Path(info.value.path()).read_text(encoding='utf-8-sig')
        assert 'rating_5' in csv and 'Existing Live' in csv
        payload = dict(name='backup.json', mimeType='application/json', buffer=exported.encode())
        def dismiss(dialog):
            dialog.dismiss()
        page.on('dialog', dismiss)
        page.locator('#import-json').set_input_files(payload)
        expect(page.locator('#import-json')).to_have_value('')
        assert stored(page) == current
        page.remove_listener('dialog', dismiss)
        page.on('dialog', lambda dialog: dialog.accept())
        page.locator('#import-json').set_input_files(payload)
        expect(page.locator('#import-json')).to_have_value('')
        assert stored(page) == current
        page.reload()
        assert stored(page) == current
        # Original records are byte-equivalent except the two explicitly edited ratings.
        for archive in ['listening', 'collection', 'live']:
            for original in SEED[archive]:
                actual = next(r for r in current[archive] if r['entryId'] == original['entryId'])
                if original['title'] in ['Score 4.2', 'C 4.2']:
                    assert actual['rating'] == ''
                    for key, value in original.items():
                        if key not in ['rating', 'tags', 'genre']:
                            assert actual[key] == value
                    assert actual['genre'] == ''
                    assert actual['tags'] == (['Electronic', 'AOTY2026'] if archive == 'listening' else [])
                else:
                    assert actual == original
        page.screenshot(path='/tmp/mma-v0322-listening.png', full_page=True)
        page.locator('[data-section=live]').click()
        page.screenshot(path='/tmp/mma-v0322-live.png', full_page=True)
        assert not errors, errors
        print('PASS exact JSON backup/restore, cancelled import, CSV, reload persistence, unrelated fields/records intact; no JS errors')
        browser.close()
    server.shutdown()


if __name__ == '__main__':
    main()
