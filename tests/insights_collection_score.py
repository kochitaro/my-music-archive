"""Round-four Collection ranking and Live metadata order, synthetic records only."""
import copy,json,threading
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from insights_polish import E,SEED,SNAP,order
from ui_v0322 import KEY,QuietHandler

def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
 seed=copy.deepcopy(SEED);seed['collection']=copy.deepcopy(SEED['collection']);seed['listening'][0]['rating']='0';seed['collection'][3].update(rating='0',date='',release='');seed['collection'][5].update(title='Duplicate purchase',artist='Same artist',rating='8');seed['collection'][6].update(title='Duplicate purchase',artist='Same artist',rating='8')
 seed['live'][0].update(title='長い公演名 Long Festival '*10,venue='長い会場名 Long Venue '*10)
 seed['live'][1]['venue']='';seed['live'][2]['date']='';seed['live'][3].update(venue='',date='',rating='10')
 expected=sorted([r for r in seed['collection'] if r.get('rating') not in ['',None]],key=lambda r:-float(r['rating']))
 expected_ranks=[next(j+1 for j,x in enumerate(expected) if float(x['rating'])==float(r['rating'])) for r in expected]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  def context(width=390,lang='en',old=None):
   ctx=browser.new_context(viewport=dict(width=width,height=844),is_mobile=True,has_touch=True);ctx.route('https://**/*',lambda r:r.abort());ctx.add_init_script('if(!localStorage.getItem('+json.dumps(KEY)+'))localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(seed))+');localStorage.setItem("mma-ui-language",'+json.dumps(lang)+')'+(' ;if(!localStorage.getItem("mla-insights-layout-v1:collection"))localStorage.setItem("mla-insights-layout-v1:collection",'+json.dumps(json.dumps(old))+')' if old else ''));p=ctx.new_page();p.clock.set_fixed_time(datetime(2026,11,27,tzinfo=timezone.utc));p.goto(base);p.evaluate('MLAReady');return ctx,p
  def area(p,a):p.locator('[data-section='+a+']').click();p.locator('#insights-screen').click();return p.locator('#'+a+'-insights')
  for width in [320,375,390,393,430]:
   for lang in ['ja','en']:
    ctx,p=context(width,lang);root=area(p,'collection');rank=root.locator('[data-insight=score]');errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
    more='さらに表示' if lang=='ja' else 'Show more';collapse='折りたたむ' if lang=='ja' else 'Collapse';purchase='購入年' if lang=='ja' else 'Purchase Year';release='リリース年' if lang=='ja' else 'Release Year'
    assert order(root)==['artists','score','genre','tags','label','store','format','time','release'];assert rank.locator('li').count()==15;assert rank.locator('select').input_value()=='';expect(rank.get_by_role('button',name=release,exact=True)).to_have_attribute('aria-pressed','true')
    assert rank.locator('label').evaluate('(e)=>[...e.childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join("").trim()')==''
    assert rank.locator('select').get_attribute('aria-label')==('対象年' if lang=='ja' else 'Year');assert rank.locator('.rating-number').first.inner_text()=='5.0/5';assert rank.locator('li').first.locator('img').count()==1;assert rank.locator('.art.placeholder').count()>0
    if width==390:rank.screenshot(path=str(E/f'collection-score-{lang}.png'))
    rank.evaluate('(e)=>scrollTo(0,e.getBoundingClientRect().top+scrollY-60)');y=rank.locator('h3').bounding_box()['y'];p.evaluate('window.keptHeading=document.querySelector("#collection-insights [data-insight=score] h3");window.keptArtists=document.querySelector("#collection-insights [data-insight=artists]")');rank.locator('select').select_option('2020');assert rank.locator('li').count()==1;assert abs(rank.locator('h3').bounding_box()['y']-y)<3
    rank.locator('select').select_option('');assert rank.locator('li').count()==15;rank.get_by_role('button',name=more,exact=True).click();assert rank.locator('li').count()==30;rank.get_by_role('button',name=more,exact=True).click();assert rank.locator('li').count()==39
    assert rank.locator('.rating-number').all_inner_texts()==[f'{float(r["rating"])/2:.1f}/5' for r in expected];assert rank.locator('.insight-rank').all_inner_texts()==list(map(str,expected_ranks));assert rank.locator('.insight-score-title').filter(has_text='Duplicate purchase').count()==2
    assert rank.locator('.rating-readout').evaluate_all('(nodes)=>new Set(nodes.map(e=>getComputedStyle(e).color)).size')==1
    rank.get_by_role('button',name=collapse,exact=True).click();assert rank.locator('li').count()==15;assert 0<=rank.locator('h3').bounding_box()['y']<150
    rank.get_by_role('button',name=purchase,exact=True).click();assert rank.locator('li').count()==15;assert rank.locator('select option').all_text_contents()[1:]==['2026','2024'];rank.locator('select').select_option('2024');assert rank.locator('li').count()==15
    rank.get_by_role('button',name=more,exact=True).click();assert rank.locator('li').count()==18
    rank.get_by_role('button',name=release,exact=True).click();assert rank.locator('select').input_value()=='';assert rank.locator('li').count()==15
    assert p.evaluate('keptHeading===document.querySelector("#collection-insights [data-insight=score] h3")&&keptArtists===document.querySelector("#collection-insights [data-insight=artists]")')
    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
    live=area(p,'live').locator('[data-insight=score]');morelive=live.get_by_role('button',name=more,exact=True)
    while morelive.count():morelive.click()
    for r in seed['live']:
     if r.get('rating') in ['',None]:continue
     row=live.locator('li').filter(has=p.get_by_text(r['title'],exact=True));classes=row.locator('.insight-score-info > div').evaluate_all('(nodes)=>nodes.map(e=>e.className)');assert classes==['insight-score-title']+(['insight-score-venue'] if r.get('venue','').strip() else [])+(['insight-score-date'] if r.get('date','').strip() else []),classes
    assert live.locator('img').count()==1;assert live.locator('.art.placeholder').count()>0;assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
    if width==390:live.get_by_role('button',name=collapse,exact=True).click();live.screenshot(path=str(E/f'live-order-{lang}.png'))
    assert not errors,errors;print('PASS',width,lang,'Collection independent rating/ranks/zero/unknown/duplicates/images/year filters/paging/scroll; Live title-venue-date and missing rows',flush=True);ctx.close()
  # Existing Collection configuration must survive adding the new field, and writes affect only layout keys.
  ids=['time','release','artists','format','store','genre','tags','label'];old=dict(version=1,items=[dict(id=x,visible=x!='store') for x in ids]);ctx,p=context(old=old);root=area(p,'collection');assert order(root)==[x for x in ids if x!='store']+['score'];before=p.evaluate(SNAP)
  root.locator('.insight-settings').click();d=p.locator('.insight-layout-modal');assert d.locator('li').count()==9;assert d.locator('input[data-item=score]').is_checked();assert not d.locator('input[data-item=store]').is_checked()
  for _ in range(8):d.locator('button[data-item=score][data-direction="-1"]').click()
  d.get_by_role('button',name='Done',exact=True).click();assert order(root)[0]=='score';assert p.evaluate(SNAP)==before
  p.reload();p.evaluate('MLAReady');root=area(p,'collection');assert order(root)[0]=='score';root.locator('.insight-settings').click();d=p.locator('.insight-layout-modal');d.locator('input[data-item=score]').uncheck();d.get_by_role('button',name='Done',exact=True).click();assert 'score' not in order(root)
  root.locator('.insight-settings').click();d=p.locator('.insight-layout-modal');d.locator('input[data-item=score]').check();d.get_by_role('button',name='Reset to Default',exact=True).click();d.get_by_role('button',name='Done',exact=True).click();assert order(root)[1]=='score';assert len(order(root))==9;assert p.evaluate(SNAP)==before
  print('PASS Collection old layout migration, arbitrary ordering/hide/show/reset, reload, exact IDB invariance',flush=True)
  # Real Collection edit/delete/create/restore updates the ranking and its year choices.
  p.locator('#archive-screen').click();p.locator('#library .coverbtn').filter(has=p.get_by_text('Album 39',exact=True)).click();p.locator('#view-edit').click();slider=p.locator('[data-target=rating] .star-rating');slider.focus();p.keyboard.press('Home');p.locator('#save').click();expect(p.locator('#modal')).not_to_be_visible();p.locator('#insights-screen').click();rank=root.locator('[data-insight=score]');rank.locator('select').select_option('2020');expect(rank.locator('.rating-number')).to_have_text('0.0/5')
  p.locator('#archive-screen').click();p.locator('#library .coverbtn').filter(has=p.get_by_text('Album 39',exact=True)).click();p.locator('#view-edit').click();p.locator('#delete').click();p.locator('#delete-accept').click();expect(p.locator('#modal')).not_to_be_visible();p.locator('#insights-screen').click();assert '2020' not in rank.locator('option').all_text_contents()
  p.locator('#archive-screen').click();p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('Fresh Collection score');p.locator('#manual-artist').fill('Synthetic artist');slider.focus();p.keyboard.press('End');p.locator('#save').click();expect(p.locator('#modal')).not_to_be_visible();p.locator('#insights-screen').click();expect(rank).to_contain_text('Fresh Collection score');expect(rank.locator('.rating-number').first).to_have_text('5.0/5')
  saved=p.evaluate('localStorage.getItem("mla-insights-layout-v1:collection")');p.on('dialog',lambda d:d.accept());p.locator('#import-json').set_input_files(dict(name='synthetic.json',mimeType='application/json',buffer=json.dumps(seed).encode()));expect(rank).not_to_contain_text('Fresh Collection score');expect(rank.locator('select option[value="2020"]')).to_have_count(1);assert p.evaluate('localStorage.getItem("mla-insights-layout-v1:collection")')==saved
  print('PASS Collection real CRUD to 0.0/5.0, deletion/year option refresh, actual JSON restore and layout retention',flush=True);browser.close()
 server.shutdown()
if __name__=='__main__':main()
