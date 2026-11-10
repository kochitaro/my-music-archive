"""Group-owned single settings action + Live grid: synthetic Chromium and data protection."""
import copy, json, os, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, stored, assert_hearts, choose
OUT=ROOT/'docs/group-display-live-evidence';OUT.mkdir(exist_ok=True)
PREF='mma-ui-grid-display-v1';BASE='79d2047a6110d4d7f5d9547962eccbf571695dcf'
PHOTO='data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" fill="%237c9dad"/></svg>'
seed=dict(version=3,listening=[],collection=[],live=[])
for area in ['listening','collection']:
 for i in range(6):
  seed[area].append({**album(area+str(i),label='Very long label, Other label',genre='Ambient, Electronic',tags=['夜','Tag']), 'release':['2026-11-10','2026-10-02','2025-02-03','2024','2025-01','2024-01-02'][i], 'date':['2026-11-10','2026-10-02','2025-02-03','2024-01-01','2025-01-02','2024-01-02'][i], 'artist':'Other artist' if i<3 else 'Artist A','rating':'8.6'})
for i in range(6):
 seed['live'].append(dict(entryId='live'+str(i),title=['短い公演名','A very long live show title 日本語とEnglishが混在する公演名','Missing values','Four','Five','Six'][i],date=['2026-11-10','2026-10-02','2025-02-03','2024','2025-01','2024-01-02'][i],venue='' if i==2 else ('Other Hall' if i<3 else 'Very long venue 東京 International Concert Hall'),artists=[] if i==2 else ['Artist A','長い出演者名 Artist B','Third artist'],rating=['8.8','9','','0','10','8.6'][i],memo='' if i==2 else 'Very long memo 日本語のメモ\nSecond line must stay in the details, not expand the card',photo=PHOTO if i==0 else ''))


def button(p,grouped=None):
 if grouped is None:grouped=p.locator("#library > h3").count()>0
 b=p.locator('#display-options');assert b.count()==1 and b.is_visible()
 assert p.locator('.archive-heading #display-options').count()==0
 box=b.bounding_box();assert box['width']>=44 and box['height']>=44
 if grouped:
  assert p.locator('#library > h3').count()>1
  assert p.locator('#library > h3').first.locator('#display-options').count()==1
 else:assert p.locator('#library > .display-options-row #display-options').count()==1
 assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
 b.click();expect(p.locator('#display-modal')).to_have_class('modal open');p.keyboard.press('Escape');expect(b).to_be_focused();b.evaluate('(e)=>e.blur()')


def slot_geometry(p):
 r=p.locator('.live-tile').evaluate_all('''ns=>ns.map(n=>{const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}};return {card:rect(n),art:rect(n.querySelector('.art')),title:rect(n.querySelector('.title')),slots:[...n.querySelectorAll('.tile-slot')].map(rect)}})''')
 rows={}
 for m in r:rows.setdefault(round(m['art']['y']),[]).append(m)
 for row in rows.values():
  for k in ['title']:
   assert max(m[k]['y'] for m in row)-min(m[k]['y'] for m in row)<1
  for i in range(len(row[0]['slots'])):assert max(m['slots'][i]['y'] for m in row)-min(m['slots'][i]['y'] for m in row)<1
 assert all(abs(m['art']['w']-m['art']['h'])<1 for m in r)
 assert p.locator('.live-tile .tile-slot').evaluate_all('(ns)=>ns.every(n=>n.scrollWidth<=n.clientWidth)')
 assert p.locator('.live-tile .rating-readout').evaluate_all('(ns)=>ns.every(n=>n.scrollWidth<=n.clientWidth)')
 return r


