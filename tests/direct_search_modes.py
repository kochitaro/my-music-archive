"""One-tap mode controls: geometry, rapid input, keyboard, language and no writes."""
import json, subprocess, threading, os
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, stored
from top_hierarchy import SEED

OUT=ROOT/'docs/direct-search-modes-evidence'

def main():
    OUT.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';baseline=subprocess.check_output(['git','show','c0592ee:index.html'],cwd=ROOT).decode();measurements=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for phase in os.environ.get('MLA_DIRECT_PHASES','before,after').split(','):
            for width in [320,375,390,430,1280]:
                for lang in ['ja','en']:
                    ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width<600,has_touch=width<600)
                    calls=[];ctx.route('https://**/*',lambda r:(calls.append(r.request.url),r.abort()))
                    if phase=='before':ctx.route(base+'/',lambda r:r.fulfill(body=baseline,content_type='text/html'))
                    p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
                    p.goto(base);p.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,SEED,lang]);p.reload()
                    p.evaluate('''key=>{window.writes=0;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===key)writes++;return set.call(this,k,v)}}''',KEY)
                    for area in ['listening','collection']:
                        p.locator(f'[data-section={area}]').click()
                        if phase=='after':
                            group=p.get_by_role('group',name='検索方式' if lang=='ja' else 'Search mode',exact=True)
                            assert group.locator('button[type=button]').count()==2 and p.locator('select#search-modes').count()==0
                            p.locator('#query').fill('Keep this query')
                            sizes=[]
                            for mode in ['artist','title']:
                                button=p.locator(f'[data-search-mode={mode}]');button.click()
                                expect(button).to_have_attribute('aria-pressed','true')
                                expect(group.locator('[aria-pressed=true]')).to_have_count(1)
                                placeholder=('アーティストを検索' if mode=='artist' else 'アルバムを検索') if lang=='ja' else ('Search artists' if mode=='artist' else 'Search albums')
                                expect(p.locator('#query')).to_have_attribute('placeholder',placeholder);expect(p.locator('#query')).to_have_value('Keep this query')
                                text=button.inner_text();assert text==({'artist':'アーティスト','title':'アルバム名'} if lang=='ja' else {'artist':'Artist','title':'Album Title'})[mode]
                                css=button.evaluate('''e=>{const s=getComputedStyle(e),r=document.createRange();r.selectNodeContents(e);return {bg:s.backgroundColor,font:parseFloat(s.fontSize),bottom:s.borderBottomColor,weight:s.fontWeight,text:r.getBoundingClientRect().width,available:e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)}}''')
                                assert css['bg']=='rgba(0, 0, 0, 0)' and css['font']==13 and css['bottom']=='rgb(159, 207, 220)' and css['text']<=css['available']+.5,css
                                b=button.bounding_box();assert b['width']>=44 and b['height']>=44;sizes.append(dict(mode=mode,width=b['width'],height=b['height']))
                                if area=='listening':
                                    p.locator('#query').fill('');p.locator('#query').blur();p.screenshot(path=str(OUT/f'selected-{mode}-{lang}-{width}.png'),full_page=True);p.locator('#query').fill('Keep this query')
                            # Synchronous repeated native clicks must never disagree with the selected mode.
                            p.evaluate('''()=>{for(let i=0;i<100;i++){const mode=i%2?'artist':'title',b=document.querySelector(`[data-search-mode=${mode}]`);b.click();b.click();if(b.getAttribute('aria-pressed')!=='true'||document.querySelectorAll('#search-modes [aria-pressed=true]').length!==1)throw Error('inconsistent selection')}}''')
                            expect(p.locator('#query')).to_have_value('Keep this query')
                            title=p.locator('[data-search-mode=title]');title.focus();title.press('Space');expect(title).to_have_attribute('aria-pressed','true')
                            artist=p.locator('[data-search-mode=artist]');artist.focus();artist.press('Enter');expect(artist).to_have_attribute('aria-pressed','true')
                            assert artist.evaluate('(e)=>parseFloat(getComputedStyle(e).outlineWidth)')>=2
                            if area=='listening':p.screenshot(path=str(OUT/f'focus-{lang}-{width}.png'),full_page=True)
                            boxes=[p.locator(x).bounding_box() for x in ['[data-search-mode=artist]','[data-search-mode=title]','#manual-add-trigger','#query','#search-btn']]
                            for i,a in enumerate(boxes):
                                assert a['x']>=0 and a['x']+a['width']<=width+.1
                                for b in boxes[i+1:]:assert a['x']+a['width']<=b['x']+.1 or b['x']+b['width']<=a['x']+.1 or a['y']+a['height']<=b['y']+.1 or b['y']+b['height']<=a['y']+.1,(width,lang,a,b)
                            assert abs(boxes[0]['y']-boxes[2]['y'])<1 and boxes[3]['y']>=boxes[0]['y']+44
                            assert p.locator('#query').evaluate('(e)=>parseFloat(getComputedStyle(e).fontSize)')>=16
                            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
                            p.locator('#insights-screen').click();p.locator('#ui-language').select_option('en' if lang=='ja' else 'ja');p.locator('#ui-language').select_option(lang);p.locator('#archive-screen').click()
                            expect(artist).to_have_attribute('aria-pressed','true');expect(p.locator('#query')).to_have_value('Keep this query')
                            p.locator('#query').fill('');p.locator('#query').blur()
                            measurements.append(dict(width=width,lang=lang,area=area,buttons=sizes,rapidClicks=200,dbWrites=0,apiCalls=0,overlap=False))
                        p.screenshot(path=str(OUT/f'{phase}-{area}-{lang}-{width}.png'),full_page=True)
                        if phase=='after':
                            p.locator('#manual-add-trigger').click();expect(p.locator('#modal')).to_be_visible();p.locator('#close').click()
                    assert p.evaluate('writes')==0 and stored(p)==SEED and not errors and not calls,(errors,calls)
                    print(f'PASS {phase} {lang} {width}',flush=True);ctx.close()
        browser.close()
    (OUT/'measurements.json').write_text(json.dumps(measurements,indent=2));server.shutdown()

if __name__=='__main__':main()
