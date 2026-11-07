"""Web-side Safari zoom prevention and pre-save native photo picker contract.
Actual iOS Photos UI and Safari zoom behavior require a real-device check.
"""
import json, os, subprocess, threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, stored
from compact_live_ui import FILE, OTHER, SEED

OUT=ROOT/'docs/ios-search-photo-evidence'
OTHER={**OTHER,'buffer':b'<svg xmlns="http://www.w3.org/2000/svg" width="320" height="160"><rect width="320" height="160" fill="#75c5da"/></svg>'}

def main():
    OUT.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    baseline=subprocess.check_output(['git','show','498992f:index.html'],cwd=ROOT).decode()
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for phase in ['before','after']:
            for width in ([390] if phase=='before' else [320,375,390,430,1280]):
                for lang in ['ja','en']:
                    ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width<600,has_touch=width<600)
                    ctx.route('https://**/*',lambda r:r.abort())
                    if phase=='before':ctx.route(base+'/',lambda r:r.fulfill(body=baseline,content_type='text/html'))
                    p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.on('dialog',lambda d:d.accept())
                    p.goto(base);p.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,SEED,lang]);p.reload()
                    p.evaluate('''key=>{window.writes=0;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===key)writes++;return set.call(this,k,v)}}''',KEY)
                    for area in ['listening','collection']:
                        p.locator(f'[data-section={area}]').click();p.locator('#query').focus()
                        font=p.locator('#query').evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)')
                        if phase=='after':
                            assert font>=16
                            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
                            assert 'maximum-scale' not in p.locator('meta[name=viewport]').get_attribute('content')
                        if width==390 and area=='listening':p.screenshot(path=str(OUT/f'{phase}-search-{lang}.png'),full_page=True)
                    p.locator('[data-section=live]').click();p.locator('#add-live-trigger').click()
                    p.locator('#live-title').fill('Unregistered show');p.locator('#live-venue').fill('Keep venue');p.locator('#live-notes').fill('Keep notes')
                    button=p.locator('#select-live-photo')
                    if phase=='after':expect(button).to_have_text('写真を追加' if lang=='ja' else 'Add Photo')
                    if width==390:button.scroll_into_view_if_needed();p.screenshot(path=str(OUT/f'{phase}-add-photo-{lang}.png'))
                    if phase=='after':
                        # Choose using the actual button, then reopen before any registration.
                        with p.expect_file_chooser() as chooser:button.press('Enter')
                        assert p.locator('body > input[type=file]').count()==1
                        chooser.value.set_files(FILE)
                        expect(button).to_have_text('写真を変更' if lang=='ja' else 'Replace Photo')
                        expect(p.locator('#live-photo-preview')).to_be_visible()
                        assert p.locator('body > input[type=file]').count()==0
                        p.evaluate('window.previousFile=document.querySelector("#live-photo").files[0]')
                        with p.expect_file_chooser():button.click()
                        p.locator('body > input[type=file]').dispatch_event('cancel')
                        assert p.evaluate('previousFile===document.querySelector("#live-photo").files[0]')
                        with p.expect_file_chooser() as chooser:button.click()
                        chooser.value.set_files(OTHER)
                        assert p.locator('#live-photo').evaluate('(e)=>e.files[0].name')=='replacement.svg'
                        expect(p.locator('#live-title')).to_have_value('Unregistered show');expect(p.locator('#live-notes')).to_have_value('Keep notes');expect(p.locator('#live-venue')).to_have_value('Keep venue')
                        expect(p.locator('#live-form .group > span').filter(has_text='保存前でも' if lang=='ja' else 'before saving')).to_be_visible()
                        assert p.evaluate('writes')==0 and stored(p)==SEED
                        if width==390:
                            p.locator('#live-form .group > span').filter(has_text='保存前でも' if lang=='ja' else 'before saving').scroll_into_view_if_needed()
                            p.screenshot(path=str(OUT/f'after-reselected-{lang}.png'))
                        # Clearing restores Add Photo; reselecting the same file is possible.
                        p.locator('#clear-live-photo').click();expect(button).to_have_text('写真を追加' if lang=='ja' else 'Add Photo')
                        with p.expect_file_chooser() as chooser:button.click()
                        chooser.value.set_files(OTHER)
                        assert p.evaluate('writes')==0
                        p.locator('#live-form > button').click();expect(p.locator('#live-create-modal')).not_to_be_visible()
                        assert stored(p)['live'][0]['photo'].startswith('data:image/jpeg')
                        # Editing also reopens the native picker without Save Changes.
                        p.locator('.coverbtn').filter(has_text='Live sample').click();p.locator('#view-edit').click()
                        edit=p.locator('#change-live-photo');expect(edit).to_have_text('写真を変更' if lang=='ja' else 'Replace Photo')
                        with p.expect_file_chooser() as chooser:edit.click()
                        chooser.value.set_files(FILE)
                        with p.expect_file_chooser() as chooser:edit.click()
                        chooser.value.set_files(OTHER)
                        assert stored(p)['live'][1]['photo']==SEED['live'][0]['photo']
                        p.locator('#save').click();expect(p.locator('#modal')).not_to_be_visible()
                        results.append(dict(width=width,lang=lang,searchFont=font,preSaveReselection=True,cancelKeepsSelection=True,preSaveDBWrites=0))
                    assert not errors,errors
                    print(f'PASS {phase} {lang} {width}',flush=True);ctx.close()
        browser.close()
    (OUT/'matrix.json').write_text(json.dumps(results,indent=2));server.shutdown()

if __name__=='__main__':main()
