"""Actual 14px tab ink / 2px underline pixels; all sections, states and widths."""
import json, subprocess, threading
from http.server import ThreadingHTTPServer
from io import BytesIO
from PIL import Image
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, stored
from top_hierarchy import SEED
from search_underline import geometry

OUT=ROOT/'docs/archive-tab-underline-evidence'

def pixels(png):
    im=Image.open(BytesIO(png)).convert('RGB');ink=[];line=[];bg=(17,21,27);fg=(198,231,239);v=[fg[i]-bg[i] for i in range(3)];den=sum(t*t for t in v)
    for y in range(im.height):
        for x in range(im.width):
            c=im.getpixel((x,y))
            if sum(abs(c[i]-(159,207,220)[i]) for i in range(3))<4:line.append((x,y))
            t=sum((c[i]-bg[i])*v[i] for i in range(3))/den
            if .15<t<1.01 and sum((c[i]-bg[i]-t*v[i])**2 for i in range(3))<5:ink.append((x,y))
    assert ink and line
    return dict(gap=min(y for x,y in line)-max(y for x,y in ink)-1,lineWidth=max(x for x,y in line)-min(x for x,y in line)+1,inkWidth=max(x for x,y in ink)-min(x for x,y in ink)+1,lineThickness=max(y for x,y in line)-min(y for x,y in line)+1)

def placement(p):
    return p.locator('#screen-switch').evaluate('''e=>{const a=e.children[0].getBoundingClientRect(),b=e.children[1].getBoundingClientRect(),r=e.getBoundingClientRect();return {center:r.x+r.width/2,gap:b.x-a.right}}''')

def main():
    OUT.mkdir(exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';baseline=subprocess.check_output(['git','show','5ff94eb:index.html'],cwd=ROOT).decode();measurements=[];before={}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for phase in ['before','after']:
            for width in [320,375,390,430,1280]:
                for lang in ['ja','en']:
                    ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=width<600,has_touch=width<600,device_scale_factor=1)
                    calls=[];ctx.route('https://**/*',lambda r:(calls.append(r.request.url),r.abort()))
                    if phase=='before':ctx.route(base+'/',lambda r:r.fulfill(body=baseline,content_type='text/html'))
                    p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
                    p.goto(base);p.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,SEED,lang]);p.reload()
                    p.evaluate('''key=>{window.writes=0;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k===key)writes++;return set.call(this,k,v)}}''',KEY)
                    for area in ['listening','collection','live']:
                        p.locator(f'[data-section={area}]').click()
                        if area!='live':p.locator('#query').fill('Keep query')
                        positions={m:geometry(p.locator('#'+m+'-screen')) for m in ['archive','insights']}
                        for mode in ['archive','insights']:
                            button=p.locator('#'+mode+'-screen');button.click();button.blur()
                            expect(button).to_have_attribute('aria-pressed','true');expect(p.locator('#screen-switch [aria-pressed=true]')).to_have_count(1)
                            if mode=='insights':expect(p.locator(f'#{area}-insights')).to_be_visible()
                            elif area!='live':expect(p.locator('#query')).to_have_value('Keep query')
                            actual=geometry(button);paint=pixels(button.screenshot());pos=placement(p);key=(width,lang,area,mode)
                            assert actual['button']['width']>=44 and actual['button']['height']>=44
                            assert abs(pos['center']-width/2)<.1 and pos['gap']==12,pos
                            if phase=='before':before[key]=dict(geometry=actual,pixels=paint,placement=pos)
                            else:
                                assert paint['gap'] in [3,4] and paint['lineThickness']==2,paint
                                assert abs(paint['lineWidth']-paint['inkWidth'])<=4,paint
                                assert pos==before[key]['placement']
                                for part in ['button','text']:
                                    for prop in ['x','y','width','height']:assert abs(actual[part][prop]-before[key]['geometry'][part][prop])<.02,(key,actual,before[key])
                                for m,g in positions.items():assert geometry(p.locator('#'+m+'-screen'))==g
                                style=button.evaluate('(e)=>{const s=getComputedStyle(e);return {size:s.fontSize,weight:s.fontWeight,color:s.color,bg:s.backgroundColor}}')
                                assert style==dict(size='14px',weight='400',color='rgb(198, 231, 239)',bg='rgba(0, 0, 0, 0)')
                                other=p.locator('#'+('insights' if mode=='archive' else 'archive')+'-screen')
                                assert other.evaluate('(e)=>getComputedStyle(e).textDecorationLine')=='none'
                                assert other.evaluate('(e)=>getComputedStyle(e).color')=='rgb(161, 173, 188)'
                                assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
                                measurements.append(dict(width=width,lang=lang,area=area,mode=mode,before=before[key]['pixels'],after=paint,geometry=actual,placement=pos,layoutShift=0,dbWrites=0))
                            p.screenshot(path=str(OUT/f'{phase}-{area}-{mode}-{lang}-{width}.png'),full_page=True)
                        if phase=='after':
                            button.focus();button.press('Space');assert button.evaluate('(e)=>parseFloat(getComputedStyle(e).outlineWidth)')>=2
                            if area=='listening':p.screenshot(path=str(OUT/f'focus-{lang}-{width}.png'),full_page=True)
                    assert p.evaluate('writes')==0 and stored(p)==SEED and not errors and not calls,(errors,calls)
                    print(f'PASS {phase} {lang} {width}',flush=True);ctx.close()
        browser.close()
    (OUT/'measurements.json').write_text(json.dumps(measurements,indent=2));server.shutdown()

if __name__=='__main__':main()
