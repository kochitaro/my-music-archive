"""Live long memo/partial dates, keyboard controls, corrupted/read-failed UI preferences."""
import json, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import KEY, QuietHandler
from group_display_live import seed, OUT, PREF, slot_geometry

def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/';results=[]
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for lang in ['ja','en']:
   for width in [320,375,390,430,1280]:
    c=b.new_context(viewport=dict(width=width,height=844),has_touch=True);c.route('https://**/*',lambda r:r.abort())
    c.add_init_script("""window.dbWrites=0;const set=Storage.prototype.setItem,get=Storage.prototype.getItem;Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03')dbWrites++;return set.call(this,k,v)};Storage.prototype.getItem=function(k){if(k==='mma-ui-grid-display-v1'&&get.call(this,'test-read-failure')==='1')throw Error('blocked');return get.call(this,k)}""")
    p=c.new_page();p.goto(url);prefs=dict(listening=['genre','rating'],collection=['label'],live=['memo','date','rating'])
    p.evaluate('([k,s,l,pk,v])=>{localStorage.setItem(k,JSON.stringify(s));localStorage.setItem("mma-ui-language",l);localStorage.setItem(pk,JSON.stringify(v))}',[KEY,seed,lang,PREF,prefs]);p.reload();raw=p.evaluate('(k)=>localStorage.getItem(k)',KEY)
    p.locator('[data-section=live]').click();p.locator('#sort-toggle').click();p.locator('#sort').select_option('date-desc');p.locator('#group').select_option('none');p.locator('#sort-toggle').click()
    m=slot_geometry(p);assert set(p.locator('[data-field=date].tile-slot').all_text_contents())=={r['date'].replace('-','/') for r in seed['live']}
    assert p.locator('[data-field=memo].tile-slot').first.evaluate('(e)=>e.getBoundingClientRect().height')==18
    p.locator('#archive-panel').screenshot(path=str(OUT/f'live-memo-date-heart-{lang}-{width}.png'))
    p.locator('#display-options').click();p.locator('#display-modal .dialog').screenshot(path=str(OUT/f'live-modal-{lang}-{width}.png'))
    p.locator('#display-close').focus();p.keyboard.press('Shift+Tab');expect(p.locator('#display-reset')).to_be_focused();p.keyboard.press('Tab');expect(p.locator('#display-close')).to_be_focused()
    p.locator('[data-move=up][data-field=rating]').focus();p.keyboard.press('Enter');p.keyboard.press('Enter');expect(p.locator('[data-display-field=rating]')).to_be_focused();p.keyboard.press('Space');assert p.locator('#display-choices [data-order-field]').count()==2
    p.keyboard.press('Escape');expect(p.locator('#display-options')).to_be_focused()
    for value in [['date','venue','memo','artists'],['rating','rating'],['release']]:
     prefs['live']=value;p.evaluate('([k,v])=>localStorage.setItem(k,JSON.stringify(v))',[PREF,prefs]);p.reload();p.locator('[data-section=live]').click();assert p.locator('.live-tile .tile-slot').count()==0
    p.evaluate('localStorage.setItem("test-read-failure","1")');p.reload();p.locator('[data-section=live]').click();assert p.locator('.live-tile .tile-slot').count()==0
    assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw and p.evaluate('dbWrites')==0
    results.append(dict(lang=lang,width=width,longMemoAndPartialDateGeometry=m,invalidPreferenceSafe=True,readFailureSafe=True,dbWrites=0));c.close()
    print('PASS Live edges',lang,width,'memo/date/heart, keyboard, invalid/read failure, DB unchanged',flush=True)
  b.close()
 (OUT/'live-edges.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
