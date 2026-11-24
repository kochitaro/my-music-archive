"""Isolated synthetic Live input, compatibility and failure tests on both engines."""
import copy, json, os, threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler

EVIDENCE=ROOT/'docs/live-input-support'; EVIDENCE.mkdir(exist_ok=True)
PHOTO='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='
SEED=dict(version=3,listening=[dict(entryId='album',title='Album',artist='Artist')],collection=[dict(entryId='purchase',title='Purchase',artist='Artist')],live=[dict(entryId='legacy',title='Legacy',date='2020',venue='Hall',rating='8.2',memo='original',photo=PHOTO),dict(entryId='one',title='One',artists=['Alpha','Beta'],tags=['Shared','Tour'],date='2024',venue='Hall'),dict(entryId='two',title='Two',artists=['Alpha','Gamma','Delta','Epsilon','Zeta','Eta'],tags=['Shared'],date='2025',venue='Park')])

def main():
 os.chdir(ROOT)
 server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
 seam="window.liveTest={db:()=>structuredClone(db),fail:()=>{commitDB=async()=>{throw Error('synthetic failure')}},originalCommit:commitDB,retry:()=>{commitDB=liveTest.originalCommit},state:formState,busy:()=>operationBusy};"
 html=(ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();",seam+"setSection('listening');showStorageState();")
 with sync_playwright() as pw:
  for engine in os.environ.get('MLA_ENGINES','chromium,webkit').split(','):
   browser=getattr(pw,engine).launch(**({'executable_path':'/usr/bin/chromium','args':['--no-sandbox']} if engine=='chromium' else {}))
   for lang in ['ja','en']:
    ctx=browser.new_context(viewport=dict(width=390,height=844),is_mobile=True,has_touch=True,accept_downloads=True)
    ctx.route('https://**/*',lambda r:r.abort());ctx.route(base+'/',lambda r:r.fulfill(body=html,content_type='text/html'))
    page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
    ctx.add_init_script('if(!localStorage.getItem('+json.dumps(KEY)+'))localStorage.setItem('+json.dumps(KEY)+','+json.dumps(json.dumps(SEED))+');localStorage.setItem("mma-ui-language",'+json.dumps(lang)+')')
    page.goto(base);page.evaluate('MLAReady')
    def db(): return page.evaluate('liveTest.db()')
    def shot(name):page.screenshot(path=str(EVIDENCE/f'{engine}-{lang}-{name}.png'))
    def select(id,value):
     if page.locator('#filters-wrap').is_hidden():page.locator('#filters-toggle').click()
     page.locator('#'+id+'-filter').select_option(value)
    def create():page.locator('#add-live-trigger').click()
    def close_discard():page.locator('#close-live-create').click();page.locator('#live-discard-accept').click()
    def edit(id):page.locator('#library .live-tile').filter(has_text={'legacy':'Legacy','one':'One','two':'Two'}[id]).click();page.locator('#view-edit').click()
    page.locator('[data-section=live]').click();assert db()==SEED,(db(),SEED)
    create();page.locator('#close-live-create').click();expect(page.locator('#live-discard-modal')).not_to_be_visible()
    for control in ['date','rating','row']:
     create()
     if control=='date':page.locator('#live-date-parts input').fill('2025')
     elif control=='rating':page.locator('[data-target=live-rating] .star-rating').press('ArrowRight')
     else:page.locator('#live-artists > button').click()
     page.locator('#close-live-create').click();expect(page.locator('#live-discard-modal')).to_be_visible();page.locator('#live-discard-cancel').press('Escape');expect(page.locator('#live-create-modal')).to_be_visible();close_discard()
    create();inp=page.locator('#live-artists input').first;inp.fill('a');area=page.locator('#live-artists .suggest-box').first
    expect(area.locator('.suggest-item')).to_have_count(5);assert area.locator('.suggest-item').first.inner_text()=='Alpha'
    inp.fill('Al');expect(area.locator('.suggest-item')).to_have_text(['Alpha']);area.locator('button.suggest-item').tap();assert inp.input_value()=='Alpha';expect(area).not_to_be_visible();expect(page.locator('#live-artists input')).to_have_count(1)
    inp.fill('Alpha');expect(area).not_to_be_visible();inp.fill('New artist');expect(area).not_to_be_visible()
    page.locator('#live-artists > button').click();expect(page.locator('#live-artists input')).to_have_count(2);second=page.locator('#live-artists input').nth(1);second.fill('Be');expect(page.locator('#live-artists .suggest-box').nth(1).locator('.suggest-item')).to_have_text(['Beta'])
    second.dispatch_event('compositionstart');second.fill('B');page.locator('#live-artists .suggest-box').nth(1).locator('.suggest-item').evaluate('(e)=>e.click()');assert second.input_value()=='B';second.dispatch_event('compositionend');page.locator('#live-artists .suggest-box').nth(1).locator('.suggest-item').tap();assert second.input_value()=='Beta';expect(page.locator('#live-artists input')).to_have_count(2)
    page.locator('#live-artists > button').click();page.locator('#live-artists input').nth(2).fill('Remove me');page.locator('#live-artists .artist-remove').nth(2).click();expect(page.locator('#live-artists input')).to_have_count(2)
    page.locator('#live-title').fill('Created');page.locator('#live-tags').fill(' Shared， New, shared ,, ');page.locator('#live-notes').fill('notes');page.locator('#live-photo').set_input_files(dict(name='test.png',mimeType='image/png',buffer=__import__('base64').b64decode(PHOTO.split(',')[1])))
    page.locator('#live-artists input').first.fill('Al');shot('create');page.locator('#live-title').focus();expect(area).not_to_be_visible()
    state=page.evaluate('liveTest.state().input');page.locator('#close-live-create').click();shot('discard');expect(page.locator('#live-discard-title')).to_have_text('入力内容を破棄しますか？' if lang=='ja' else 'Discard your changes?');page.locator('#live-discard-cancel').click();assert page.evaluate('liveTest.state().input')==state;assert page.locator('#live-photo').evaluate('(e)=>e.files.length')==1
    # Backdrop uses the same exit guard.
    page.locator('#live-create-modal').click(position=dict(x=2,y=2));expect(page.locator('#live-discard-modal')).to_be_visible();page.locator('#live-discard-cancel').click()
    # Persist and reload keeps tags, artists and photo; no discard prompt on save.
    page.locator('#live-form > button').click();expect(page.locator('#live-create-modal')).not_to_be_visible();expect(page.locator('#live-discard-modal')).not_to_be_visible();assert db()['live'][0]['tags']==['Shared','New'];assert db()['live'][0]['photo'];assert db()['live'][1:]==SEED['live'];page.reload();page.evaluate('MLAReady');assert db()['live'][0]['tags']==['Shared','New']
    page.locator('[data-section=live]').click();create();expect(page.locator('#live-tags-suggest .suggest-item')).to_contain_text(['Shared']);page.locator('#live-tags').fill('only dirty');close_discard();create();assert page.locator('#live-tags').input_value()=='';assert page.locator('#live-artists input').count()==1;assert not page.locator('#live-title').input_value();assert page.locator('#live-photo').evaluate('(e)=>e.files.length')==0;page.locator('#close-live-create').click()
    # Edit old record without adding a missing tags property or changing other bytes.
    edit('legacy');page.locator('#save').click();expect(page.locator('#modal')).not_to_be_visible();assert next(x for x in db()['live'] if x['entryId']=='legacy')==SEED['live'][0]
    edit('legacy');page.locator('#e-live-tags').fill(' Shared, Later，shared ');page.locator('#e-live-artists input').fill('Al');shot('edit');page.locator('#e-live-artists .suggest-item').tap();page.locator('#save').click();expect(page.locator('#modal')).not_to_be_visible();r=next(x for x in db()['live'] if x['entryId']=='legacy');assert r['tags']==['Shared','Later'];assert {k:r[k] for k in SEED['live'][0]}==SEED['live'][0]
    edit('legacy');page.locator('#e-live-tags').fill('');page.locator('#save').click();expect(page.locator('#modal')).not_to_be_visible();assert next(x for x in db()['live'] if x['entryId']=='legacy')['tags']==[]
    # Shared tag AND artist/year/venue; toolbar count and area-state restore.
    page.locator('#filters-toggle').click();select('tag','Shared');expect(page.locator('#library .live-tile')).to_have_count(3);shot('filter');assert 'active' in page.locator('#filters-toggle').get_attribute('aria-label') or '適用中' in page.locator('#filters-toggle').get_attribute('aria-label');select('artist','Alpha');expect(page.locator('#library .live-tile')).to_have_count(2);select('year','2024');select('venue','Hall');expect(page.locator('#library .live-tile')).to_have_count(1)
    page.locator('[data-section=listening]').click();page.locator('[data-section=live]').click();assert page.locator('#tag-filter').input_value()=='Shared'
    for id in ['tag','artist','year','venue']:select(id,'')
    expect(page.locator('#library .live-tile')).to_have_count(4)
    # Real JSON export / restore exercises photos and optional tags.
    before=db()
    with page.expect_download() as download:page.locator('#export-json').click()
    exported=json.loads(Path(download.value.path()).read_text());data=exported.get('data',exported);assert data['live']==before['live']
    page.locator('#import-json').set_input_files(dict(name='roundtrip.json',mimeType='application/json',buffer=json.dumps(exported).encode()));page.wait_for_function('!liveTest.busy()');expect(page.locator('#storage-state')).not_to_be_visible();assert db()==before
    page.locator('#import-json').set_input_files(dict(name='old.json',mimeType='application/json',buffer=json.dumps(SEED).encode()));page.wait_for_function('!liveTest.busy()');assert db()==SEED
    # Save failure preserves input, File and dynamic rows; retry succeeds.
    create();page.locator('#live-title').fill('Failure');page.locator('#live-tags').fill('Retain');page.locator('#live-artists > button').click();page.locator('#live-artists input').nth(1).fill('Keep');page.evaluate('liveTest.fail()');page.locator('#live-form > button').click();expect(page.locator('#save-notice')).to_be_visible();assert db()==SEED;assert page.locator('#live-tags').input_value()=='Retain';page.locator('#close-live-create').click();expect(page.locator('#live-create-modal')).to_be_visible();expect(page.locator('#live-discard-modal')).not_to_be_visible();page.locator('#save-return').click();page.evaluate('liveTest.retry()');page.locator('#live-form > button').click();expect(page.locator('#live-create-modal')).not_to_be_visible()
    # Existing Listening/Collection CRUD, suggestions and tags remain usable.
    for area in ['listening','collection']:
     page.locator(f'[data-section={area}]').click();page.locator('#manual-add-trigger').click();page.locator('#manual-artist').fill('Regression');page.locator('#manual-title').fill('CRUD '+area);page.locator('#tags').fill(' Common， common, Other ');page.locator('#save').click();expect(page.locator('#modal')).not_to_be_visible();assert db()[area][0]['tags']==['Common','Other']
     page.locator('#library button').filter(has_text='CRUD '+area).click();page.locator('#view-edit').click();page.locator('#memo').fill('edited');page.locator('#tags').fill('Co');expect(page.locator('#tags-suggest .suggest-item')).to_have_text(['Common']);page.locator('#tags-suggest .suggest-item').click();page.locator('#save').click();expect(page.locator('#modal')).not_to_be_visible();assert db()[area][0]['memo']=='edited'
     page.locator('#library button').filter(has_text='CRUD '+area).click();page.locator('#view-edit').click();page.locator('#delete').click();page.locator('#delete-accept').click();expect(page.locator('#modal')).not_to_be_visible();assert len(db()[area])==1
    assert not errors,errors
    print(f'PASS {engine} {lang}: suggestions, IME guards, tags, compound filters, close paths, JSON/photos, failure/retry',flush=True);ctx.close()
   browser.close()
 server.shutdown()
if __name__=='__main__':main()
