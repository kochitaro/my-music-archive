"""Synthetic Collection score regressions and before/after brand layout evidence."""
import json
import os
import re
import subprocess
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, SEED, QuietHandler, stored, record, edit, save, assert_stars, GOLD, ROSE

BASE_SHA = 'f264ee6ff928f96dfdbda5ef0f32b78b5962e8d0'


def main():
    artifacts = Path(os.environ.get('MLA_UI_ARTIFACT_DIR', '/tmp/mla-collection-score-brand'))
    artifacts.mkdir(parents=True, exist_ok=True)
    baseline = subprocess.check_output(['git', 'show', BASE_SHA+':index.html'], cwd=ROOT)
    current = (ROOT/'index.html').read_bytes()
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    measurements = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM', '/usr/bin/chromium'), args=['--no-sandbox'])
        context = browser.new_context(viewport=dict(width=390, height=844), is_mobile=True, has_touch=True, locale='ja-JP')
        context.route('https://**/*', lambda r: r.abort())
        context.route(base+'/', lambda r: r.fulfill(body=current, content_type='text/html'))
        page = context.new_page()
        errors, alerts = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('dialog', lambda d: (alerts.append(d.message), d.accept()))
        page.goto(base)
        for width in [320, 375, 390, 430, 768]:
            pair = {}
            page.set_viewport_size(dict(width=width, height=844))
            for version, html in [('before', baseline), ('after', current)]:
                context.unroute(base+'/')
                def serve_document(document):
                    return lambda route: route.fulfill(body=document, content_type='text/html')
                context.route(base+'/', serve_document(html))
                page.reload()
                metrics = page.locator('.brand h1').evaluate('''e=>{
                  const s=getComputedStyle(e),r=e.getBoundingClientRect(),logo=document.querySelector('.brandmark').getBoundingClientRect();
                  const range=document.createRange();range.selectNodeContents(e);const text=range.getBoundingClientRect();
                  return {font:parseFloat(s.fontSize),family:s.fontFamily,weight:s.fontWeight,color:s.color,spacing:s.letterSpacing,
                    textWidth:text.width,available:document.querySelector('.brand').getBoundingClientRect().right-r.left,
                    fits:text.right<=document.querySelector('.brand').getBoundingClientRect().right+1,
                    overlaps:logo.right>text.left,clipped:e.scrollWidth>e.clientWidth+1,
                    pageOverflow:document.documentElement.scrollWidth>innerWidth,
                    h2:[...document.querySelectorAll('h2')].map(x=>getComputedStyle(x).fontSize),
                    logo:document.querySelector('.brandmark').innerHTML,logoWidth:logo.width,logoHeight:logo.height};}''')
                pair[version] = metrics
                assert metrics['fits'] and not metrics['overlaps'] and not metrics['clipped'] and not metrics['pageOverflow'], (width, version, metrics)
                if width <= 430:
                    page.screenshot(path=str(artifacts/f'brand-{width}-{version}.png'), clip=dict(x=0, y=0, width=width, height=240))
            for key in ['family', 'weight', 'color', 'logo', 'logoWidth', 'logoHeight', 'h2']:
                assert pair['before'][key] == pair['after'][key], (width, key)
            # Letter spacing retains the same em value; its px measurement scales with font size.
            assert abs(float(pair['before']['spacing'][:-2])/pair['before']['font'] - float(pair['after']['spacing'][:-2])/pair['after']['font']) < .001
            if width <= 430:
                assert pair['after']['font'] > pair['before']['font'] * 1.2
            else:
                assert pair['after']['font'] == pair['before']['font']
            measurements.append(dict(width=width, before=pair['before']['font'], after=pair['after']['font'], text_width=pair['after']['textWidth'], available=pair['after']['available']))
        (artifacts/'measurements.json').write_text(json.dumps(measurements, indent=2)+'\n')
        print('PASS brand before/after, 320/375/390/430, no clipping/overlap/overflow, unchanged family/weight/color/spacing/logo/h2, desktop unchanged:', measurements)
        page.set_viewport_size(dict(width=390, height=844))
        for lang in ['ja', 'en']:
            page.evaluate('([k,v,l])=>{localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",l)}', [KEY, SEED, lang])
            page.reload()
            term = 'スコア' if lang == 'ja' else 'Score'
            page.locator('[data-section=collection]').click()
            for direction in ['desc', 'asc']:
                expect(page.locator(f'#sort option[value=rating-{direction}]')).to_contain_text(term)
            page.locator('#sort-toggle').click()
            page.locator('#sort').select_option('rating-desc')
            assert page.locator('#library button .title').all_text_contents() == ['C 5.0', 'C 4.5', 'C 4.3', 'C 4.2', 'C unrated']
            page.locator('#sort').select_option('rating-asc')
            assert page.locator('#library button .title').all_text_contents() == ['C 4.2', 'C 4.3', 'C 4.5', 'C 5.0', 'C unrated']
            page.locator('#sort-toggle').click()
            for mode in ['grid', 'list']:
                page.locator(f'#{mode}-tab').click()
                expect(record(page, 'C 4.2').locator('.rating-readout')).to_have_attribute('aria-label', re.compile(term))
                if mode == 'list':
                    expect(record(page, 'C 4.2')).to_contain_text(term)
            for title, color, fraction in [('C 4.2', GOLD, 20), ('C 4.3', ROSE, 30)]:
                edit(page, title)
                expect(page.locator('label[for=rating]')).to_contain_text(term)
                slider = page.locator('[data-target=rating] .star-rating')
                expect(slider).to_have_attribute('aria-label', '星をなぞってスコアを設定（5点満点）' if lang == 'ja' else 'Slide across stars to set score out of 5')
                assert_stars(slider, color, fraction)
                assert slider.locator('.heart-symbol').count() == 0
                page.locator('#rating').evaluate('(e)=>e.value="11"')
                page.locator('#save').click()
                assert alerts[-1] == (term+'は0.0〜5.0の範囲で0.1刻みで指定してください。' if lang == 'ja' else 'Score must be between 0.0 and 5.0 in steps of 0.1.')
                assert stored(page) == SEED
                page.locator('#close').click()
            # Tab/language switches retain score labels and never write the archive.
            for language in ['ja', 'en', lang]:
                page.locator('#ui-language').select_option(language)
                for section, title in [('live', 'Existing Live'), ('listening', 'Score 4.2'), ('collection', 'C 4.2')]:
                    page.locator(f'[data-section={section}]').click()
                    record(page, title).click()
                    expect(page.locator('#view-content .k').filter(has_text='スコア' if language == 'ja' else 'Score')).to_have_count(1)
                    page.locator('#view-close').click()
            assert stored(page) == SEED
            # Creation, touch, drag, clear, keyboard increments, save/reload keep original numbers.
            page.locator('#manual-add-trigger').click()
            expect(page.locator('label[for=rating]')).to_contain_text(term)
            page.locator('#manual-title').fill('Synthetic Collection')
            page.locator('#manual-artist').fill('Synthetic Artist')
            slider = page.locator('[data-target=rating] .star-rating')
            slider.scroll_into_view_if_needed()
            box = slider.bounding_box();x,y=box['x'],box['y']+box['height']/2
            page.touchscreen.tap(x+box['width']*.4, y)
            expect(page.locator('#rating')).to_have_value('4.0')
            page.mouse.move(x+box['width']*.4, y);page.mouse.down()
            page.mouse.move(x+box['width']*.86, y, steps=5);page.mouse.up()
            expect(page.locator('#rating')).to_have_value('8.6')
            page.locator('[data-target=rating] .rating-clear').click()
            expect(page.locator('#rating')).to_have_value('')
            slider.press('Home');slider.press('ArrowRight')
            expect(page.locator('#rating')).to_have_value('0.2')
            slider.press('End');save(page)
            expected = stored(page)
            assert expected['collection'][0]['rating'] == '10.0'
            for section in ['listening', 'collection', 'live']:
                actual = expected[section][1:] if section == 'collection' else expected[section]
                assert actual == SEED[section]
            page.reload();page.locator('[data-section=collection]').click()
            assert stored(page) == expected
            edit(page, 'Synthetic Collection')
            expect(page.locator('#rating')).to_have_value('10.0')
            page.locator('#close').click()
            for value in ['0.0', '']:
                edit(page, 'Synthetic Collection')
                if value:
                    page.locator('[data-target=rating] .star-rating').press('Home')
                else:
                    page.locator('[data-target=rating] .rating-clear').click()
                save(page);page.reload();page.locator('[data-section=collection]').click()
                assert stored(page)['collection'][0]['rating'] == value
                assert stored(page)['collection'][1:] == SEED['collection']
            print('PASS Collection all labels/a11y/validation, stars/colors, touch/drag/clear/keyboard/create/save/reload, original values unchanged, all-tab language switching:', lang)
        assert not errors, errors
        browser.close()
    server.shutdown()


if __name__ == '__main__':
    main()
