"""Native select styling, text fit, focus, two-row geometry and no-write checks."""
import json, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, stored
from top_hierarchy import SEED

OUT=ROOT/'docs/search-mode-light-evidence'

def main():
    OUT.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';baseline=subprocess.check_output(['git','show','78dd28a:index.html'],cwd=ROOT).decode();matrix=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for phase in ['before','after']:
            for width in [320,375,390,430,1280]:
                for lang in ['ja','en']:
                    ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width<600,has_touch=width<600)
                    calls=[];ctx.route('https://**/*',lambda r:(calls.append(r.request.url),r.abort()))
                    if phase=='before':ctx.route(base+'/',lambda r:r.fulfill(body=baseline,content_type='text/html'))
                    p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
                    p.goto(base);p.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,SEED,lang]);p.reload()
                    p.evaluate('''key=>{window.writes=0;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===key)writes++;return set.call(this,k,v)}}''',KEY)
                    for area in ['listening','collection']:
                        p.locator(f'[data-section={area}]').click();select=p.locator('#search-modes')
                        if phase=='after':
                            for mode in ['artist','title']:
                                select.select_option(mode)
                                text=select.locator('option:checked').inner_text()
                                assert text==({'artist':'アーティスト','title':'アルバム名'} if lang=='ja' else {'artist':'Artist','title':'Album Title'})[mode]
                                style=select.evaluate('''e=>{const s=getComputedStyle(e),c=document.createElement('canvas').getContext('2d');c.font=s.font;return {tag:e.tagName,w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height,bg:s.backgroundColor,border:s.borderWidth,color:s.color,font:parseFloat(s.fontSize),arrow:s.backgroundImage,text:c.measureText(e.selectedOptions[0].text).width,available:e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)}}''')
                                assert style['tag']=='SELECT' and style['w']>=44 and style['h']>=44
                                assert style['bg']=='rgba(0, 0, 0, 0)' and style['border']=='0px' and 12<=style['font']<=13
                                assert style['arrow']!='none' and style['text']<=style['available']+.5,style
                                assert style['color']==p.locator('#manual-add-trigger').evaluate('(e)=>getComputedStyle(e).color')
                                placeholder=('アーティストを検索' if mode=='artist' else 'アルバムを検索') if lang=='ja' else ('Search artists' if mode=='artist' else 'Search albums')
                                expect(p.locator('#query')).to_have_attribute('placeholder',placeholder)
                            select.focus();select.press('ArrowUp');expect(select).to_have_value('artist')
                            assert select.evaluate('(e)=>getComputedStyle(e).outlineStyle')!='none'
                            assert select.evaluate('(e)=>parseFloat(getComputedStyle(e).outlineWidth)')>=2
                            a=select.bounding_box();b=p.locator('#manual-add-trigger').bounding_box();q=p.locator('#query').bounding_box();search=p.locator('#search-btn').bounding_box()
                            assert a['x']+a['width']<=b['x'] and abs(a['y']-b['y'])<1
                            assert q['y']>=a['y']+a['height'] and abs(q['y']-search['y'])<1 and q['x']+q['width']<=search['x']
                            assert 0<=a['x'] and b['x']+b['width']<=width and search['x']+search['width']<=width
                            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
                            assert p.locator('#query').evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)')>=16
                            if area=='listening':p.screenshot(path=str(OUT/f'focus-{lang}-{width}.png'),full_page=True)
                            p.locator('#query').focus();p.locator('#query').fill('Keep query')
                            select.select_option('title');p.locator('#ui-language').select_option('en' if lang=='ja' else 'ja');p.locator('#ui-language').select_option(lang)
                            expect(select).to_have_value('title');expect(p.locator('#query')).to_have_value('Keep query')
                            p.locator('#query').fill('');select.select_option('artist');p.locator('#query').blur()
                        p.screenshot(path=str(OUT/f'{phase}-{area}-{lang}-{width}.png'),full_page=True)
                        if phase=='after':
                            p.locator('#manual-add-trigger').click();expect(p.locator('#modal')).to_be_visible();p.locator('#close').click()
                    assert p.evaluate('writes')==0 and stored(p)==SEED and not calls and not errors,(calls,errors)
                    if phase=='after':matrix.append(dict(width=width,lang=lang,areas=2,nativeSelect=True,twoRows=True,selectWidth=style['w'],selectHeight=style['h'],font=13,focus='2px',textFits=True,arrowVisible=True,dbWrites=0,apiCalls=0))
                    print(f'PASS {phase} {lang} {width}',flush=True);ctx.close()
        browser.close()
    (OUT/'matrix.json').write_text(json.dumps(matrix,indent=2));server.shutdown()

if __name__=='__main__':main()
