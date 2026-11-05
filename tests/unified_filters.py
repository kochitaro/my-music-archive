"""Archive-wide counted selects: synthetic data, mobile bilingual evidence, no DB writes."""
import copy, json, os, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, stored, choose, titles, unset_value, open_filters, options, edit, save


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    rows=[album('A',genre='Ambient，AMBIENT, Drone',tags=['Night','night'],label='Label',store='Shop'),
          {**album('B',genre='ambient',tags='Night',label='label',store='shop'), 'artist':'artist a','date':'2025','release':'2024-02'},
          {**album('Empty'), 'artist':' ', 'date':'', 'release':'202'},
          {**album('Partial'), 'artist':'__mma_unset__','date':'2026-02','release':'2026'},
          {**album('Unknown'), 'date':'March 2020','release':''}]
    seed=dict(version=3,listening=rows,collection=copy.deepcopy(rows),live=[
        dict(entryId='L1',title='Festival',artists=['Artist A','artist a',' Artist B '],date='2026-02',venue='WWW',label='Keep',tags=['Keep']),
        dict(entryId='L2',title='Other',artists=['artist a'],date='2025',venue='www'),
        dict(entryId='L3',title='Old Artist Title',date='',venue=''),
        dict(entryId='L4',title='Empty array',artists=[],date='March 2020',venue=' '),
        dict(entryId='L5',title='Blank array',artists=[' '],date='2026',venue='__mma_unset__')])
    evidence=ROOT/'docs/unified-filters-evidence';evidence.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        for lang in ['ja','en']:
            ctx=browser.new_context(viewport=dict(width=390,height=844),is_mobile=True,has_touch=True)
            ctx.route('https://**/*',lambda r:r.abort())
            page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.evaluate('([k,v,l])=>{localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",l)}',[KEY,seed,lang]);page.reload()
            raw=page.evaluate('(k)=>localStorage.getItem(k)',KEY)
            def tab(area):
                page.locator(f'[data-section={area}]').click();open_filters(page)
            for area in ['listening','collection','live']:
                tab(area)
                active=['artist','year','venue'] if area=='live' else ['artist','genre','label','tag','year','release-year']+(['store'] if area=='collection' else [])
                assert page.locator('#filters-wrap select:visible').count()==len(active)
                for field in ['artist','genre','label','tag','year','release-year','store','venue']:
                    control=page.locator('#'+field+'-filter')
                    assert control.is_enabled()==(field in active)
                    if field not in active:assert control.is_hidden()
                for field in active:
                    opts=options(page,field);assert opts[''].endswith(' (2)' if area=='live' and field=='artist' else ' (5)'),(area,field,opts)
                    assert all(v.endswith(')') for v in opts.values())
                    expected_unset={'artist':3 if area=='live' else 1,'year':2,'venue':2,'genre':3,'label':3,'tag':3,'store':3,'release-year':2}[field]
                    assert opts[unset_value(page,field)].endswith(f' ({expected_unset})')
                    assert page.locator('#'+field+'-filter').evaluate('(e)=>e.tagName')=='SELECT'
                assert options(page,'artist')['Artist A']==('Artist A (2)' if area=='live' else 'Artist A (3)')
                assert options(page,'year')['2026']=='2026 (2)'
                assert page.locator('#year-filter option:not([data-unset])').evaluate_all('(els)=>els.map(e=>e.value)')==['','2026','2025']
                if area=='live':
                    assert 'Old Artist Title' not in options(page,'artist')
                    assert options(page,'artist')['Artist B']=='Artist B (1)'
                    assert options(page,'venue')['WWW']=='WWW (2)'
                    choose(page,'artist',unset_value(page,'artist'));assert set(titles(page))=={'Old Artist Title','Empty array','Blank array'}
                    choose(page,'artist','Artist A');choose(page,'year','2026');choose(page,'venue','WWW');assert titles(page)==['Festival']
                    assert options(page,'artist')['Artist A']=='Artist A (2)'
                    page.screenshot(path=str(evidence/f'{area}-and-{lang}.png'),full_page=True)
                    for f in ['artist','year','venue']:choose(page,f,'')
                else:
                    for f,v in [('genre','Ambient (2)'),('tag','Night (2)'),('label','Label (2)')]:assert v in options(page,f).values()
                    if area=='collection':assert options(page,'store')['Shop']=='Shop (2)'
                    choose(page,'artist',unset_value(page,'artist'));assert titles(page)==['Empty']
                    choose(page,'artist','Artist A');choose(page,'genre','Ambient');choose(page,'year','2025');choose(page,'release-year','2024');assert titles(page)==['B']
                    assert options(page,'artist')['Artist A']=='Artist A (3)'
                    page.screenshot(path=str(evidence/f'{area}-and-{lang}.png'),full_page=True)
                    for f in active:choose(page,f,'')
                choose(page,'year',unset_value(page,'year'));assert set(titles(page))==({'Old Artist Title','Empty array'} if area=='live' else {'Empty','Unknown'})
                choose(page,'year','')
                (evidence/f'{area}-options-{lang}.json').write_text(json.dumps({f:options(page,f) for f in active},ensure_ascii=False,indent=2)+'\n')
                for width in [320,375,390,430]:
                    page.set_viewport_size(dict(width=width,height=844))
                    for field in active:
                        box=page.locator('#'+field+'-filter').bounding_box();assert box['x']>=0 and box['x']+box['width']<=width
                page.set_viewport_size(dict(width=390,height=844));page.screenshot(path=str(evidence/f'{area}-{lang}.png'),full_page=True)
            # Independent real and unset selections, including every new control.
            for mode in ['normal','unset']:
                for area in ['listening','collection','live']:
                    tab(area)
                    for f in (['artist','year','venue'] if area=='live' else ['artist','year','release-year']):
                        choose(page,f,unset_value(page,f) if mode=='unset' else ('WWW' if f=='venue' else 'Artist A' if f=='artist' else '2026' if f=='year' else '2025'))
                for area in ['live','collection','listening','live']:
                    tab(area)
                    for f in (['artist','year','venue'] if area=='live' else ['artist','year','release-year']):
                        if mode=='unset':expect(page.locator('#'+f+'-filter option:checked')).to_have_attribute('data-unset','true')
                        else:assert page.locator('#'+f+'-filter').input_value()==('WWW' if f=='venue' else 'Artist A' if f=='artist' else '2026' if f=='year' else '2025'),(area,f,page.locator('#'+f+'-filter').input_value())
            assert page.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw and stored(page)==seed
            # Restore changes all candidates and counts through the actual JSON handler.
            restored=copy.deepcopy(seed);restored['live'].append(dict(entryId='new',title='Restored',artists=['New'],date='2030',venue='New venue'))
            page.locator('#import-json').set_input_files(dict(name='restore.json',mimeType='application/json',buffer=json.dumps(restored).encode()))
            page.wait_for_function('(k)=>JSON.parse(localStorage.getItem(k)).live.length===6',arg=KEY)
            tab('live');assert options(page,'year')['2030']=='2030 (1)' and options(page,'venue')['New venue']=='New venue (1)'
            for f in ['artist','year','venue']:choose(page,f,'')
            # Live create/edit/delete refreshes each of the three counts.
            page.locator('#add-live-trigger').click();page.locator('#live-title').fill('Created');page.locator('#live-artists input').fill('New');page.locator('#live-venue').fill('New venue');page.locator('#live-form > button').click()
            expect(page.locator('#live-create-modal')).not_to_have_class('modal open')
            assert options(page,'artist')['New']=='New (2)' and options(page,'venue')['New venue']=='New venue (2)'
            edit(page,'Created');page.locator('#e-live-artists input').fill('Edited');page.locator('#e-live-venue').fill('Edited venue');page.locator('#e-live-date-parts input').fill('2031');page.locator('#memo').click();save(page)
            assert options(page,'year')['2031']=='2031 (1)'
            assert options(page,'artist')['New']=='New (1)' and options(page,'venue')['Edited venue']=='Edited venue (1)'
            edit(page,'Created');page.locator('#delete').click();page.locator('#delete-accept').click();expect(page.locator('#modal')).not_to_have_class('modal open')
            assert 'Edited' not in options(page,'artist') and '2031' not in options(page,'year') and stored(page)==restored
            assert not errors,errors
            print('PASS',lang,'all counted selects; deduplication; year precision/order/unset; archive-wide AND; legacy Live; tab isolation; widths; unchanged DB; restore; Live CRUD',flush=True)
            ctx.close()
        browser.close()
    server.shutdown()

if __name__=='__main__':main()
