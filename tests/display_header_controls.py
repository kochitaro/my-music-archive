"""PR35 header-only change: before/after geometry, appearance, Live pixels and storage."""
import copy, json, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from display_options import seed, PREF
from display_simplification import header, assert_header, cards
OUT=ROOT/'docs/display-header-controls-evidence';OUT.mkdir(exist_ok=True)
BASE='3895564419d4137758bc9f850bf3ac4ee49ba945'
data=copy.deepcopy(seed)
for area in ['listening','collection']:
 data[area]=[{**seed[area][i%6],'entryId':area+'-'+str(i)} for i in range(60)]
data['live']=[dict(entryId='live',title='Live sample',venue='Tokyo',date='2026-11-10',rating='8.6')]

def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/'
 old=subprocess.check_output(['git','show',BASE+':index.html']).decode();results=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for width in [320,375,390,430]:
   for lang in ['ja','en']:
    versions={}
    for phase in ['before','after']:
     c=b.new_context(viewport=dict(width=width,height=844),has_touch=True);c.route('https://**/*',lambda r:r.abort())
     if phase=='before':c.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
     c.add_init_script("""window.dbWrites=0;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03')dbWrites++;return set.call(this,k,v)}""")
     p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(url)
     prefs={a:['genre','label','rating'] for a in ['listening','collection']}
     p.evaluate('([k,s,l,pk,pref])=>{localStorage.setItem(k,JSON.stringify(s));localStorage.setItem("mma-ui-language",l);localStorage.setItem(pk,JSON.stringify(pref))}',[KEY,data,lang,PREF,prefs]);p.reload()
     raw=p.evaluate('(k)=>localStorage.getItem(k)',KEY);pref_raw=p.evaluate('(k)=>localStorage.getItem(k)',PREF);versions[phase]={}
     for area in ['listening','collection','live']:
      p.locator(f'[data-section={area}]').click()
      p.evaluate('document.fonts.ready')
      metrics=header(p)
      png=p.locator('.archive-heading').screenshot(path=str(OUT/f'{phase}-{area}-{lang}-{width}.png'))
      if area=='live':
       assert p.locator('#display-options').is_hidden()
       versions[phase][area]=dict(metrics=metrics,png=png)
      else:
       # Wide enough group, right-aligned, no overlap, even with a four-digit count.
       if phase=='after':
        assert_header(p,metrics)
        assert abs(metrics['segments']['right']-metrics['container']['right'])<.1
        assert p.locator('.archive-heading button').evaluate_all('(ns)=>ns.map(n=>n.id)')==['display-options','grid-tab','list-tab']
        p.locator('#count').evaluate('(e)=>e.textContent="(9999)"');assert_header(p,header(p));p.locator('#count').evaluate('(e)=>e.textContent="(60)"')
        style=p.locator('#display-options').evaluate('''e=>{const s=getComputedStyle(e);return {border:s.borderWidth,radius:s.borderRadius,background:s.backgroundColor,color:s.color}}''')
        assert style==dict(border='0px',radius='0px',background='rgba(0, 0, 0, 0)',color='rgb(161, 173, 188)'),style
       geometry=cards(p)
       p.locator('#display-options').click();expect(p.locator('#display-modal')).to_have_class('modal open')
       modal=p.locator('#display-modal').inner_html()
       p.keyboard.press('Escape');expect(p.locator('#display-options')).to_be_focused()
       p.locator('#display-options').click();p.locator('#display-close').click();expect(p.locator('#display-modal')).not_to_have_class('modal open')
       p.locator('#list-tab').click();expect(p.locator('#list-tab')).to_have_attribute('aria-pressed','true');assert p.locator('.tile-slot').count()==0
       listing=p.locator('#library').inner_html()
       p.locator('#grid-tab').click();expect(p.locator('#grid-tab')).to_have_attribute('aria-pressed','true');assert p.locator('.tile-slot').count()==180
       versions[phase][area]=dict(cards=geometry,list=listing,modal=modal)
       if phase=='after':results.append(dict(width=width,lang=lang,area=area,header=metrics,style=style,dbWrites=0))
      assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw and p.evaluate('dbWrites')==0
      assert p.evaluate('(k)=>localStorage.getItem(k)',PREF)==pref_raw
     assert not errors,errors;c.close()
    assert versions['before']==versions['after'],(width,lang,'Live header/cards/list/modal changed')
    print('PASS',width,lang,'both archives: settings left, grid/list right, 44px, muted; Live pixel-identical; modal/list/cards unchanged; DB writes 0',flush=True)
  b.close()
 (OUT/'measurements.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
