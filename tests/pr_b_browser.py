"""DP-05: synthetic shared-origin tabs, real Chromium Web Locks, isolated profile."""
import copy, json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler
from data_preservation import OLD, PHOTO, seed_data

LOCK='mla:'+KEY+':write'

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    seam="window.b={saveDB,db:()=>db,openEdit,setSection,create:openCreateListening,busy:()=>operationBusy,draft:()=>draft,pause:()=>{resizePhoto=()=>new Promise(r=>window.finishPhoto=r)}};"
    html=(ROOT/'index.html').read_text().replace("setSection('listening');showStorageState();",seam+"setSection('listening');showStorageState();")
    count=0
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
        ctx=browser.new_context(accept_downloads=True,locale='en-US')
        ctx.route(base+'/',lambda r:r.fulfill(body=html,content_type='text/html'))
        ctx.route('https://**/*',lambda r:r.abort())
        a=ctx.new_page();b=ctx.new_page();errors=[]
        for p in [a,b]:
            p.on('dialog',lambda d:d.accept())
            p.on('pageerror',lambda e:errors.append(str(e)))
        a.goto(base);b.goto(base)
        def raw():return a.evaluate('(k)=>localStorage.getItem(k)',KEY)
        def reset(seed=None):
            a.evaluate('([k,o,v])=>{localStorage.clear();if(v!==null)localStorage.setItem(k,v)}',[KEY,OLD,json.dumps(seed or seed_data())])
            a.reload();b.reload()
        def change(area,kind):
            d=seed_data()
            if kind=='delete':d[area]=d[area][1:]
            elif kind=='create':d[area].append(dict(d[area][0],entryId='new'))
            elif kind=='photo':d[area][0]['photo']='data:image/jpeg;base64,AAAA'
            else:d[area][0]['memo']=kind
            return d
        # Same/different areas, create/edit/delete/restore/photo: stale snapshot never wins.
        for winner in ['listening','collection','live']:
            for loser in ['listening','collection','live']:
                for kind in ['create','edit','delete','restore','photo']:
                    reset();first=change(winner,'winner');second=change(loser,kind)
                    assert a.evaluate('(v)=>b.saveDB(v)',first)
                    assert b.evaluate('(v)=>b.saveDB(v)',second) is False
                    assert json.loads(raw())==first
                    assert b.evaluate('b.db().listening[0].memo')=='Original'
                    count+=1
        print('PASS sequential same/different-area operation matrix:',count)
        # Simultaneous real requests: exactly one save, even before storage notification.
        reset();a.evaluate('(v)=>{window.result=b.saveDB(v)}',change('live','A'))
        b.evaluate('(v)=>{window.result=b.saveDB(v)}',change('collection','B'))
        results=[a.evaluate('result'),b.evaluate('result')];assert sum(results)==1;count+=1
        # Suppress storage listener completely: raw guard handles change/delete/empty string.
        for value in [None,'',json.dumps(change('live','external'))]:
            reset()
            # Own-page writes do not dispatch storage to that same page.
            b.evaluate('([k,v])=>v===null?localStorage.removeItem(k):localStorage.setItem(k,v)',[KEY,value])
            assert b.evaluate('b.saveDB(b.db())') is False
            assert raw()==value;count+=1
        reset();before=raw();assert b.evaluate('()=>b.saveDB({...b.db(),extra:Infinity})') is False;assert raw()==before;count+=1
        # API absence, insecure context, request rejection, thrown request, lock busy.
        for mode in ['absent','insecure','reject','throw','held']:
            reset();before=raw()
            if mode=='absent':b.evaluate("Object.defineProperty(navigator,'locks',{value:undefined})")
            if mode=='insecure':b.evaluate("Object.defineProperty(window,'isSecureContext',{value:false})")
            if mode=='reject':b.evaluate("()=>{navigator.locks.request=()=>Promise.reject(Error('secret'))}")
            if mode=='throw':b.evaluate("()=>{navigator.locks.request=()=>{throw Error('secret')}}")
            if mode=='held':
                a.evaluate('(name)=>{window.hold=navigator.locks.request(name,()=>new Promise(r=>window.release=r))}',LOCK)
                a.wait_for_function('!!window.release')
            assert b.evaluate('b.saveDB(b.db())') is False
            assert raw()==before
            if mode=='held':a.evaluate('release()')
            count+=1
        # Tab holding the lock closes: browser releases it; fresh tab can save.
        reset();holder=ctx.new_page();holder.goto(base)
        holder.evaluate('(name)=>{navigator.locks.request(name,()=>new Promise(r=>window.held=true))}',LOCK)
        holder.wait_for_function('window.held');holder.close()
        assert a.evaluate('b.saveDB(b.db())');count+=1
        # First save keeps null distinct from an empty string.
        a.evaluate('localStorage.clear()');a.reload();assert a.evaluate('b.saveDB(b.db())');count+=1
        print('PASS lock/absent/insecure/exceptions/release/raw guards; cumulative:',count)
        # Preserve all form input and processed photo, no whole DB in recovery.
        for area in ['listening','collection','live']:
            for kind in ['edit','create']:
                reset();b.evaluate('(area)=>b.setSection(area)',area)
                if kind=='edit':b.evaluate('(area)=>b.openEdit(area)',area)
                elif area=='live':b.locator('#add-live-trigger').click();b.locator('#live-title').fill('Unsaved Live')
                else:b.locator('#manual-add-trigger').click();b.locator('#manual-title').fill('Unsaved Album');b.locator('#manual-artist').fill('Unsaved Artist')
                memo='#live-notes' if area=='live' and kind=='create' else '#memo'
                b.locator(memo).fill('未保存メモ / unsaved')
                date_id='live-date' if kind=='create' and area=='live' else 'e-live-date' if area=='live' else 'date'
                b.locator('#'+date_id+'-parts input').fill('2026')
                b.locator('#'+date_id+'-parts input').dispatch_event('change')
                b.locator('#'+date_id+'-parts select').nth(0).select_option('04')
                b.locator('#'+date_id+'-parts select').nth(1).select_option('05')
                photo='#live-photo' if area=='live' and kind=='create' else '#e-live-photo' if area=='live' else '#album-photo'
                import base64
                b.locator(photo).set_input_files(dict(name='photo.png',mimeType='image/png',buffer=base64.b64decode(PHOTO.split(',')[1])))
                assert a.evaluate('(v)=>b.saveDB(v)',change('listening','winner'))
                if area=='live' and kind=='create':b.locator('#live-form button').last.click()
                else:b.locator('#save').click()
                expect(b.locator('#save-notice')).to_be_visible();assert b.locator('#unsaved-recovery,#draft-export,#draft-text,#draft-confirm').count()==0
                draft=b.evaluate('b.draft()');assert draft['area']==area
                assert '未保存メモ' in json.dumps(draft,ensure_ascii=False)
                assert draft['proposedRecord']['photo'].startswith('data:image/jpeg;')
                assert 'listening' not in draft['base'] and 'raw' not in draft['base']
                assert draft['input'][date_id]=='2026-04-05'
                assert draft['input']['dateParts'][date_id+'-parts']==['2026','04','05']
                if area!='live':assert draft['input']['manual-artist'] and draft['input']['manual-title']
                assert draft['files'][0]['name']=='photo.png';assert 'Original photo' in draft['limitations']
                assert b.locator(memo).input_value()=='未保存メモ / unsaved'
                rating_root='#live-form' if area=='live' and kind=='create' else '#live-edit-fields' if area=='live' else '#album-fields'
                b.locator(rating_root+' .rating-clear').click()
                draft=b.evaluate('b.draft()')
                assert draft['input']['live-rating' if area=='live' and kind=='create' else 'e-live-rating' if area=='live' else 'rating']==''
                # The same internal data/photos remain protected without JSON UI.
                before=raw();b.evaluate("async v=>{await document.getElementById('import-json').onchange({target:{files:[{text:async()=>v}],value:'x'}})}",json.dumps(draft));assert raw()==before
                b.evaluate("()=>{URL.createObjectURL=()=>{throw Error('download failed')}}")
                b.locator('#save-return').click();b.locator(memo).select_text()
                assert b.locator(memo).evaluate('e=>e.selectionEnd-e.selectionStart')==len('未保存メモ / unsaved')
                assert b.locator(memo).input_value()=='未保存メモ / unsaved';assert b.evaluate('b.draft()')==draft;count+=1
        print('PASS all areas create/edit internal draft + photos/text copy/no JSON UI/restore rejection; cumulative:',count)
        # Slow photo: duplicate submits and attempted navigation cannot mix targets.
        reset();b.evaluate("b.openEdit('listening');b.pause()")
        b.locator('#album-photo').set_input_files(dict(name='photo.png',mimeType='image/png',buffer=b'x'))
        b.evaluate("document.getElementById('save').onclick();document.getElementById('save').onclick();document.querySelector('[data-section=live]').click()")
        assert b.evaluate('b.busy()')
        b.locator('#album-fields .star-rating').dispatch_event('pointerdown',dict(pointerId=1,clientX=900))
        assert b.locator('#rating').input_value()=='8.4'
        expect(b.locator('#modal')).to_be_visible()
        b.evaluate("finishPhoto('data:image/jpeg;base64,AAAA')")
        b.wait_for_function('!b.busy()');assert json.loads(raw())['listening'][0]['photo']=='data:image/jpeg;base64,AAAA';count+=1
        print('PASS slow photo')
        # Deletion confirmation keeps target fixed; failed deletion has no replay payload.
        reset();b.evaluate("b.openEdit('listening');void document.getElementById('delete').onclick()")
        b.evaluate("document.querySelector('[data-section=live]').click()")
        assert a.evaluate('(v)=>b.saveDB(v)',change('collection','winner'))
        b.locator('#delete-accept').click();b.wait_for_function('!b.busy()')
        assert len(json.loads(raw())['listening'])==2
        assert b.evaluate('b.draft().operation')=='delete';assert b.evaluate('b.draft().proposedRecord') is None;count+=1
        print('PASS delete')
        # Lock busy -> input retained -> retry succeeds after release.
        reset();b.evaluate("b.openEdit('listening')");b.locator('#memo').fill('retry')
        a.evaluate('(name)=>{navigator.locks.request(name,()=>new Promise(r=>window.release=r))}',LOCK);a.wait_for_function('!!window.release')
        b.locator('#save').click();b.wait_for_function('!b.busy()');assert b.locator('#memo').input_value()=='retry'
        a.evaluate('release()');b.locator('#remove-album-photo').evaluate('(el)=>el.onclick()');assert b.evaluate('b.draft()') is not None
        b.locator('#close').click();expect(b.locator('#modal')).to_be_visible();assert b.locator('#memo').input_value()=='retry'
        b.locator('#save').click();expect(b.locator('#modal')).not_to_be_visible();assert json.loads(raw())['listening'][0]['memo']=='retry';count+=1
        print('PASS retry')
        # Startup migration pauses before real lock to simulate another tab writing current/old key.
        legacy=[dict(id='',title='Legacy',artist='Artist')]
        b.add_init_script("{const req=navigator.locks.request.bind(navigator.locks);navigator.locks.request=(...args)=>new Promise(r=>window.resumeMigration=()=>r(req(...args)))}")
        for target in [KEY,OLD,None]:
            a.evaluate('([o,v])=>{localStorage.clear();localStorage.setItem(o,v)}',[OLD,json.dumps(legacy)])
            b.reload();b.wait_for_function('!!window.resumeMigration')
            if target:a.evaluate('([k,v])=>localStorage.setItem(k,v)',[target,json.dumps(seed_data() if target==KEY else legacy+[dict(id='',title='Other',artist='A')])])
            b.evaluate('resumeMigration()');b.wait_for_function('!b.busy()')
            if target:expect(b.locator('#storage-state')).to_be_visible()
            else:assert json.loads(raw())['listening'][0]['title']=='Legacy'
            assert a.evaluate('(o)=>localStorage.getItem(o)',OLD) is not None;count+=1
        # Startup without Web Locks: original stays byte-for-byte; retry after reload.
        m=ctx.new_page();m.on('dialog',lambda d:d.accept())
        m.add_init_script("if(localStorage.getItem('no-lock'))Object.defineProperty(navigator,'locks',{value:undefined})")
        a.evaluate('([o,v])=>{localStorage.clear();localStorage.setItem(o,v);localStorage.setItem("no-lock","yes")}',[OLD,json.dumps(legacy)])
        m.goto(base);expect(m.locator('#storage-state')).to_be_visible();assert raw() is None
        with m.expect_download() as dl:m.locator('#recover-source').click()
        assert Path(dl.value.path()).read_text()==json.dumps(legacy)
        m.evaluate("localStorage.removeItem('no-lock')");m.reload()
        m.wait_for_function('(k)=>localStorage.getItem(k)!==null',arg=KEY)
        assert json.loads(raw())['listening'][0]['title']=='Legacy';m.close();count+=1
        assert not errors,errors
        print('PASS asynchronous operations/retry/migration races; total scenarios:',count)
        browser.close()
    server.shutdown()

if __name__=='__main__':main()
