"""PR #13 review A-D + state boundaries; synthetic data and actual JSON/form comparisons."""
import base64, json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from data_preservation import PHOTO, seed_data


def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    source=Path(os.environ.get('MLA_TEST_HTML',ROOT/'index.html')).read_text()
    seam="""window.review={saveDB,db:()=>db,draft:()=>draft,recovered:()=>draftRecovered,busy:()=>operationBusy,
    openEdit,setSection,pause:()=>{resizePhoto=()=>new Promise((r,j)=>{window.finishPhoto=r;window.rejectPhoto=j})}};"""
    source=source.replace("setSection('listening');showStorageState();",seam+"setSection('listening');showStorageState();")
    passed=failed=0
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        def run(area,name,case):
            nonlocal passed,failed
            ctx=browser.new_context(locale='en-US',accept_downloads=True)
            ctx.route(base+'/',lambda r:r.fulfill(body=source,content_type='text/html'))
            ctx.route('https://**/*',lambda r:r.abort())
            ctx.add_init_script("const original=Storage.prototype.setItem;window.failWrite=false;Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03'&&failWrite)throw Error('synthetic quota');return original.call(this,k,v)}")
            p=ctx.new_page();errors=[];p.on('dialog',lambda d:d.accept());p.on('pageerror',lambda e:errors.append(str(e)));p.goto(base)
            p.evaluate('([k,v])=>localStorage.setItem(k,v)',[KEY,json.dumps(seed_data())]);p.reload()
            p.evaluate('(area)=>{review.setSection(area);review.openEdit(area)}',area)
            photo='#e-live-photo' if area=='live' else '#album-photo'
            remove='#remove-photo' if area=='live' else '#remove-album-photo'
            rating='#e-live-rating' if area=='live' else '#rating'
            def draft():return p.evaluate('review.draft()')
            def stored():return p.evaluate('(k)=>JSON.parse(localStorage.getItem(k))',KEY)
            def edit(value):
                p.locator('#memo').fill(value)
                p.locator(rating).evaluate("el=>{el.value='9.0';el.dispatchEvent(new Event('input',{bubbles:true}))}")
            def save(fail):
                p.evaluate('(v)=>window.failWrite=v',fail)
                p.locator('#save').evaluate('(el)=>el.onclick()')
                p.wait_for_function('!review.busy()')
            def match(value,operation='edit'):
                d=draft();assert d is not None,'draft disappeared'
                assert d['operation']==operation,(d['operation'],operation)
                assert d['area']==area and d['recordId']==area,(d['area'],d['recordId'])
                assert d['input']['memo']==p.locator('#memo').input_value()==value
                assert d['input'][rating[1:]]==p.locator(rating).input_value()
                assert p.locator('#draft-text,#draft-export,#draft-confirm').count()==0
                return d
            def attach(name='one.png'):
                p.locator(photo).set_input_files(dict(name=name,mimeType='image/png',buffer=base64.b64decode(PHOTO.split(',')[1])))
            def blocked_close():
                p.locator('#close').click();assert p.locator('#modal').is_visible(),'unrecovered form closed'
                assert p.evaluate('review.recovered()') is False
            try:
                case(p,edit,save,match,draft,stored,attach,remove,blocked_close)
                assert not errors,errors
                print('PASS',area,name,flush=True);passed+=1
            except Exception as e:
                print('FAIL',area,name,type(e).__name__,(str(e).splitlines() or [repr(e)])[0][:240],flush=True);failed+=1
            finally:ctx.close()

        def retry(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('A first');save(True);match('A first')
            edit('A latest');save(True);match('A latest');blocked()
            save(False);assert draft() is None
            assert stored()[area][0]['memo']=='A latest' and stored()[area][0]['rating']=='9.0'
            assert not p.locator('#modal').is_visible()
        def photo_no_draft(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('B unsaved');p.locator(remove).evaluate('(el)=>el.onclick()')
            assert stored()[area][0]['photo']=='' and stored()[area][0]['memo']=='Original'
            if draft() is None:
                p.locator('#close').click();p.evaluate('(a)=>review.openEdit(a)',area)
                assert p.locator('#memo').input_value()=='B unsaved','memo lost after close/reopen; DB still contains Original'
            assert match('B unsaved','photo-remove')['photoState']['savedPhotoRemoved'];blocked()
        def photo_pending(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('B pending');attach();save(True);before=match('B pending')['proposedRecord']['photo']
            p.evaluate('failWrite=false');p.locator(remove).evaluate('(el)=>el.onclick()')
            after=draft();assert after and after['proposedRecord']['photo']==before,'processed pending photo lost on persisted-photo removal'
            match('B pending','photo-remove')
            assert p.locator('#'+('e-live-photo' if area=='live' else 'album-photo')).evaluate('(el)=>el.files.length')==1
            blocked()
        def hidden(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('C first');attach();save(True);p.locator('#save-return').click()
            edit('C changed');p.locator('#close').click();match('C changed')
            p.locator('[data-section=collection]' if area!='collection' else '[data-section=live]').evaluate('(el)=>el.click()')
            match('C changed');blocked()
        def replaced_file(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('C photo');attach();save(True);p.locator('#save-return').click();attach('two.png')
            p.locator('#close').click();d=match('C photo')
            assert d['files'][0]['name']=='two.png'
            assert not d['proposedRecord'] or not d['proposedRecord'].get('photo'),'old processed photo falsely assigned to new file'
            assert d['limitations'];p.locator('#'+('e-live-photo' if area=='live' else 'album-photo')).set_input_files([])
            d=match('C photo');assert d['files']==[] and (not d['proposedRecord'] or not d['proposedRecord'].get('photo')) and d['limitations'];blocked()
        def unrelated(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('D retained');save(True)
            p.evaluate("()=>{URL.createObjectURL=()=>{throw Error('output failed')}}")
            p.locator('#save-return').click();p.locator('#memo').select_text();before=match('D retained');raw=stored()
            p.evaluate('failWrite=false')
            other='live' if area!='live' else 'collection'
            result=p.evaluate('(other)=>{const v=structuredClone(review.db());v[other][0].memo="unrelated";return review.saveDB(v,{area:other,id:other,kind:"edit",proposed:v[other][0]})}',other)
            if result is not False:
                p.locator('#close').click();p.evaluate('(a)=>review.openEdit(a)',area)
                assert p.locator('#memo').input_value()=='D retained','unrelated save cleared draft; memo lost after close/reopen'
            assert result is False and stored()==raw,'unrelated save ran while recovery was pending'
            assert draft()==before;match('D retained');blocked()
        def delete_guard(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('D deletion');save(True);p.evaluate('failWrite=false')
            p.locator('#delete').evaluate('(el)=>{void el.onclick()}')
            if p.locator('#delete-confirm-modal').is_visible():p.locator('#delete-accept').click()
            p.wait_for_function('!review.busy()')
            assert len(stored()[area])==2,'delete destroyed unrecovered edits'
            match('D deletion');blocked()
        def confirmed_edit(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('confirmed');save(True);p.locator('#save-again').click();p.locator('#discard-cancel').click();assert not p.evaluate('review.recovered()')
            edit('edited again');match('edited again');blocked()
        def conversion_failure(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('early photo failure');attach();p.evaluate('review.pause()')
            p.locator('#save').evaluate('(el)=>{void el.onclick();void el.onclick()}')
            p.wait_for_function('!!window.rejectPhoto')
            p.evaluate("rejectPhoto(Error('synthetic conversion failure'))");p.wait_for_function('!review.busy()')
            d=match('early photo failure');assert d['files'][0]['name']=='one.png';blocked()
        def delayed_lock(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('waiting');save(True);p.evaluate('failWrite=false')
            p.evaluate("()=>{const req=navigator.locks.request.bind(navigator.locks);navigator.locks.request=(...args)=>new Promise(r=>window.resumeSave=()=>r(req(...args)))}")
            p.locator('#save').evaluate('(el)=>{void el.onclick();void el.onclick()}');p.wait_for_function('!!window.resumeSave')
            match('waiting');assert p.locator('#modal').is_visible()
            # Simulate a late callback changing the form despite disabled native controls.
            p.locator('#memo').evaluate("el=>{el.value='late input';el.dispatchEvent(new Event('input',{bubbles:true}))}")
            p.evaluate('resumeSave()');p.wait_for_function('!review.busy()')
            assert stored()[area][0]['memo']=='waiting'
            match('late input');blocked()
        def photo_completion(p,edit,save,match,draft,stored,attach,remove,blocked):
            edit('before conversion');attach();p.evaluate('review.pause()')
            p.locator('#save').evaluate('(el)=>{void el.onclick()}');p.wait_for_function('!!window.finishPhoto')
            before=stored()
            assert p.evaluate('(area)=>review.saveDB(review.db(),{area,id:area,kind:"edit",proposed:review.db()[area][0]})',area) is False
            assert stored()==before
            p.locator('#memo').evaluate("el=>{el.value='during conversion';el.dispatchEvent(new Event('input',{bubbles:true}))}")
            p.evaluate("finishPhoto('data:image/jpeg;base64,AAAA')");p.wait_for_function('!review.busy()')
            assert stored()[area][0]['memo']=='before conversion'
            assert match('during conversion')['proposedRecord']['photo']=='data:image/jpeg;base64,AAAA';blocked()
        def delete_wait(p,edit,save,match,draft,stored,attach,remove,blocked):
            # Existing deletion confirmation must exclude a second asynchronous save.
            p.locator('#delete').evaluate('(el)=>{void el.onclick()}');expect(p.locator('#delete-confirm-modal')).to_be_visible()
            raw=stored();p.evaluate('failWrite=true')
            result=p.evaluate('review.saveDB(review.db(),{kind:"restore"})')
            assert result is False and stored()==raw
            assert draft() is None,'another operation replaced recovery during deletion confirmation'
            p.locator('#delete-cancel').click();p.wait_for_function('!review.busy()')
        for area in ['listening','collection','live']:
            for name,case in [('A repeated failure / exact retry',retry),('B photo success without previous draft',photo_no_draft),('B pending processed photo',photo_pending),('C hide/edit/reopen/navigation',hidden),('C new file invalidates processed photo',replaced_file),('D unavailable download / text copy / unrelated refusal',unrelated),('D deletion cannot discard draft',delete_guard),('boundary discard cancelled then edited',confirmed_edit),('boundary conversion failed early',conversion_failure),('boundary delayed completion / double click',delayed_lock),('boundary deletion confirmation / second failure',delete_wait),('boundary input changed during photo conversion',photo_completion)]:
                run(area,name,case)
        browser.close()
    server.shutdown()
    print(f'TOTAL success={passed} failure={failed} unexecuted=0',flush=True)
    if failed:raise SystemExit(1)

if __name__=='__main__':main()
