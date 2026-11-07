"""UI hierarchy, placeholder, state and no-record-write evidence. Chromium only."""
import json, threading, subprocess
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, stored, open_filters

OUT=ROOT/'docs/top-hierarchy-evidence'
SEED=dict(version=3,listening=[album('Listening sample')],collection=[album('Collection sample')],live=[dict(entryId='live',title='Live sample',artists=['Artist A'],venue='Tokyo',date='2026-11-07',rating='8.4')])

def main():
    OUT.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    before=subprocess.check_output(['git','show','1c70fb8:index.html'],cwd=ROOT).decode()
    matrix=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for phase in ['before','after']:
            for width in ([390] if phase=='before' else [320,375,390,430,1280]):
                for lang in ['ja','en']:
                    ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width<600,has_touch=width<600)
                    calls=[];ctx.route('https://**/*',lambda r:(calls.append(r.request.url),r.abort()))
                    if phase=='before':ctx.route(base+'/',lambda r:r.fulfill(body=before,content_type='text/html'))
                    p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
                    p.goto(base);p.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,SEED,lang]);p.reload()
                    p.evaluate('''key=>{window.writes=0;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===key)writes++;return set.call(this,k,v)}}''',KEY)
                    for area in ['listening','collection','live']:
                        p.locator(f'[data-section={area}]').click()
                        expect(p.locator('#sections .active')).to_have_attribute('data-section',area)
                        if phase=='after':
                            assert p.locator('#search-title').count()==0 and p.locator('#search-panel h2').count()==0
                            for name in ['archive','insights']:
                                tab=p.locator('#'+name+'-screen');b=tab.bounding_box();assert b['width']>=44 and b['height']>=44
                                css=tab.evaluate('(e)=>{const s=getComputedStyle(e);return {bg:s.backgroundColor,font:parseFloat(s.fontSize),border:s.borderBottomColor,line:s.textDecorationLine,thickness:s.textDecorationThickness}}')
                                assert css['bg']=='rgba(0, 0, 0, 0)' and css['font']<p.locator('#sections .tab').first.evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)')
                                if name=='archive':assert css['border']=='rgba(0, 0, 0, 0)' and css['line']=='underline' and css['thickness']=='2px'
                                else:assert css['border']=='rgba(0, 0, 0, 0)'
                            if area!='live':
                                for mode in ['artist','title']:
                                    p.locator(f'[data-search-mode={mode}]').click()
                                    placeholder=('アーティストを検索' if mode=='artist' else 'アルバムを検索') if lang=='ja' else ('Search artists' if mode=='artist' else 'Search albums')
                                    expect(p.locator('#query')).to_have_attribute('placeholder',placeholder)
                                    if width==390:p.screenshot(path=str(OUT/f'placeholder-{area}-{mode}-{lang}.png'),full_page=True)
                                    assert p.locator('#query').get_attribute('aria-label') and p.locator('#query').evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)')>=16
                                p.locator('[data-search-mode=artist]').click()
                                for target in ['query','search-modes','search-btn','manual-add-trigger']:
                                    b=p.locator('#'+target).bounding_box();assert b['width']>=44 and b['height']>=44 and b['x']>=0 and b['x']+b['width']<=width+.1
                                boxes=[p.locator('#'+x).bounding_box() for x in ['search-modes','query','search-btn','manual-add-trigger']]
                                for i,a in enumerate(boxes):
                                    for b in boxes[i+1:]:assert a['x']+a['width']<=b['x']+.1 or b['x']+b['width']<=a['x']+.1 or a['y']+a['height']<=b['y']+.1 or b['y']+b['height']<=a['y']+.1
                            else:expect(p.locator('#search-panel')).to_be_hidden();expect(p.locator('#add-live-trigger')).to_be_visible()
                            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
                        p.screenshot(path=str(OUT/f'{phase}-{area}-{lang}-{width}.png'),full_page=True)
                        if phase=='after':
                            if area!='live':p.locator('#query').fill('Keep this query')
                            p.locator('#list-tab').click();open_filters(p);p.locator('#artist-filter').select_option('Artist A')
                            p.locator('#sort-toggle').click();p.locator('#sort').select_option('rating-desc')
                            state=p.locator('#archive-content select').evaluate_all('(es)=>es.map(e=>[e.id,e.value])')
                            p.locator('#insights-screen').focus();p.keyboard.press('Enter')
                            expect(p.locator('#insights-screen')).to_have_attribute('aria-pressed','true');expect(p.locator(f'#{area}-insights')).to_be_visible()
                            if width==390:p.screenshot(path=str(OUT/f'after-insights-{area}-{lang}.png'),full_page=True)
                            p.locator('#ui-language').select_option('en' if lang=='ja' else 'ja');p.locator('#ui-language').select_option(lang)
                            p.locator('#archive-screen').click();assert state==p.locator('#archive-content select').evaluate_all('(es)=>es.map(e=>[e.id,e.value])')
                            expect(p.locator('#list-tab')).to_have_attribute('aria-pressed','true');p.locator('#grid-tab').click()
                            if area!='live':expect(p.locator('#query')).to_have_value('Keep this query')
                    assert p.evaluate('writes')==0 and stored(p)==SEED and not errors,errors
                    assert not calls,calls
                    if phase=='after':matrix.append(dict(width=width,lang=lang,archives=3,touchTargets='>=44px',queryFont=16,overlap=False,overflow=False,dbWrites=0,apiCalls=0))
                    print(f'PASS {phase} {lang} {width}',flush=True);ctx.close()
        browser.close()
    (OUT/'matrix.json').write_text(json.dumps(matrix,indent=2));server.shutdown()

if __name__=='__main__':main()
