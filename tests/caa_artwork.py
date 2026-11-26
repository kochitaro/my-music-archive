"""CAA-only containment: real UI, synthetic images, before/after browser regression.

Run: python tests/caa_artwork.py
Optional MLA_WEBKIT selects a WebKit executable; MLA_EVIDENCE selects output directory.
All HTTP requests are fulfilled locally or aborted. No personal browser profile is used.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlparse

from PIL import Image, ImageChops, ImageDraw, ImageStat
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('MLA_EVIDENCE', '/tmp/mla-caa-artwork-evidence'))
BASELINE = 'ba83392ce179c7e6ad0c099241d86dfeedd49dc3'
SHAPES = [('square', 400, 400), ('portrait', 240, 480), ('landscape', 480, 240)]
IMAGES = {}
for name, width, height in SHAPES:
    image = Image.new('RGB', (width, height), '#596f83')
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, 19), fill='#ff0000')
    draw.rectangle((0, height - 20, width - 1, height - 1), fill='#00ff00')
    draw.rectangle((0, 20, 19, height - 21), fill='#0000ff')
    draw.rectangle((width - 20, 20, width - 1, height - 21), fill='#ffff00')
    stream = io.BytesIO()
    image.save(stream, format='PNG')
    IMAGES[name] = stream.getvalue()
PHOTO = 'data:image/png;base64,' + base64.b64encode(IMAGES['portrait']).decode()
RELEASES = [{'id': name, 'title': name.title(), 'primary-type': 'Album',
             'first-release-date': '2026-01-01',
             'artist-credit': [{'name': 'Synthetic Artist'}]}
            for name, _, _ in SHAPES] + [
    {'id': 'failure', 'title': 'Failure', 'primary-type': 'Album',
     'artist-credit': [{'name': 'Synthetic Artist'}]}]
SEED = {'version': 3, 'listening': [], 'collection': [], 'live': []}
for area in ['listening', 'collection']:
    for name in ['square', 'portrait', 'landscape', 'photo', 'failure', 'no-id']:
        SEED[area].append({'entryId': area + '-' + name,
                           'id': '' if name == 'no-id' else name,
                           'title': name.title(), 'artist': 'Synthetic Artist',
                           'release': '2026-01-01', 'date': '2026-11-20',
                           'photo': PHOTO if name == 'photo' else ''})


def archive_snapshot(page):
    return page.evaluate('''async()=>{const db=await new Promise((ok,no)=>{
      const r=indexedDB.open('mla-archive-v1');r.onsuccess=()=>ok(r.result);r.onerror=no});
      try{return await new Promise((ok,no)=>{const tx=db.transaction('archive');
      const r=tx.objectStore('archive').getAll();r.onsuccess=()=>ok(JSON.stringify(r.result));r.onerror=no})}
      finally{db.close()}}''')


def run(browser, phase, width, engine, baseline):
    ctx = browser.new_context(viewport={'width': width, 'height': 844}, locale='ja-JP')
    ctx.add_init_script('localStorage.setItem("my-music-archive-pilot-v03",' +
                        json.dumps(json.dumps(SEED)) + ');localStorage.setItem("mma-ui-language","ja")')
    calls, errors, results = [], [], {}

    def route(request):
        url = request.request.url
        calls.append(url)
        parsed = urlparse(url)
        if parsed.netloc == 'coverartarchive.org':
            name = parsed.path.split('/')[-2]
            if name in IMAGES:
                request.fulfill(body=IMAGES[name], content_type='image/png')
            else:
                request.fulfill(status=404)
        elif parsed.netloc == 'musicbrainz.org':
            body = {'artists': [{'id': 'artist', 'name': 'Synthetic Artist'}]} if '/artist/' in parsed.path else {'release-groups': RELEASES, 'count': 4, 'release-group-count': 4}
            request.fulfill(json=body)
        elif parsed.netloc == 'localhost':
            file = ROOT / parsed.path.lstrip('/')
            if phase == 'before' and parsed.path == '/index.html':
                request.fulfill(body=baseline, content_type='text/html')
            elif file.is_file():
                request.fulfill(path=str(file))
            else:
                request.abort()
        else:
            request.abort()

    ctx.route('**/*', route)
    page = ctx.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://localhost/index.html')
    page.evaluate('async()=>await MLAReady')
    before_archive = archive_snapshot(page)

    def capture(screen, selector):
        root = page.locator(selector)
        root.scroll_into_view_if_needed()
        for image in root.locator('img.art').all():
            image.scroll_into_view_if_needed()
            image.evaluate('(i)=>i.decode().catch(()=>{})')
        expect(root.locator('img[src*="/failure/"]')).to_have_count(0)
        page.evaluate('scrollTo(0,0)')
        geometry = root.locator('.art,.title,.grow').evaluate_all('''xs=>xs.map(e=>{
          const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {
          tag:e.tagName,text:e.tagName==='IMG'?'':e.textContent,
          box:[r.x,r.y,r.width,r.height],radius:s.borderRadius,
          background:s.backgroundColor,position:s.objectPosition}})''')
        images = []
        for i, image in enumerate(root.locator('img.art').all()):
            src = image.get_attribute('src')
            photo = src.startswith('data:')
            shape = 'photo' if photo else src.split('/')[-2]
            fit = image.evaluate('(e)=>getComputedStyle(e).objectFit')
            assert fit == ('cover' if phase == 'before' or photo else 'contain'), (screen, shape, fit)
            assert ('caa-art' in image.get_attribute('class').split()) == (phase == 'after' and not photo)
            png = image.screenshot(animations='disabled')
            decoded = Image.open(io.BytesIO(png)).convert('RGB')
            (OUT / f'{engine}-{width}-{phase}-{screen}-{shape}-art.png').write_bytes(png)
            digest = hashlib.sha256(decoded.tobytes()).hexdigest()
            if phase == 'after' and not photo:
                pixels = set(decoded.get_flattened_data())
                assert all(color in pixels for color in [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]), (screen, shape, 'edge missing')
            images.append({'shape': shape, 'digest': digest, 'file': str(OUT / f'{engine}-{width}-{phase}-{screen}-{shape}-art.png')})
        placeholders = [hashlib.sha256(p.screenshot()).hexdigest() for p in root.locator('.placeholder').all()]
        page.evaluate('scrollTo(0,0)')
        page.screenshot(path=str(OUT / f'{engine}-{width}-{phase}-{screen}.png'))
        results[screen] = {'geometry': geometry, 'images': images, 'placeholders': placeholders}

    for mode in ['artist', 'title']:
        page.locator(f'[data-search-mode={mode}]').click()
        page.locator('#query').fill('Synthetic Artist' if mode == 'artist' else 'Synthetic')
        page.locator('#search-btn').click()
        expect(page.locator('#results .result')).to_have_count(4)
        capture('search-' + mode, '#results')
    page.locator('#clear-search').click()
    for area in ['listening', 'collection']:
        page.locator(f'[data-section={area}]').click()
        capture(area + '-grid', '#library')
        page.locator('#archive-view-toggle').click()
        capture(area + '-list', '#library')
        for idx, shape in enumerate(['square', 'portrait', 'landscape', 'photo', 'failure', 'no-id']):
            page.locator('#library .listrow').nth(idx).click()
            capture(area + '-detail-' + shape, '#view-content')
            page.locator('#view-close').click()
        page.locator('#archive-view-toggle').click()
    assert archive_snapshot(page) == before_archive
    assert not errors, errors
    ctx.close()
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = subprocess.check_output(['git', 'show', BASELINE + ':index.html'], cwd=ROOT).decode()
    summary = []
    with sync_playwright() as pw:
        for engine in ['chromium', 'webkit']:
            options = {'executable_path': '/usr/bin/chromium', 'args': ['--no-sandbox']} if engine == 'chromium' else ({'executable_path': os.environ['MLA_WEBKIT']} if os.environ.get('MLA_WEBKIT') else {})
            browser = getattr(pw, engine).launch(**options)
            for width in [390, 1280]:
                before = run(browser, 'before', width, engine, baseline)
                after = run(browser, 'after', width, engine, baseline)
                for screen, old in before.items():
                    new = after[screen]
                    assert old['geometry'] == new['geometry'], (engine, width, screen, 'layout/radius/background changed')
                    assert old['placeholders'] == new['placeholders'], (screen, 'placeholder changed')
                    for a, b in zip(old['images'], new['images'], strict=True):
                        assert a['shape'] == b['shape']
                        if a['shape'] == 'square':
                            # cover/contain can differ slightly at fractional CSS pixel edges.
                            diff = ImageChops.difference(Image.open(a['file']).convert('RGB'), Image.open(b['file']).convert('RGB'))
                            assert max(ImageStat.Stat(diff).mean) < .25 and max(v[1] for v in diff.getextrema()) <= 16, (screen, 'square changed visually')
                        elif a['shape'] == 'photo':
                            assert a['digest'] == b['digest'], (screen, 'photo pixels changed')
                        else:
                            assert a['digest'] != b['digest'], (screen, 'non-square not updated')
                    summary.append({'engine': engine, 'width': width, 'screen': screen, 'result': 'PASS'})
                print(engine, width, len(after), 'screens PASS', flush=True)
            browser.close()
    (OUT / 'results.json').write_text(json.dumps(summary, indent=2))
    print('PASS:', len(summary), 'before/after screen comparisons; CAA edges, visually unchanged squares and identical photo pixels, frames, corners, placeholders and records')


if __name__ == '__main__':
    main()
