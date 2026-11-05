"""Only Live's all-artists label counts distinct saved performers. Public UI, synthetic data."""
import copy, json, os, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, stored, options, unset_value, choose, open_filters, titles, edit, save


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    seed=dict(version=3,listening=[album('L1'),album('L2')],collection=[album('C1'),album('C2')],live=[
        dict(entryId='one',title='One',artists=['Artist A','B','C','D','E',' artist a ',''],date='2026',venue='WWW'),
        dict(entryId='two',title='Two',artists=['artist a',' F ','G','H','f',' '],date='2025',venue='WWW'),
        dict(entryId='old',title='Old title is not a performer',date='',venue='')])
    evidence=ROOT/'docs/live-artist-total-evidence';evidence.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        for lang in ['ja','en']:
            ctx=browser.new_context(viewport=dict(width=390,height=844),is_mobile=True,has_touch=True)
            ctx.route('https://**/*',lambda r:r.abort())
            page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.evaluate('([k,v,l])=>{localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",l)}',[KEY,seed,lang]);page.reload()
            raw=page.evaluate('(k)=>localStorage.getItem(k)',KEY)
            for area in ['listening','collection']:
                page.locator(f'[data-section={area}]').click();open_filters(page)
                for control in page.locator('#filters-wrap select:enabled').all():
                    assert control.locator('option[value=""]').inner_text().endswith(' (2)')
                assert options(page,'artist')['Artist A']=='Artist A (2)'
            page.locator('[data-section=live]').click();open_filters(page)
            prefix='すべての出演アーティスト' if lang=='ja' else 'All Performing Artists'
            def total(n):assert options(page,'artist')['']==f'{prefix} ({n})'
            total(8);assert options(page,'artist')['Artist A']=='Artist A (2)'
            assert page.locator('#count').inner_text()=='(3)'
            assert options(page,'year')[''].endswith(' (3)') and options(page,'venue')[''].endswith(' (3)')
            assert options(page,'artist')[unset_value(page,'artist')].endswith(' (1)')
            assert 'Old title is not a performer' not in options(page,'artist')
            assert set(titles(page))=={r['title'] for r in seed['live']}
            page.screenshot(path=str(evidence/f'all-{lang}.png'),full_page=True)
            choose(page,'artist','Artist A');total(8);assert set(titles(page))=={'One','Two'}
            choose(page,'artist',unset_value(page,'artist'));total(8);assert titles(page)==['Old title is not a performer']
            choose(page,'artist','');assert len(titles(page))==3
            page.locator('#ui-language').select_option('en' if lang=='ja' else 'ja')
            assert options(page,'artist')['']==('All Performing Artists (8)' if lang=='ja' else 'すべての出演アーティスト (8)')
            page.locator('#ui-language').select_option(lang)
            assert stored(page)==seed and page.evaluate('(k)=>localStorage.getItem(k)',KEY)==raw
            # Real registration, edit and deletion. A retained (0) selection must not count as a saved artist.
            page.locator('#add-live-trigger').click();page.locator('#live-title').fill('Created');page.locator('#live-artists input').fill('New');page.locator('#live-form > button').click()
            expect(page.locator('#live-create-modal')).not_to_have_class('modal open');total(9)
            choose(page,'artist','New');edit(page,'Created');page.locator('#e-live-artists input').fill('Edited');save(page)
            total(9);assert options(page,'artist')['New']=='New (0)'
            choose(page,'artist','Edited');edit(page,'Created');page.locator('#delete').click();page.locator('#delete-accept').click()
            expect(page.locator('#modal')).not_to_have_class('modal open');total(8)
            assert options(page,'artist')['Edited']=='Edited (0)' and stored(page)==seed
            choose(page,'artist','')
            # JSON restore with missing, empty and blank arrays; no inference from title.
            restored=copy.deepcopy(seed)
            restored['live'] += [dict(entryId='empty',title='Empty',artists=[]),dict(entryId='blank',title='Blank',artists=['','  ']),dict(entryId='new',title='Restored',artists=['I',' i ','A different artist'])]
            def restore(value):
                page.locator('#import-json').set_input_files(dict(name='restore.json',mimeType='application/json',buffer=json.dumps(value).encode()))
                page.wait_for_function('([k,v])=>JSON.stringify(JSON.parse(localStorage.getItem(k)))===JSON.stringify(v)',arg=[KEY,value])
            restore(restored);total(10);assert len(titles(page))==6
            assert options(page,'artist')[unset_value(page,'artist')].endswith(' (3)')
            assert options(page,'year')[''].endswith(' (6)') and options(page,'venue')[''].endswith(' (6)')
            empty=dict(version=3,listening=[],collection=[],live=[dict(entryId='none',title='No performers',artists=[])])
            restore(empty);total(0);assert titles(page)==['No performers']
            assert not errors,errors
            print('PASS',lang,'8 distinct / 3 shows; case+space+duplicate handling; per-show counts; unset/all inclusion; other archive totals; language switch; unchanged DB; CRUD; retained zero-count option; JSON restore; zero artists',flush=True)
            ctx.close()
        browser.close()
    server.shutdown()

if __name__=='__main__':main()
