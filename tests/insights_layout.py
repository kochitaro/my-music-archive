"""Persistent layout safety, conflicts, restoration and scroll regression evidence."""
import json,threading,tempfile,subprocess
from pathlib import Path
from datetime import datetime,timezone
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
from insights_polish import E,SEED,SNAP,order
from ui_v0322 import KEY,ROOT,QuietHandler
PREFIX='mla-insights-layout-v1:'
def main():
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);ctx=browser.new_context(viewport=dict(width=390,height=844));ctx.route('https://**/*',lambda r:r.abort());p=ctx.new_page()
  def ready(page):page.goto(base);page.evaluate('MLAReady');page.locator('#insights-screen').click()
  ready(p);p.on('dialog',lambda d:d.accept());p.locator('#import-json').set_input_files(dict(name='synthetic.json',mimeType='application/json',buffer=json.dumps(SEED).encode()));root=p.locator('#listening-insights');expect(root.locator('[data-insight=score] li')).to_have_count(15)
  def dialog(page):page.locator('#listening-insights .insight-settings').click();return page.locator('.insight-layout-modal')
  before=p.evaluate(SNAP);d=dialog(p);d.locator('input[data-item=genre]').uncheck();d.get_by_role('button',name='Done',exact=True).click();assert p.evaluate(SNAP)==before;assert 'genre' not in order(root)
  # Same-area conflict disables completion; a different area does not conflict.
  d=dialog(p);p2=ctx.new_page();ready(p2);p2.locator('[data-section=collection]').click();p2.locator('#insights-screen').click();p2.locator('#collection-insights .insight-settings').click();p2.locator('.insight-layout-modal input[data-item=store]').uncheck();p2.locator('.insight-layout-modal').get_by_role('button',name='Done',exact=True).click();expect(d.get_by_role('button',name='Done',exact=True)).to_be_enabled()
  p2.locator('[data-section=listening]').click();p2.locator('#insights-screen').click();d2=dialog(p2);d2.locator('button[data-item=score][data-direction="-1"]').click();d2.get_by_role('button',name='Done',exact=True).click();expect(d.get_by_role('button',name='Done',exact=True)).to_be_disabled();expect(d.locator('[role=status]')).to_contain_text('another tab');d.get_by_role('button',name='Cancel',exact=True).click();assert order(root)[0]=='score';assert not root.evaluate('(e)=>e.inert');assert p.evaluate(SNAP)==before
  print('PASS settings IDB byte-equivalence; independent area updates; same-area conflict blocks stale draft',flush=True)
  # Failed preference write: session-only fallback, no archive/meta/photo/settings mutation.
  p.evaluate('''()=>{const set=Storage.prototype.setItem;window.originalSet=set;Storage.prototype.setItem=function(k,v){if(k.startsWith('mla-insights-layout-v1:'))throw new DOMException('synthetic quota','QuotaExceededError');return set.call(this,k,v)}}''');before=p.evaluate(SNAP);d=dialog(p);d.locator('input[data-item=tags]').uncheck();d.get_by_role('button',name='Done',exact=True).click();assert 'tags' not in order(root);expect(root.locator('.insight-layout-error')).to_be_visible();assert p.evaluate(SNAP)==before
  p.reload();p.evaluate('MLAReady');p.locator('#insights-screen').click();assert 'tags' in order(root);assert 'genre' not in order(root)
  print('PASS quota failure session fallback and unchanged archive/photos/meta/settings; reload returns persisted settings',flush=True)
  # Actual restore and language changes do not reset independent layout keys.
  saved=p.evaluate('localStorage.getItem("mla-insights-layout-v1:listening")');p.locator('#import-json').set_input_files(dict(name='synthetic.json',mimeType='application/json',buffer=json.dumps(SEED).encode()));expect(root.locator('[data-insight=score] li')).to_have_count(15);assert p.evaluate('localStorage.getItem("mla-insights-layout-v1:listening")')==saved;assert order(root)[0]=='score'
  with p.expect_download() as item:p.locator('#export-json').click()
  backup=json.loads(Path(item.value.path()).read_text());assert set(backup)==set(SEED);assert not any('layout' in k.lower() for k in backup)
  p.locator('#ui-language').select_option('ja');assert order(root)[0]=='score';p.locator('#ui-language').select_option('en');assert order(root)[0]=='score'
  print('PASS real JSON restore preserves layout, JSON export schema unchanged, live Japanese/English',flush=True)
  # Existing score behavior still refreshes after actual record edits, deletion and creation.
  p.locator('#archive-screen').click();p.locator('#library .coverbtn').filter(has=p.get_by_text('Album 39',exact=True)).click();p.locator('#view-edit').click();slider=p.locator('[data-target=rating] .star-rating');slider.focus();p.keyboard.press('Home');p.locator('#save').click();expect(p.locator('#modal')).not_to_be_visible();p.locator('#insights-screen').click();rank=root.locator('[data-insight=score]');rank.locator('select').select_option('2020');expect(rank.locator('.rating-number')).to_have_text('0.0/5')
  p.locator('#archive-screen').click();p.locator('#library .coverbtn').filter(has=p.get_by_text('Album 39',exact=True)).click();p.locator('#view-edit').click();p.locator('#delete').click();p.locator('#delete-accept').click();expect(p.locator('#modal')).not_to_be_visible();p.locator('#insights-screen').click();assert '2020' not in rank.locator('option').all_text_contents()
  p.locator('#archive-screen').click();p.locator('#manual-add-trigger').click();p.locator('#manual-title').fill('New scored record');p.locator('#manual-artist').fill('Synthetic artist');slider.focus();p.keyboard.press('End');p.locator('#save').click();expect(p.locator('#modal')).not_to_be_visible();p.locator('#insights-screen').click();expect(rank).to_contain_text('New scored record');expect(rank.locator('.rating-number').first).to_have_text('5.0/5')
  print('PASS real score edit to 0.0, deletion removes year option, new score creation refreshes ranking',flush=True)
  p.locator('#import-json').set_input_files(dict(name='synthetic.json',mimeType='application/json',buffer=json.dumps(SEED).encode()));expect(rank.locator('select option[value="2020"]')).to_have_count(1)
  # Corrupt values safely recover. Unknown and duplicate IDs reconcile without duplicates.
  for raw in ['bad','null','{}','{"version":1,"items":[{"id":"time","visible":"bad"}]}']:
   p.evaluate('v=>localStorage.setItem("mla-insights-layout-v1:listening",v)',raw);p.reload();p.evaluate('MLAReady');p.locator('#insights-screen').click();assert order(root)==['artists','score','genre','tags','label','time','release']
  raw=dict(version=1,items=[dict(id='score',visible=True),dict(id='retired',visible=False),dict(id='score',visible=False),dict(id='artists',visible=False)])
  p.evaluate('v=>localStorage.setItem("mla-insights-layout-v1:listening",JSON.stringify(v))',raw);p.reload();p.evaluate('MLAReady');p.locator('#insights-screen').click();assert order(root)==['score','genre','tags','label','time','release'];assert root.locator('.insight-metrics').count()==1
  # Only score visible near page end: content shrink still retains the heading.
  p.evaluate('''()=>{localStorage.setItem('mla-insights-layout-v1:listening',JSON.stringify({version:1,items:MLAInsights.sectionIds('listening').map(id=>({id,visible:id==='score'}))}))}''');p.reload();p.evaluate('MLAReady');p.locator('#insights-screen').click();rank=root.locator('[data-insight=score]');rank.evaluate('(e)=>scrollTo(0,e.getBoundingClientRect().top+scrollY-30)');y=rank.locator('h3').bounding_box()['y'];rank.locator('select').select_option('2020');assert abs(rank.locator('h3').bounding_box()['y']-y)<3
  print('PASS corrupt/missing settings; retired/duplicate IDs; appended new items; single visible score shrink retains scroll position',flush=True)
  browser.close()
  # Close the entire Chromium process and reopen the same actual user-data directory.
  with tempfile.TemporaryDirectory() as profile:
   for run in [1,2]:
    ctx=pw.chromium.launch_persistent_context(profile,executable_path='/usr/bin/chromium',args=['--no-sandbox'],viewport=dict(width=390,height=844));ctx.route('https://**/*',lambda r:r.abort());page=ctx.pages[0];ready(page)
    if run==1:
     d=dialog(page);d.locator('button[data-item=score][data-direction="-1"]').click();d.locator('input[data-item=genre]').uncheck();d.get_by_role('button',name='Done',exact=True).click()
    else:assert order(page.locator('#listening-insights'))[0]=='score';assert 'genre' not in order(page.locator('#listening-insights'))
    ctx.close()
  print('PASS real Chromium process restart preserves order/visibility',flush=True)
  # Compare actual previous renderer with this change using synthetic records.
  old=subprocess.check_output(['git','show','cbcc61c:insights.js'],cwd=ROOT).decode();results=[]
  for phase in ['previous','current']:
   browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox']);ctx=browser.new_context(viewport=dict(width=390,height=844));ctx.route('https://**/*',lambda r:r.abort())
   if phase=='previous':ctx.route('**/insights.js*',lambda r:r.fulfill(body=old,content_type='application/javascript'))
   page=ctx.new_page();ready(page);page.on('dialog',lambda d:d.accept());page.locator('#import-json').set_input_files(dict(name='synthetic.json',mimeType='application/json',buffer=json.dumps(SEED).encode()));rank=page.locator('[data-insight=score]');expect(rank.locator('li')).to_have_count(15);rank.evaluate('(e)=>scrollTo(0,e.getBoundingClientRect().top+scrollY-60)');before=rank.locator('h3').bounding_box()['y'];page.evaluate('window.previousHeading=document.querySelector("[data-insight=score] h3");window.previousArtist=document.querySelector("[data-insight=artists]")');rank.locator('select').select_option('2020');after=rank.locator('h3').bounding_box()['y'];results.append(dict(phase=phase,headerBefore=before,headerAfter=after,headingRetained=page.evaluate('previousHeading===document.querySelector("[data-insight=score] h3")'),artistRetained=page.evaluate('previousArtist===document.querySelector("[data-insight=artists]")')));browser.close()
  assert results[0]['headingRetained']==False;assert results[1]['headingRetained'];assert abs(results[1]['headerBefore']-results[1]['headerAfter'])<3
  (E/'scroll-comparison.json').write_text(json.dumps(results,indent=2));print('PASS measured prior/current renderer DOM/scroll comparison',results,flush=True)
 server.shutdown()
if __name__=='__main__':main()
