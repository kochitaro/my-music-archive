"""Synthetic app/browser evidence for Insights polish; no external metadata requests."""
import json,threading
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from data_preservation import PHOTO
from ui_v0322 import ROOT,KEY,QuietHandler,album
E=ROOT/'docs/insights-polish-01';E.mkdir(exist_ok=True)
def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start()
 records=[dict(album('Album '+str(i)),rating=str(10-i%11),artist='Artist '+str(i),genre='Genre '+str(i),label='Label '+str(i),tags=['Tag '+str(i)],date='2026-09-01' if i%2 else '2026-11-01',release=str(1900+i*5)) for i in range(40)]
 records[0].update(title='長い作品名 / Long album title '*5,artist='長いアーティスト / Long artist '*5,photo=PHOTO)
 records[1]['id']='12345678-1234-1234-1234-123456789abc';records[2]['rating']='';records[3].update(date='',release='')
 seed=dict(version=3,listening=records,collection=records,live=[dict(entryId=str(i),title='Show',date=r['date'],artists=['Artist'],venue=r['genre']) for i,r in enumerate(records)])
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for width in [320,375,390,393,430]:
   for lang in ['ja','en']:
    ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=True,has_touch=True);ctx.route('https://**/*',lambda r:r.abort());p=ctx.new_page();p.set_default_timeout(6000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    p.clock.set_fixed_time(datetime(2026,11,27,tzinfo=timezone.utc));ctx.add_init_script('localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(seed))+');localStorage.setItem("mma-ui-language",'+json.dumps(lang)+')');p.goto(f'http://127.0.0.1:{server.server_port}');p.evaluate('MLAReady');p.locator('#insights-screen').click();raw=p.evaluate('(k)=>localStorage.getItem(k)',KEY)
    for area in ['listening','collection','live']:
     p.locator(f'[data-section={area}]').click();p.locator('#insights-screen').click();root=p.locator(f'#{area}-insights');field='venue' if area=='live' else 'genre';cat=root.locator(f'[data-insight={field}]');assert cat.locator('.insight-legend li').count()==16,(area,p.locator('body').inner_text(),errors)
     assert cat.locator('.insight-center strong').inner_text()=='40';assert cat.locator('.insight-center').evaluate('(e)=>{const c=e.getBoundingClientRect(),d=e.parentElement.getBoundingClientRect();return Math.abs(c.x+c.width/2-d.x-d.width/2)<1&&Math.abs(c.y+c.height/2-d.y-d.height/2)<1}');assert cat.locator('circle').count()==16
     time=root.locator('[data-insight=time]');assert time.locator('rect').count()==3;assert '2026-10: 0' in time.locator('svg').get_attribute('aria-label')
     if width==390:cat.screenshot(path=str(E/f'{area}-{lang}-donut.png'));time.screenshot(path=str(E/f'{area}-{lang}-monthly.png'))
     time.get_by_role('button',name='年別' if lang=='ja' else 'Yearly',exact=True).click();assert time.locator('li').count()==1
     assert time.locator('.insight-name').evaluate('(e)=>getComputedStyle(e).whiteSpace')=='nowrap'
     if width==390:time.screenshot(path=str(E/f'{area}-{lang}-yearly.png'))
     if area!='live':
      rel=root.locator('[data-insight=release]');
      if width==390:rel.screenshot(path=str(E/f'{area}-{lang}-release-year.png'))
      rel.get_by_role('button',name='年代別' if lang=='ja' else 'By Decade',exact=True).click();assert rel.locator('svg').count()==3
      if width==390:rel.screenshot(path=str(E/f'{area}-{lang}-decades.png'))
     else:assert root.locator('[data-insight=score]').count()==0
     assert p.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,lang,area)
    p.locator('[data-section=listening]').click();p.locator('#insights-screen').click();rank=p.locator('[data-insight=score]');assert rank.locator('li').count()==15;assert rank.locator('select').input_value()==''
    assert rank.locator('.rating-number').first.inner_text()=='5.0/5';assert rank.locator('li').first.locator('img').count()==1
    rank.get_by_role('button',name='さらに表示' if lang=='ja' else 'Show more',exact=True).click();assert rank.locator('li').count()==30
    rank.get_by_role('button',name='さらに表示' if lang=='ja' else 'Show more',exact=True).click();assert rank.locator('li').count()==39;assert '0.0/5' in rank.inner_text()
    rank.get_by_role('button',name='鑑賞年' if lang=='ja' else 'Listening Year',exact=True).click();rank.locator('select').select_option('2026');assert rank.locator('select option').count()==2
    rank.get_by_role('button',name='リリース年' if lang=='ja' else 'Release Year',exact=True).click();assert rank.locator('select').input_value()==''
    if width==390:rank.screenshot(path=str(E/f'score-{lang}.png'))
    assert p.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw;assert not errors,errors
    print('PASS',width,lang,'3 areas / chart forms / periods / ranking paging and selection / no overflow / no archive writes',flush=True);ctx.close()
  # Real score create/edit/delete and restore freshness through application controls.
  ctx=browser.new_context(viewport=dict(width=320,height=844));ctx.route('https://**/*',lambda r:r.abort());p=ctx.new_page();p.goto(f'http://127.0.0.1:{server.server_port}');p.evaluate('MLAReady')
  p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Fresh scored');p.locator('#manual-artist').fill('Fresh artist');slider=p.locator('[data-target=rating] .star-rating');slider.focus();p.keyboard.press('End');p.locator('#save').click();expect(p.locator('#modal')).not_to_be_visible();p.locator('#insights-screen').click()
  rank=p.locator('[data-insight=score]');expect(rank.locator('.rating-number')).to_have_text('5.0/5')
  p.locator('#archive-screen').click();p.locator('#library .coverbtn').filter(has_text='Fresh scored').click();p.locator('#view-edit').click();slider.focus();p.keyboard.press('Home');p.locator('#save').click();expect(p.locator('#modal')).not_to_be_visible();p.locator('#insights-screen').click();expect(rank.locator('.rating-number')).to_have_text('0.0/5')
  p.locator('#archive-screen').click();p.locator('#library .coverbtn').filter(has_text='Fresh scored').click();p.locator('#view-edit').click();p.locator('#delete').click();p.locator('#delete-accept').click();expect(p.locator('#modal')).not_to_be_visible();p.locator('#insights-screen').click();assert rank.locator('li').count()==0
  p.on('dialog',lambda d:d.accept());p.locator('#import-json').set_input_files(dict(name='synthetic.json',mimeType='application/json',buffer=json.dumps(seed).encode()));expect(rank.locator('li')).to_have_count(15);expect(rank.locator('.rating-number').first).to_have_text('5.0/5');p.locator('#ui-language').select_option('ja');expect(rank.locator('h3')).to_have_text('スコアランキング')
  print('PASS score create / edit to 0.0 / delete / real JSON restore / live language update',flush=True)
  # Pure renderer edge cases for tiny segments and huge counts; same production component.
  ctx=browser.new_context(viewport=dict(width=320,height=844));p=ctx.new_page();p.goto(f'http://127.0.0.1:{server.server_port}');p.evaluate('MLAReady');p.locator('#insights-screen').click()
  for n in [0,1,10,15,16,70]:
   p.evaluate('n=>MLAInsights.render(document.querySelector("#listening-insights"),Array.from({length:n},(_,i)=>({genre:"Long category "+i,date:"2026-11",release:"2026"})),"listening",false,new Date(2026,10,27))',n)
   assert p.locator('#listening-insights circle').count()==min(16,n)
  p.evaluate("""()=>{const source=Array.from({length:12000},(_,i)=>({genre:i?'Large':'Tiny',date:(i%12===0?'2025-12':'2026-'+String(i%12).padStart(2,'0'))}));MLAInsights.render(document.querySelector('#listening-insights'),source,'listening',false,new Date(2026,10,27))}""")
  assert p.locator('#listening-insights [data-insight=time] rect').count()==12
  assert p.locator('#listening-insights circle').evaluate_all('(nodes)=>nodes.every(e=>Number(e.getAttribute("stroke-dasharray").split(" ")[0])>0)')
  assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
  p.locator('#listening-insights [data-insight=time]').screenshot(path=str(E/'large-monthly-320.png'))
  print('PASS renderer empty / 1 / 10 / 15 / 16 / 70 categories',flush=True)
  browser.close()
 server.shutdown()
if __name__=='__main__':main()