def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_port}/';measurements=[]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for lang in ['ja','en']:
   ctx=browser.new_context(viewport=dict(width=390,height=844),has_touch=True,accept_downloads=True);ctx.route('https://**/*',lambda r:r.abort())
   ctx.add_init_script("""window.dbWrites=0;window.failPreference=false;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03')dbWrites++;if(k==='mma-ui-grid-display-v1'&&window.failPreference)throw Error('quota');return set.call(this,k,v)}""")
   p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)));p.goto(url)
   oldprefs=dict(listening=['genre','rating'],collection=['label'])
   p.evaluate('([k,s,l,pk,v])=>{localStorage.setItem(k,JSON.stringify(s));localStorage.setItem("mma-ui-language",l);localStorage.setItem(pk,JSON.stringify(v))}',[KEY,seed,lang,PREF,oldprefs]);p.reload();raw=p.evaluate('(k)=>localStorage.getItem(k)',KEY)
   for area in ['listening','collection','live']:
    p.locator(f'[data-section={area}]').click();sort='date-desc' if area=='live' else 'release-desc'
    for width in [320,375,390,430,1280]:
     p.set_viewport_size(dict(width=width,height=844))
     if p.locator('#sort-wrap').is_hidden():p.locator('#sort-toggle').click()
     p.locator('#sort').select_option(sort)
     for group in ['year','month','week','day','none']:
      p.locator('#group').select_option(group);button(p,group!='none')
      p.locator('#sort-toggle').click()
      measurements.append(dict(kind='placement',area=area,lang=lang,width=width,group=group,button=p.locator('#display-options').bounding_box(),heading=p.locator('#library > h3').first.bounding_box() if group!='none' else None))
      p.locator('#archive-panel').screenshot(path=str(OUT/f'{area}-{lang}-{width}-{group}.png'))
      p.locator('#sort-toggle').click()
     p.locator('#sort').select_option('rating-desc');button(p)
     p.locator('#list-tab').click();button(p);p.locator('#grid-tab').click()
     p.locator('#sort').select_option(sort);p.locator('#group').select_option('year')
     # Real filters with incompatible values produce zero matches.
     choose(p,'year','2024');choose(p,'venue' if area=='live' else 'artist','Other Hall' if area=='live' else 'Other artist')
     assert p.locator('.coverbtn').count()==0;button(p)
     for f in ['year','venue' if area=='live' else 'artist']:p.locator('#'+f+'-filter').select_option('')
     p.locator('#filters-toggle').click();p.locator('#sort-toggle').click()
     print('PASS placement',lang,area,width,flush=True)
    assert p.evaluate('dbWrites')==0 and p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
   # Live defaults contain only title text and preserve photo/placeholder behavior.
   p.locator('[data-section=live]').click();p.locator('#sort-toggle').click();p.locator('#sort').select_option('date-desc');p.locator('#group').select_option('none');p.locator('#sort-toggle').click()
   assert p.locator('.live-tile .muted.small,.live-tile .tile-slot,.live-tile .tile-date,.live-tile .tile-rating').count()==0
   assert p.locator('.live-tile img.art').count()==1 and p.locator('.live-tile .placeholder').count()==5
   for width in [320,375,390,430,1280]:
    p.set_viewport_size(dict(width=width,height=844));m=slot_geometry(p);measurements.append(dict(kind='live',lang=lang,width=width,fields=0,cards=m));p.locator('#archive-panel').screenshot(path=str(OUT/f'live-{lang}-{width}-default.png'))
   p.locator('#display-options').click();expect(p.locator('#display-fixed')).to_have_text('公演名は常に表示' if lang=='ja' else 'Show name is always shown.')
   for i,field in enumerate(['artists','venue','rating']):
    p.locator(f'[data-display-field={field}]').check();assert p.locator('.live-tile .tile-slot').count()==6*(i+1)
    p.locator('#display-close').click()
    for width in [320,375,390,430,1280]:
     p.set_viewport_size(dict(width=width,height=844));m=slot_geometry(p);p.locator('#archive-panel').screenshot(path=str(OUT/f'live-{lang}-{width}-{i+1}-fields.png'));measurements.append(dict(lang=lang,width=width,fields=i+1,cards=m))
    p.locator('#display-options').click()
   assert p.locator('[data-display-field=memo]').is_disabled()
   p.locator('[data-move=up][data-field=rating]').click();p.locator('[data-move=up][data-field=rating]').click()
   assert p.locator('#display-choices [data-order-field]').evaluate_all('(ns)=>ns.map(n=>n.dataset.orderField)')==['rating','artists','venue']
   p.locator('#display-close').click();assert_hearts(p.locator('.live-tile').first.locator('.tile-rating'))
   p.reload();p.locator('[data-section=live]').click();assert p.locator('.live-tile .tile-slot').first.get_attribute('data-field')=='rating'
   pref=p.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',PREF);assert pref['listening']==oldprefs['listening'] and pref['collection']==oldprefs['collection'] and pref['live']==['rating','artists','venue']
   # Every remaining Live field uses saved values and partial dates without padding.
   p.locator('#display-options').click();p.locator('#display-reset').click()
   for field in ['date','memo','artists']:p.locator(f'[data-display-field={field}]').check()
   p.locator('#display-close').click();assert '2024' in p.locator('.tile-slot[data-field=date]').all_text_contents()
   assert p.locator('.tile-slot[data-field=memo]').first.get_attribute('aria-label').endswith(seed['live'][0]['memo'])
   p.locator('.live-tile').first.click();assert seed['live'][0]['memo'] in p.locator('#view-content').inner_text();assert p.locator('.live-artist-list li').all_text_contents()==seed['live'][0]['artists'];p.locator('#view-close').click()
   p.locator('#display-options').click();p.evaluate('failPreference=true');p.locator('[data-display-field=memo]').uncheck();assert p.locator('#display-save-status').is_visible();p.evaluate('failPreference=false');p.locator('#display-reset').click();p.locator('#display-close').click();assert p.locator('.live-tile .tile-slot').count()==0
   p.locator('#insights-screen').click();expect(p.locator('#display-options')).to_be_hidden();p.locator('#archive-screen').click();button(p)
   assert p.evaluate('dbWrites')==0 and p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
   # All archives with genuinely empty records retain an operable action.
   empty=dict(version=3,listening=[],collection=[],live=[]);p.evaluate('([k,s])=>localStorage.setItem(k,JSON.stringify(s))',[KEY,empty]);p.reload()
   for area in ['listening','collection','live']:
    p.locator(f'[data-section={area}]').click()
    for width in [320,375,390,430,1280]:
     p.set_viewport_size(dict(width=width,height=844));button(p);assert p.locator('.empty').is_visible();p.locator('#archive-panel').screenshot(path=str(OUT/f'empty-{area}-{lang}-{width}.png'))
   assert not errors,errors;ctx.close();print('PASS',lang,'3 archives × 5 widths × groups/empty/list; Live 0-3 fields; save/read/DB safety',flush=True)
  browser.close()
 (OUT/'measurements.json').write_text(json.dumps(measurements,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
