"""UI-only screen switching, bilingual mobile evidence and Live form contract."""
import json, threading, os
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, stored, open_filters


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    evidence=Path(os.environ.get('MLA_EVIDENCE',str(ROOT/'docs/archive-insights-evidence')));evidence.mkdir(exist_ok=True)
    seed=dict(version=3,listening=[album('Listening sample')],collection=[album('Collection sample')],live=[dict(entryId='live',title='Live sample',artists=['A','B','A'],venue='Tokyo',date='2026-11-06',rating='8.4')])
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for width in [320,390,430,1280]:
            for lang in ['ja','en']:
                ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width<600,has_touch=width<600)
                ctx.route('https://**/*',lambda r:r.abort())
                page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                page.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,seed,lang]);page.reload()
                raw=page.evaluate('(k)=>localStorage.getItem(k)',KEY)
                # Count any record DB writes, including writes of the same value.
                page.evaluate('''(key)=>{window.dbWrites=0;const original=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===key)window.dbWrites++;return original.call(this,k,v)}}''',KEY)
                for area in ['listening','collection','live']:
                    page.locator(f'[data-section={area}]').click()
                    expect(page.locator('#archive-content')).to_be_visible()
                    expect(page.locator('#archive-screen')).to_have_text('アーカイブ' if lang=='ja' else 'Archive')
                    expect(page.locator('#insights-screen')).to_have_text('統計' if lang=='ja' else 'Insights')
                    for value,name in [('grid','グリッド' if lang=='ja' else 'Grid'),('list','リスト' if lang=='ja' else 'List')]:
                        button=page.get_by_role('button',name=name,exact=True)
                        assert button.inner_text()==''
                        box=button.bounding_box();assert box['width']>=44 and box['height']>=44
                        heading=page.locator('.archive-heading h2').bounding_box()
                        assert box['x']>=heading['x']+heading['width'] and box['y']<heading['y']+heading['height']+44
                    page.screenshot(path=str(evidence/f'archive-{area}-{lang}-{width}.png'),full_page=True)
                    page.locator('#list-tab').click();open_filters(page)
                    page.locator('#sort-toggle').click();page.locator('#sort').select_option('rating-desc');open_filters(page)
                    page.locator('#artist-filter').select_option('A' if area=='live' else 'Artist A')
                    state=page.locator('#archive-content').evaluate('(e)=>[...e.querySelectorAll("select")].map(s=>[s.id,s.value])')
                    if width==390:page.screenshot(path=str(evidence/f'after-{area}-{lang}-{width}.png'),full_page=True)
                    page.locator('#insights-screen').click()
                    expect(page.locator('#archive-content')).to_be_hidden()
                    assert page.locator('#archive-content').evaluate('(e)=>e.inert')
                    expect(page.locator(f'#{area}-insights')).to_be_visible()
                    expect(page.locator(f'#{area}-insights h2')).to_contain_text('統計' if lang=='ja' else 'Insights')
                    assert page.locator('#insights-content > section:visible').count()==1
                    for selector in ['#search-panel','#library','#grid-tab','#sort-toggle','#filters-toggle','#add-live-trigger']:
                        expect(page.locator(selector)).to_be_hidden()
                    expect(page.locator('#export-json')).to_be_visible()
                    other='en' if lang=='ja' else 'ja'
                    page.locator('#ui-language').select_option(other)
                    expect(page.locator(f'#{area}-insights h2')).to_contain_text('統計' if other=='ja' else 'Insights')
                    page.locator('#ui-language').select_option(lang)
                    if width==390:page.screenshot(path=str(evidence/f'insights-{area}-{lang}-{width}.png'),full_page=True)
                    page.locator('#archive-screen').click()
                    assert state==page.locator('#archive-content').evaluate('(e)=>[...e.querySelectorAll("select")].map(s=>[s.id,s.value])')
                    expect(page.locator('#list-tab')).to_have_attribute('aria-pressed','true')
                    assert page.locator('.listrow').count()==1
                    page.locator('#grid-tab').focus();page.keyboard.press('Enter')
                    expect(page.locator('#grid-tab')).to_have_attribute('aria-pressed','true')
                    assert page.locator('.coverbtn').count()==1
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    page.locator('#insights-screen').click()
                assert page.evaluate('window.dbWrites')==0
                assert page.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
                page.locator('[data-section=live]').click()
                page.locator('#add-live-trigger').click()
                for prefix in ['live','e-live']:
                    if prefix=='e-live':
                        page.locator('#close-live-create').click();page.locator('.coverbtn').click();page.locator('#view-edit').click()
                    expect(page.locator(f'label[for={prefix}-title]')).to_have_text('公演名' if lang=='ja' else 'Show Name')
                    expect(page.locator(f'label[for={prefix}-rating]')).to_have_text('スコア' if lang=='ja' else 'Score')
                    expect(page.locator(f'#{prefix}-artists .group > label').first).to_have_text('アーティスト（任意・複数）' if lang=='ja' else 'Artists (Optional, Multiple)')
                    assert page.locator(f'#{prefix}-artists').evaluate('(e)=>e.previousElementSibling.contains(document.querySelector("#'+prefix+'-title"))')
                    slider=page.locator(f'[data-target={prefix}-rating] .star-rating');slider.focus();page.keyboard.press('Home');page.keyboard.press('ArrowRight')
                    expect(slider).to_have_attribute('aria-valuenow','0.1')
                    if width==390:page.screenshot(path=str(evidence/f'{prefix}-form-{lang}.png'),full_page=True)
                assert stored(page)==seed and not errors,errors
                print(f'PASS {lang} {width}: screen isolation, DOM state, no DB writes, icon names/tap sizes, overflow, Live labels/order/score')
                ctx.close()
        browser.close()
    server.shutdown()

if __name__=='__main__':main()
