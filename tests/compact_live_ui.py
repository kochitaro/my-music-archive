"""Compact controls / photo lifecycle regressions; synthetic data, no external API."""
import json, threading, subprocess, os
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, stored
from data_preservation import PHOTO

OUT=ROOT/'docs/compact-live-evidence'
FILE=dict(name='photo.png',mimeType='image/png',buffer=__import__('base64').b64decode(PHOTO.split(',')[1]))
OTHER=dict(name='replacement.svg',mimeType='image/svg+xml',buffer=b'<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4" fill="blue"/></svg>')
SEED=dict(version=3,listening=[album('Listening sample')],collection=[album('Collection sample')],live=[dict(entryId='live',title='Live sample',artists=['A','B'],venue='Tokyo',date='2026-11-06',rating='8.4',photo=PHOTO,memo='Saved note')])

def main():
    OUT.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    before=subprocess.check_output(['git','show','059e0f6:index.html'],cwd=ROOT).decode()
    measurements=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for phase in (['after'] if os.environ.get('MLA_AFTER_ONLY') else ['before','after']):
            for width in (list(map(int,os.environ.get('MLA_WIDTHS','320,375,390,430,1280').split(','))) if phase=='after' else [390]):
                for lang in ['ja','en']:
                    ctx=browser.new_context(viewport=dict(width=width,height=844),has_touch=width<600,is_mobile=width<600)
                    ctx.route('https://**/*',lambda r:r.abort())
                    if phase=='before':ctx.route(base+'/',lambda r:r.fulfill(body=before,content_type='text/html'))
                    p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept())
                    p.goto(base);p.evaluate('([k,s,l])=>{localStorage.setItem(k,JSON.stringify(s));localStorage.setItem("mma-ui-language",l)}',[KEY,SEED,lang]);p.reload()
                    p.evaluate('''key=>{window.writes=0;window.fail=false;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===key){if(window.fail)throw Error('test quota');window.writes++}return set.call(this,k,v)}}''',KEY)
                    for area in ['listening','collection','live']:
                        p.locator(f'[data-section={area}]').click()
                        if width==390:p.screenshot(path=str(OUT/f'{phase}-{area}-{lang}.png'),full_page=True)
                        if phase=='after':
                            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
                            for target in ['grid-tab','list-tab','archive-screen','insights-screen']:
                                b=p.locator('#'+target).bounding_box();assert b['height']>=44 and b['width']>=44
                            p.locator('#list-tab').click();p.locator('#insights-screen').click();p.locator('#archive-screen').click()
                            expect(p.locator('#list-tab')).to_have_attribute('aria-pressed','true');p.locator('#grid-tab').click()
                            if area!='live':
                                p.locator('#search-modes').select_option('title');expect(p.locator('#query')).to_have_attribute('aria-label','アルバム名' if lang=='ja' else 'Album title');p.locator('#search-modes').select_option('artist')
                    assert p.evaluate('writes')==0 and stored(p)==SEED
                    p.locator('#add-live-trigger').click();p.locator('#live-title').fill('Draft show');p.locator('#live-venue').fill('Draft venue');p.locator('#live-notes').fill('Keep these notes')
                    if width==390:p.screenshot(path=str(OUT/f'{phase}-create-{lang}.png'),full_page=True)
                    if phase=='after':
                        assert p.locator('#live-form-panel h2').count()==0
                        expect(p.locator('#live-create-modal')).to_have_attribute('aria-labelledby','live-create-title')
                        artists=p.locator('#live-artists');artists.locator('input').fill('First');artists.get_by_role('button',name='＋ アーティストを追加' if lang=='ja' else '＋ Add Artist').click();artists.locator('input').nth(1).fill('Second')
                        remove=artists.get_by_role('button',name='アーティストを削除' if lang=='ja' else 'Remove Artist',exact=True).first
                        b=remove.bounding_box();ib=artists.locator('input').first.bounding_box();assert b['width']>=44 and b['height']>=44 and abs((b['y']+22)-(ib['y']+ib['height']/2))<2,(b,ib)
                        remove.click();assert artists.locator('input').count()==1 and artists.locator('input').first.input_value()=='Second'
                        artists.locator('.artist-remove').click();assert artists.locator('input').count()==1 and artists.locator('input').input_value()==''
                        artists.locator('input').fill('Performer')
                        p.locator('#live-photo').set_input_files(FILE);expect(p.locator('#live-photo-preview')).to_be_visible();expect(p.locator('#live-photo-preview')).to_have_attribute('alt','ライブ写真' if lang=='ja' else 'Live photo')
                        with p.expect_file_chooser() as chooser:p.locator('#select-live-photo').click()
                        chooser.value.set_files(FILE);expect(p.locator('#live-photo-preview')).to_be_visible();expect(p.locator('#live-photo-preview')).to_have_attribute('alt','ライブ写真' if lang=='ja' else 'Live photo')
                        # A cancelled picker emits no accepted selection; current form file stays intact.
                        with p.expect_file_chooser():p.locator('#select-live-photo').click()
                        assert p.locator('#live-photo').evaluate('(e)=>e.files.length')==1
                        with p.expect_file_chooser() as chooser:p.locator('#select-live-photo').click()
                        chooser.value.set_files(OTHER);assert p.locator('#live-photo').evaluate('(e)=>e.files[0].name')=='replacement.svg'
                        if width==390:p.locator('#live-photo-preview').scroll_into_view_if_needed();p.screenshot(path=str(OUT/f'photo-selected-{lang}.png'))
                        p.locator('#clear-live-photo').click();expect(p.locator('#live-photo-preview')).to_be_hidden()
                        expect(p.locator('#live-title')).to_have_value('Draft show');expect(p.locator('#live-notes')).to_have_value('Keep these notes');expect(p.locator('#live-venue')).to_have_value('Draft venue')
                        p.locator('#live-photo').set_input_files(FILE)
                        p.locator('#live-form > button').click();expect(p.locator('#live-create-modal')).not_to_be_visible();assert stored(p)['live'][0]['photo'].startswith('data:image/jpeg')
                    else:p.locator('#close-live-create').click()
                    # Edit the original record.
                    p.locator('.coverbtn').filter(has_text='Live sample').click();p.locator('#view-edit').click()
                    if width==390:p.screenshot(path=str(OUT/f'{phase}-edit-{lang}.png'),full_page=True)
                    if phase=='after':
                        p.locator('#e-live-title').fill('Edited show');p.locator('#memo').fill('Unsaved edit note')
                        p.locator('#e-live-photo').set_input_files(FILE)
                        selected=p.locator('#existing-photo').get_attribute('src');assert selected.startswith('blob:')
                        # Failure must preserve saved image, selected replacement and other input.
                        p.evaluate('fail=true');p.locator('#remove-photo').click();expect(p.locator('#save-notice')).to_be_visible()
                        assert stored(p)['live'][1]['photo']==PHOTO
                        assert p.locator('#e-live-photo').evaluate('(e)=>e.files.length')==1
                        expect(p.locator('#memo')).to_have_value('Unsaved edit note');assert p.locator('#existing-photo').get_attribute('src')==selected
                        p.locator('#save-return').click();p.evaluate('fail=false');p.locator('#remove-photo').click()
                        expect(p.locator('#existing-photo')).to_be_hidden();assert p.locator('#e-live-photo').evaluate('(e)=>e.files.length')==0
                        assert stored(p)['live'][1]['photo']=='';expect(p.locator('#memo')).to_have_value('Unsaved edit note')
                        if p.locator('#save-notice').is_visible():p.locator('#save-return').click()
                        if width==390:p.locator('#change-live-photo').scroll_into_view_if_needed();p.screenshot(path=str(OUT/f'photo-deleted-{lang}.png'))
                        p.locator('#save').click();expect(p.locator('#modal')).not_to_be_visible();assert stored(p)['live'][1]['photo']=='' and stored(p)['live'][1]['memo']=='Unsaved edit note'
                        # Replacement save persists the new image; old saved image never returns.
                        p.locator('.coverbtn').filter(has_text='Edited show').click();p.locator('#view-edit').click()
                        with p.expect_file_chooser() as chooser:p.locator('#change-live-photo').click()
                        chooser.value.set_files(OTHER)
                        p.evaluate('fail=true');p.locator('#save').click();expect(p.locator('#save-notice')).to_be_visible()
                        assert stored(p)['live'][1]['photo']=='' and p.locator('#e-live-photo').evaluate('(e)=>e.files[0].name')=='replacement.svg'
                        p.locator('#save-return').click();p.evaluate('fail=false');p.locator('#save').click();expect(p.locator('#modal')).not_to_be_visible();assert stored(p)['live'][1]['photo'].startswith('data:image/jpeg')
                        measurements.append(dict(width=width,lang=lang,overflow=False,touchTargets='>=44px',uiDBWrites=0,photoLifecycle='pass'))
                    assert not errors,errors
                    print(f'PASS {phase} {lang} {width}',flush=True);ctx.close()
        browser.close()
    (OUT/('matrix-'+os.environ['MLA_WIDTHS']+'.json' if os.environ.get('MLA_WIDTHS') else 'matrix.json')).write_text(json.dumps(measurements,indent=2));server.shutdown()

if __name__=='__main__':main()
