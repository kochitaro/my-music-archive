"""Independent classifications: synthetic data, actual forms/filters/JSON, mobile evidence."""
import copy, json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, album, stored, edit, save, choose, titles, unset_value


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    evidence=ROOT/'docs/genres-tags-evidence';evidence.mkdir(exist_ok=True)
    seed=dict(version=3,listening=[],collection=[],live=[dict(entryId='live',title='Live',memo='intact')])
    for area in ['listening','collection']:
        seed[area]=[album('Legacy tags',tags=' Ambient, Drone, Experimental, Ambient '),
                    album('Legacy genre',genre=' Ambient，Drone, AMBIENT ',tags=[' Japan ', 'Night','Night']),
                    album('Genre only',genre='Drone'),album('Empty'),
                    album('Same',genre='Shared',tags=['Shared']),album('Lower',genre='drone',tags=['japan'])]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        for lang in ['ja','en']:
            ctx=browser.new_context(viewport=dict(width=390,height=844),is_mobile=True,has_touch=True,locale='ja-JP')
            ctx.route('https://**/*',lambda r:r.abort())
            page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('dialog',lambda d:d.accept())
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.evaluate('([k,v,l])=>{localStorage.setItem(k,JSON.stringify(v));localStorage.setItem("mma-ui-language",l)}',[KEY,seed,lang]);page.reload()
            assert stored(page)==seed
            for area in ['listening','collection']:
                page.evaluate('([k,v])=>localStorage.setItem(k,JSON.stringify(v))',[KEY,seed]);page.reload()
                page.locator(f'[data-section={area}]').click()
                # All suggestion/filter counts come from their own field, case-insensitive.
                choose(page,'genre','');choose(page,'tag','')
                genres=page.locator('#genre-filter option').all_text_contents();tags=page.locator('#tag-filter option').all_text_contents()
                assert 'Ambient (1)' in genres and 'Drone (3)' in genres,genres
                assert not any('Japan' in x for x in genres)
                assert not any('Drone (3)'==x for x in tags)
                choose(page,'genre',unset_value(page,'genre'));assert set(titles(page))=={'Legacy tags','Empty'}
                choose(page,'genre','');choose(page,'tag',unset_value(page,'tag'));assert set(titles(page))=={'Genre only','Empty'}
                choose(page,'tag','');choose(page,'genre','Drone');assert set(titles(page))=={'Legacy genre','Genre only','Lower'}
                choose(page,'genre','');choose(page,'tag','Japan');assert set(titles(page))=={'Legacy genre','Lower'}
                choose(page,'tag','')
                # Opening and unrelated editing never normalizes existing raw classification values.
                before=copy.deepcopy(stored(page))
                for title in ['Legacy tags','Legacy genre','Genre only','Empty']:
                    edit(page,title)
                    old=next(r for r in before[area] if r['title']==title)
                    if title=='Legacy tags':assert page.locator('#genre').input_value()==''
                    page.locator('#memo').fill('unrelated edit');save(page)
                    after=next(r for r in stored(page)[area] if r['title']==title)
                    for field in ['genre','tags']:
                        assert (field in after)==(field in old) and after.get(field)==old.get(field),(field,after,old)
                edit(page,'Legacy tags');original_tags=stored(page)[area][0]['tags']
                assert page.locator('label[for=genre]').inner_text()==('ジャンル（任意・複数）' if lang=='ja' else 'Genres (optional · comma-separated)')
                assert page.locator('label[for=tags]').inner_text()==('タグ（任意・複数）' if lang=='ja' else 'Tags (optional · comma-separated)')
                assert page.locator('#tags').get_attribute('placeholder')==('国、気分、シーンなど' if lang=='ja' else 'Country, mood, occasion, etc.')
                assert page.locator('#genre-suggest .suggest-item').all_text_contents()==['Drone','Ambient','Shared']
                page.locator('#tags').fill('')
                assert 'Japan' in page.locator('#tags-suggest .suggest-item').all_text_contents()
                page.locator('#genre').scroll_into_view_if_needed()
                page.screenshot(path=str(evidence/f'{area}-suggestions-{lang}.png'))
                page.locator('#tags').fill('Free tag, ja')
                page.locator('#tags-suggest .suggest-item').get_by_text('Japan',exact=True).click()
                assert page.locator('#tags').input_value()=='Free tag, Japan, '
                assert page.locator('#genre').input_value()==''
                page.locator('#tags').fill('Ambient, Drone, Experimental, Ambient')
                assert not any(x=='Japan' for x in page.locator('#genre-suggest .suggest-item').all_text_contents())
                # Multiple input, suggestions, case duplicates and cross-field isolation.
                page.locator('#genre').fill('Free, dr')
                page.locator('#genre-suggest .suggest-item').get_by_text('Drone',exact=True).click()
                assert page.locator('#genre').input_value()=='Free, Drone, '
                assert page.locator('#tags').input_value()=='Ambient, Drone, Experimental, Ambient'
                page.locator('#genre').fill('Ambient, ambient，Drone, 新しいジャンル')
                # Composition updates do not rerender suggestions or swallow IME keys.
                page.locator('#genre').dispatch_event('compositionstart')
                snapshot=page.locator('#genre-suggest').inner_html()
                page.locator('#genre').dispatch_event('input',dict(isComposing=True))
                assert page.locator('#genre-suggest').inner_html()==snapshot
                page.locator('#genre').dispatch_event('compositionend')
                for width in [320,375,390,430]:
                    page.set_viewport_size(dict(width=width,height=844))
                    assert page.locator('#modal .dialog').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                    for field in ['genre','tags']:
                        assert page.locator('#'+field).bounding_box()['width']<width
                page.set_viewport_size(dict(width=390,height=844))
                page.locator('#genre').scroll_into_view_if_needed();page.screenshot(path=str(evidence/f'{area}-input-{lang}.png'))
                save(page)
                row=next(r for r in stored(page)[area] if r['title']=='Legacy tags')
                assert row['genre']=='Ambient, Drone, 新しいジャンル' and row['tags']==original_tags
                page.locator('#library button').filter(has=page.get_by_text('Legacy tags',exact=True)).click()
                table=page.locator('.detail-table').inner_text()
                assert ('ジャンル' if lang=='ja' else 'Genre') in table and ('タグ' if lang=='ja' else 'Tags') in table
                assert 'Ambient, Drone, 新しいジャンル' in table and 'Ambient, Drone, Experimental, Ambient' in table
                page.screenshot(path=str(evidence/f'{area}-detail-{lang}.png'));page.locator('#view-close').click()
                # Explicit edits dedupe, allow same value in both, and delete independently.
                edit(page,'Legacy tags');page.locator('#tags').fill('Shared, shared，Japan');page.locator('#genre').fill('Shared, shared');save(page)
                row=next(r for r in stored(page)[area] if r['title']=='Legacy tags');assert row['tags']==['Shared','Japan'] and row['genre']=='Shared'
                edit(page,'Legacy tags');page.locator('#genre').fill('');save(page)
                row=next(r for r in stored(page)[area] if r['title']=='Legacy tags');assert row['genre']=='' and row['tags']==['Shared','Japan']
                edit(page,'Legacy tags');page.locator('#tags').fill('');save(page)
                # Optional fields across actual new-record forms.
                for i,(genre,tags) in enumerate([('Ambient, Drone','Japan, Night'),('Only genre',''),('','Only tag'),('',''),('Same','Same')]):
                    page.locator('#manual-add-trigger').click();page.locator('#manual-artist').fill('New Artist');page.locator('#manual-title').fill(f'New {i}')
                    page.locator('#genre').fill(genre);page.locator('#tags').fill(tags);save(page)
                    row=stored(page)[area][0];assert row['genre']==genre and row['tags']==([x.strip() for x in tags.split(',')] if tags else [])
                # A failed write retains both new fields and the saved original; retry persists both.
                edit(page,'New 0');before_failure=stored(page)
                page.locator('#genre').fill('Failed genre');page.locator('#tags').fill('Failed tag')
                page.evaluate('''() => {window.originalSetItem=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03')throw new DOMException('full','QuotaExceededError');return window.originalSetItem.call(this,k,v)}}''')
                page.locator('#save').click();expect(page.locator('#save-notice')).to_be_visible()
                assert stored(page)==before_failure
                page.locator('#save-return').click()
                assert page.locator('#genre').input_value()=='Failed genre' and page.locator('#tags').input_value()=='Failed tag'
                page.evaluate('()=>{Storage.prototype.setItem=window.originalSetItem}');save(page)
                assert stored(page)[area][0]['genre']=='Same'
                row=next(r for r in stored(page)[area] if r['title']=='New 0');assert row['genre']=='Failed genre' and row['tags']==['Failed tag']
                choose(page,'genre','');page.screenshot(path=str(evidence/f'{area}-filters-{lang}.png'))
                print('PASS',lang,area,'independent inputs, raw preservation, suggestions, case deduplication, IME events, filters, detail, widths',flush=True)
            # Actual export and restore handlers, including mixed historic forms.
            current=stored(page)
            with page.expect_download() as dl:page.locator('#export-json').click()
            raw=Path(dl.value.path()).read_text();assert json.loads(raw)==current
            page.locator('#import-json').set_input_files(dict(name='roundtrip.json',mimeType='application/json',buffer=raw.encode()))
            page.wait_for_function('([k,v])=>JSON.stringify(JSON.parse(localStorage.getItem(k)))===JSON.stringify(v)',arg=[KEY,current]);assert stored(page)==current
            page.locator('#import-json').set_input_files(dict(name='old-v3.json',mimeType='application/json',buffer=json.dumps(seed).encode()))
            page.wait_for_function('([k,v])=>JSON.stringify(JSON.parse(localStorage.getItem(k)))===JSON.stringify(v)',arg=[KEY,seed]);assert stored(page)==seed
            legacy=[dict(id='old',title='Old',artist='Artist',genre='Ambient，Drone',tags=' Ambient, Ambient ',rating=4)]
            page.locator('#import-json').set_input_files(dict(name='legacy.json',mimeType='application/json',buffer=json.dumps(legacy).encode()))
            page.wait_for_function('(k)=>JSON.parse(localStorage.getItem(k)).listening[0]?.id==="old"',arg=KEY);row=stored(page)['listening'][0];assert row['genre']==legacy[0]['genre'] and row['tags']==legacy[0]['tags']
            assert not errors,errors
            print('PASS',lang,'JSON export/restore exact equality, v3 historic backup, legacy-array backup; Live unchanged',flush=True)
            ctx.close()
        browser.close()
    server.shutdown()

if __name__=='__main__':main()
