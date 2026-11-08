"""Multi-label and venue history: real UI, isolated synthetic storage, no external calls."""
import copy, csv, io, json, os, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, stored, edit, save, choose, titles, unset_value

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    evidence=ROOT/'docs/multi-label-venue-evidence';evidence.mkdir(exist_ok=True)
    seed=dict(version=3,listening=[],collection=[],live=[])
    for area in ['listening','collection']:
        seed[area]=[album('Multi',label=' 4AD， Warp Records, 4ad, , '),
                    album('Single',label='4AD'),album('Empty'),album('Blank',label=' , ， '),
                    album('First',label='4AD, AAA'),album('Later',label='Warp Records, AAA')]
    for i,v in enumerate([' LIQUIDROOM ','liquidroom','Zepp','Alpha','Beta','Gamma','Delta','Epsilon',' ',None]):
        seed['live'].append(dict(entryId=str(i),title='Show '+str(i),venue=v,date='2026-01-01',memo='keep'))
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        for lang in ['ja','en']:
            ctx=browser.new_context(viewport=dict(width=390,height=844),is_mobile=True,has_touch=True)
            ctx.route('https://**/*',lambda r:r.abort())
            ctx.add_init_script("""window.failWrite=false;window.writes=0;const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03'){if(window.failWrite)throw Error('test quota');window.writes++}return set.call(this,k,v)}""")
            page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
            page.goto(f'http://127.0.0.1:{server.server_port}')
            def reset(data=seed):
                page.evaluate('([k,v,l])=>{failWrite=false;localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",l)}',[KEY,data,lang]);page.reload()
            reset();assert stored(page)==seed
            for area in ['listening','collection']:
                reset();page.locator(f'[data-section={area}]').click()
                assert '4AD (3)' in page.locator('#label-filter option').all_text_contents()
                choose(page,'label','4AD');assert set(titles(page))=={'Multi','Single','First'}
                choose(page,'label',unset_value(page,'label'));assert set(titles(page))=={'Empty','Blank'}
                choose(page,'label','');page.locator('#sort-toggle').click();page.locator('#sort').select_option('label-asc')
                assert titles(page)[:3]==['Multi','Single','First'],titles(page)
                page.locator('#list-tab').click()
                assert '4AD, Warp Records' in page.locator('#library').inner_text()
                # Opening, cancelling, and unrelated saves preserve raw label and missing property.
                for title in ['Multi','Single','Empty']:
                    before=copy.deepcopy(next(r for r in stored(page)[area] if r['title']==title))
                    edit(page,title);assert page.locator('#label').input_value()==(before.get('label') or '')
                    page.locator('#memo').fill('changed');save(page)
                    after=next(r for r in stored(page)[area] if r['title']==title)
                    assert ('label' in before)==('label' in after) and before.get('label')==after.get('label')
                edit(page,'Multi');raw=stored(page);writes=page.evaluate('writes')
                page.locator('#label').fill('New， wa')
                expect(page.locator('#label-suggest .suggest-item')).to_have_text(['Warp Records'])
                page.locator('#label-suggest .suggest-item').tap()
                assert page.locator('#label').input_value()=='New, Warp Records, '
                assert 'Warp Records' not in page.locator('#label-suggest .suggest-item').all_text_contents()
                assert stored(page)==raw and page.evaluate('writes')==writes
                for width in [320,375,390,430,1280]:
                    page.set_viewport_size(dict(width=width,height=844))
                    page.locator('label[for=label]').scroll_into_view_if_needed()
                    assert page.locator('#modal .dialog').evaluate('(n)=>n.scrollWidth<=n.clientWidth')
                    page.screenshot(path=str(evidence/f'labels-{area}-{lang}-{width}.png'))
                page.set_viewport_size(dict(width=390,height=844))
                page.locator('#label').fill(' 4AD，Warp Records, 4ad, , ')
                page.evaluate('failWrite=true');page.locator('#save').click()
                expect(page.locator('#modal')).to_have_class('modal open')
                assert stored(page)==raw and page.locator('#label').input_value()==' 4AD，Warp Records, 4ad, , '
                page.locator('#save-return').click();page.evaluate('failWrite=false')
                # Retry the ordinary save through existing recovery mechanism.
                page.locator('#save').click()
                expect(page.locator('#modal')).not_to_have_class('modal open')
                assert next(r for r in stored(page)[area] if r['title']=='Multi')['label']=='4AD, Warp Records'
                page.locator('#insights-screen').click()
                legend=page.locator(f'#{area}-insights [data-insight=label] .insight-legend').inner_text()
                assert '42.9%' in legend and '28.6%' in legend,legend
                page.locator('#archive-screen').click()
                # New manual records use the same normalizer.
                page.locator('#manual-add-trigger').click()
                page.locator('#manual-artist').fill('New artist');page.locator('#manual-title').fill('New album')
                page.locator('#label').fill(' A， b, a ,, B ');save(page)
                assert stored(page)[area][0]['label']=='A, b'
            reset();page.locator('[data-section=live]').click()
            page.locator('#add-live-trigger').click()
            expect(page.locator('#live-venue-suggest .suggest-item')).to_have_text(['LIQUIDROOM','Alpha','Beta','Delta','Epsilon'])
            raw=stored(page);writes=page.evaluate('writes')
            page.locator('#live-title').fill('New show');page.locator('#live-notes').fill('keep inputs')
            page.locator('#live-venue-suggest .suggest-more').tap()
            assert page.locator('#live-venue-suggest .suggest-item').count()==7
            page.locator('#live-venue').fill('liq')
            expect(page.locator('#live-venue-suggest .suggest-item')).to_have_text(['LIQUIDROOM'])
            # Synthetic IME events validate guards, not a physical Japanese keyboard.
            page.locator('#live-venue').dispatch_event('compositionstart')
            page.locator('#live-venue-suggest .suggest-item').evaluate('(b)=>b.click()')
            assert page.locator('#live-venue').input_value()=='liq'
            page.locator('#live-venue').dispatch_event('compositionend')
            assert page.locator('#live-venue-suggest .suggest-more').is_enabled()
            page.locator('#live-venue-suggest .suggest-item').tap()
            assert page.locator('#live-venue').input_value()=='LIQUIDROOM'
            assert page.locator('#live-notes').input_value()=='keep inputs'
            assert stored(page)==raw and page.evaluate('writes')==writes
            for width in [320,375,390,430,1280]:
                page.set_viewport_size(dict(width=width,height=844))
                page.locator('#live-venue').fill('')
                page.locator('#live-venue').scroll_into_view_if_needed()
                assert page.locator('#live-venue').evaluate('(n)=>parseFloat(getComputedStyle(n).fontSize)')>=16
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                assert page.locator('#live-create-modal .dialog').evaluate('(n)=>n.scrollWidth<=n.clientWidth')
                page.screenshot(path=str(evidence/f'create-{lang}-{width}.png'))
            page.locator('#live-venue').fill('Free venue')
            page.locator('#live-form button.btn').last.click()
            expect(page.locator('#live-create-modal')).not_to_have_class('modal open')
            assert stored(page)['live'][0]['venue']=='Free venue'
            edit(page,'Show 0')
            assert page.locator('#e-live-venue').input_value()==' LIQUIDROOM '
            page.locator('#e-live-venue').fill('zep');page.locator('#e-live-venue-suggest .suggest-item').tap()
            assert page.locator('#e-live-venue').input_value()=='Zepp'
            for width in [320,375,390,430,1280]:
                page.set_viewport_size(dict(width=width,height=844))
                page.locator('label[for=e-live-venue]').scroll_into_view_if_needed()
                assert page.locator('#modal .dialog').evaluate('(n)=>n.scrollWidth<=n.clientWidth')
                page.screenshot(path=str(evidence/f'edit-{lang}-{width}.png'))
            before=stored(page);page.locator('#close').click();assert stored(page)==before
            edit(page,'Show 0');page.locator('#e-live-venue').fill('New venue')
            page.evaluate('failWrite=true');page.locator('#save').click()
            assert stored(page)==before and page.locator('#e-live-venue').input_value()=='New venue'
            page.locator('#save-return').click();page.evaluate('failWrite=false');page.locator('#save').click()
            expect(page.locator('#modal')).not_to_have_class('modal open')
            assert next(r for r in stored(page)['live'] if r['entryId']=='0')['venue']=='New venue'
            # Real downloads and import exercise existing compatibility paths.
            reset()
            with page.expect_download() as dl:page.locator('#export-json').click()
            backup=json.loads(open(dl.value.path()).read());assert backup==seed
            with page.expect_download() as dl:page.locator('#export-csv').click()
            rows=list(csv.DictReader(io.StringIO(open(dl.value.path(),encoding='utf-8-sig').read())))
            assert rows[0]['label']==seed['listening'][0]['label']
            page.locator('#import-json').set_input_files(dict(name='backup.json',mimeType='application/json',buffer=json.dumps(backup).encode()))
            page.wait_for_timeout(150);assert stored(page)==seed
            empty=dict(version=3,listening=[],collection=[],live=[])
            reset(empty);page.locator('[data-section=live]').click();page.locator('#add-live-trigger').click()
            assert page.locator('#live-venue-suggest .suggest-item').count()==0
            page.locator('#live-title').fill('Zero history');page.locator('#live-venue').fill('First venue')
            page.locator('#live-form button.btn').last.click()
            expect(page.locator('#live-create-modal')).not_to_have_class('modal open')
            assert stored(page)['live'][0]['venue']=='First venue'
            assert not errors,errors
            ctx.close()
        browser.close()
    server.shutdown();print('PASS multi-label/venue UI, preservation, exports, restore, IME guards, ja/en, 5 widths')
if __name__=='__main__':main()
