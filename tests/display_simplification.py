"""PR35 follow-up: paired evidence, unified options, keyboard and storage isolation."""
import json, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from display_options import seed, PREF
OUT=ROOT/'docs/display-simplification-evidence';OUT.mkdir(exist_ok=True)
BASE='4adf87c9fca848fcb1bd7a09edff22c62890bfd5'

def header(p):
 return p.locator('.archive-heading').evaluate('''e=>{const rect=n=>{const r=n.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};const h=e.querySelector('h2'),range=document.createRange();range.selectNodeContents(h);const t=range.getBoundingClientRect();return {container:rect(e),heading:rect(h),text:{x:t.x,right:t.right,w:t.width,h:t.height},buttons:[...e.querySelectorAll('button:not([hidden])')].map(rect),segments:rect(e.querySelector('.view-segments')),controls:rect(e.querySelector('.archive-controls')),font:getComputedStyle(h).fontSize,countFont:getComputedStyle(e.querySelector('#count')).fontSize,icons:[...e.querySelectorAll('button:not([hidden]) svg')].map(rect)}}''')

def assert_header(p,m):
 assert m['text']['right']<=m['buttons'][0]['x'],m
 assert abs(m['heading']['y']+m['heading']['h']/2-m['buttons'][0]['y']-22)<1,m
 assert m['text']['h']<=m['heading']['h']+1,m
 assert all(b['w']>=44 and b['h']>=44 for b in m['buttons']),m
 assert abs(m['buttons'][2]['x']-m['segments']['right']-12)<.1,m
 assert all(i['w']==18 and i['h']==18 for i in m['icons']),m
 assert m['controls']['right']<=m['container']['right']+.1,m
 assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')

def cards(p):
 return p.locator('.album-tile').evaluate_all('''ns=>ns.map(n=>{const r=n.getBoundingClientRect();return {w:r.width,h:r.height,text:n.textContent,children:[...n.querySelectorAll('.art,.title,.muted.small,.tile-slot')].map(e=>{const x=e.getBoundingClientRect();return [x.x-r.x,x.y-r.y,x.width,x.height]})}})''')

def functional(p,area):
 check=lambda f:p.locator(f'[data-display-field={f}]')
 order=lambda:p.locator('#display-choices [data-order-field]').evaluate_all('(ns)=>ns.map(n=>n.dataset.orderField)')
 assert p.locator('#display-selected').count()==0 and p.locator('#display-order-help').count()==0
 assert p.locator('#display-choices li').count()==(8 if area=='collection' else 6)
 assert order()==['genre','label','rating']
 for li in p.locator('#display-choices li').all():
  assert li.locator('input').count()==1
  assert li.locator('button').count()==(2 if li.locator('input').is_checked() else 0)
 assert check('date').is_disabled()
 check('label').uncheck();assert order()==['genre','rating']
 check('date').check();assert order()==['genre','rating','date']
 p.locator('[data-move=up][data-field=date]').focus();p.keyboard.press('Enter');assert order()==['genre','date','rating']
 p.keyboard.press('Enter');assert order()==['date','genre','rating']
 expect(check('date')).to_be_focused()
 p.keyboard.press('Space');assert order()==['genre','rating']
 check('label').check();assert order()==['genre','rating','label']
 p.locator('[data-move=down][data-field=rating]').click();assert order()==['genre','label','rating']
 assert p.locator('#display-save-status').inner_text()=='' and not p.locator('#display-save-status').is_visible()
 p.locator('#display-close').focus();p.keyboard.press('Shift+Tab');expect(p.locator('#display-reset')).to_be_focused()
 p.keyboard.press('Tab');expect(p.locator('#display-close')).to_be_focused()
 p.keyboard.press('Escape');expect(p.locator('#display-options')).to_be_focused()
 p.reload();p.locator(f'[data-section={area}]').click();p.locator('#display-options').click();assert order()==['genre','label','rating']
 p.evaluate('window.failPreference=true');check('rating').uncheck();assert p.locator('#display-save-status').is_visible()
 p.evaluate('window.failPreference=false');check('rating').check();assert not p.locator('#display-save-status').is_visible()
 other='collection' if area=='listening' else 'listening'
 assert p.evaluate('([k,a])=>JSON.parse(localStorage.getItem(k))[a]',[PREF,other])==['genre','label','rating']
 p.locator('#display-reset').click();assert p.evaluate('([k,a])=>JSON.parse(localStorage.getItem(k))[a]',[PREF,area]) is None
 assert not p.locator('#display-save-status').is_visible()
 p.keyboard.press('Escape')

def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/'
 old=subprocess.check_output(['git','show',BASE+':index.html']).decode();results=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for width in [320,375,390,430]:
   for lang in ['ja','en']:
    for area in ['listening','collection']:
     versions={}
     for phase in ['before','after']:
      c=b.new_context(viewport=dict(width=width,height=844),has_touch=True);c.route('https://**/*',lambda r:r.abort())
      if phase=='before':c.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
      c.add_init_script("""window.dbWrites=0;window.failPreference=false;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03')dbWrites++;if(k==='mma-ui-grid-display-v1'&&window.failPreference)throw Error('quota');return set.call(this,k,v)}""")
      p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(url)
      prefs={a:['genre','label','rating'] for a in ['listening','collection']}
      p.evaluate('([k,s,l,pk,pref])=>{localStorage.setItem(k,JSON.stringify(s));localStorage.setItem("mma-ui-language",l);localStorage.setItem(pk,JSON.stringify(pref))}',[KEY,seed,lang,PREF,prefs]);p.reload()
      raw=p.evaluate('(k)=>localStorage.getItem(k)',KEY);p.locator(f'[data-section={area}]').click()
      p.locator('#sort-toggle').click();p.locator('#group').select_option('none');p.locator('#sort-toggle').click()
      p.locator('.archive-heading').screenshot(path=str(OUT/f'{phase}-header-{area}-{lang}-{width}.png'))
      m=header(p);versions[phase]=cards(p)
      p.locator('#display-options').click();p.locator('#display-modal .dialog').screenshot(path=str(OUT/f'{phase}-modal-{area}-{lang}-{width}.png'))
      if phase=='after':
       functional(p,area)
       p.locator('#count').evaluate('(e)=>e.textContent="(9999)"');stress=header(p);assert_header(p,stress)
       assert_header(p,m)
       assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw and p.evaluate('dbWrites')==0
       results.append(dict(width=width,lang=lang,area=area,header=m,fourDigitCount=stress,dbWrites=0))
      assert not errors,errors;c.close()
     assert versions['before']==versions['after'],(width,lang,area,'custom cards changed')
     print('PASS',width,lang,area,'single row; single list; keyboard; storage; cards unchanged',flush=True)
  b.close()
 (OUT/'measurements.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
