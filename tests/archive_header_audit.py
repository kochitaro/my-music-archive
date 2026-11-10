"""PR35: inspect real CSS/background pixels and left/right alignment without altering the app."""
import copy, hashlib, json, subprocess, threading
from io import BytesIO
from PIL import Image
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from display_options import seed, PREF
from display_simplification import header, assert_header
OUT=ROOT/'docs/archive-header-audit';OUT.mkdir(exist_ok=True)
BASE='1356248c92678f5ddc82f4c54d69c4b513986326'
data=copy.deepcopy(seed)
data['live']=[dict(entryId='live',title='Live sample',venue='Tokyo',date='2026-11-10',rating='8.6')]

def styles(p):
 return p.locator('#archive-panel').evaluate('''panel=>{const names=['#archive-panel','.archive-heading','.archive-heading h2','.archive-controls','#display-options','#grid-tab','#list-tab'];const take=(e,pseudo)=>{const s=getComputedStyle(e,pseudo);return Object.fromEntries(['backgroundColor','backgroundImage','boxShadow','borderTopWidth','borderRightWidth','borderBottomWidth','borderLeftWidth','borderRadius','display','justifyContent','alignItems','gap','fontSize','fontWeight','color','content','outlineWidth','outlineColor'].map(k=>[k,s[k]]))};return Object.fromEntries(names.map(k=>{const e=panel.matches(k)?panel:panel.querySelector(k);return [k,{style:take(e),before:take(e,'::before'),after:take(e,'::after')}]}))}''')

def main():
 old=subprocess.check_output(['git','show',BASE+':index.html']).decode()
 assert (ROOT/'index.html').read_text()==old,'This audit expects the app to be unchanged; investigate before adjusting CSS.'
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/';results=[]
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
      p.locator(f'[data-section={area}]').click();p.locator('#sort-toggle').click();p.locator('#group').select_option('none');p.locator('#sort-toggle').click();p.evaluate('document.fonts.ready')
      panel=p.locator('#archive-panel');png=panel.screenshot(path=str(OUT/f'{phase}-panel-{area}-{lang}-{width}.png'))
      metrics=header(p);css=styles(p);panel_rect=panel.bounding_box()
      header_png=p.locator('.archive-heading').screenshot(path=str(OUT/f'{phase}-header-{area}-{lang}-{width}.png'))
      if (width,lang,area) in [(320,'ja','listening'),(390,'ja','listening'),(390,'en','collection')]:
       scroll_y=p.evaluate('scrollY');p.evaluate('window.scrollTo(0,0)');p.screenshot(path=str(OUT/f'{phase}-page-{area}-{lang}-{width}.png'),full_page=True);p.evaluate('(y)=>window.scrollTo(0,y)',scroll_y)
      # Sample the blank header gap and panel padding, preserving original screenshot bytes.
      im=Image.open(BytesIO(png)).convert('RGB');x=int((metrics['text']['right']+metrics['buttons'][0]['x'])/2-panel_rect['x']);y=int(metrics['container']['y']-panel_rect['y']+22)
      points=[(x,y),(5,y),(5,y+52),(im.width-6,y),(im.width-6,y+52)]
      pixels=[dict(x=x,y=y,rgb=list(im.getpixel((x,y)))) for x,y in points]
      assert all(v['rgb']==[28,34,43] for v in pixels),pixels
      assert css['#archive-panel']['style']['backgroundColor']=='rgb(28, 34, 43)'
      for selector in ['.archive-heading','.archive-controls','.archive-heading h2']:
       s=css[selector]['style'];assert s['backgroundColor']=='rgba(0, 0, 0, 0)' and s['backgroundImage']=='none' and s['boxShadow']=='none',s
       assert all(s[k]=='0px' for k in ['borderTopWidth','borderRightWidth','borderBottomWidth','borderLeftWidth']),s
       assert css[selector]['before']['content']=='none' and css[selector]['after']['content']=='none'
      assert css['.archive-heading']['style']['justifyContent']=='space-between'
      assert abs(metrics['heading']['x']-metrics['container']['x'])<.1
      assert abs(metrics['segments']['right']-metrics['container']['right'])<.1
      if area!='live':
       assert_header(p,metrics)
       assert css['#display-options']['style']['backgroundColor']=='rgba(0, 0, 0, 0)'
       assert css['#display-options']['style']['borderTopWidth']=='0px'
       # Visible keyboard focus remains available on the transparent action.
       p.locator('#grid-tab').focus();p.keyboard.press('Shift+Tab');expect(p.locator('#display-options')).to_be_focused()
       focus=p.locator('#display-options').evaluate('(e)=>({visible:e.matches(":focus-visible"),outline:getComputedStyle(e).outlineWidth})');assert focus['visible'] and focus['outline']=='2px',focus
       p.keyboard.press('Enter');expect(p.locator('#display-modal')).to_have_class('modal open');p.keyboard.press('Escape')
       p.locator('#list-tab').click();assert p.locator('.listrow').count()==len(data[area]);p.locator('#grid-tab').click();assert p.locator('.album-tile').count()==len(data[area])
      else:assert p.locator('#display-options').is_hidden()
      assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw and p.evaluate('dbWrites')==0
      assert p.evaluate('(k)=>localStorage.getItem(k)',PREF)==pref_raw
      versions[phase][area]=dict(panelHash=hashlib.sha256(png).hexdigest(),headerHash=hashlib.sha256(header_png).hexdigest(),css=css,metrics=metrics)
      if phase=='after':results.append(dict(width=width,lang=lang,area=area,metrics=metrics,css=css,backgroundPixels=pixels,dbWrites=0,panelUnchanged=True))
     assert not errors,errors;c.close()
    assert versions['before']==versions['after'],(width,lang,'rendered app changed')
    print('PASS',width,lang,'left/right aligned; transparent header; continuous panel pixels; before/after identical; Live unchanged; DB writes 0',flush=True)
  b.close()
 (OUT/'measurements.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 print('PASS app HTML/CSS/JavaScript unchanged from',BASE,flush=True)
if __name__=='__main__':main()
