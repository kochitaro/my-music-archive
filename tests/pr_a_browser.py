"""PR-A synthetic import/startup/ID boundary tests. No production test API."""
import copy, json, os, threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, stored
from data_preservation import OLD, seed_data, backup


def stored(page):
    return json.loads(page.evaluate('(k)=>localStorage.getItem(k)', KEY))

def memory(page):
    return json.loads(page.evaluate('JSON.stringify(a.db())'))

def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    seam = """window.a={db:()=>JSON.parse(JSON.stringify(db)),migrate,saveDB,openEdit,operationRecord,newId,setSection,
    mutate:f=>f(db),pausePhoto:()=>{resizePhoto=()=>new Promise(resolve=>window.finishPhoto=resolve)},renderFailure:v=>{render=v?()=>{throw Error('INTERNAL_SECRET')}:originalRender}};const originalRender=render;"""
    html = Path(os.environ.get('MLA_TEST_HTML', ROOT/'index.html')).read_text().replace("setSection('listening');showStorageState();", seam+"setSection('listening');showStorageState();")
    count = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'), args=['--no-sandbox'])
        ctx = browser.new_context(locale='en-US', accept_downloads=True)
        ctx.route(base+'/',lambda r:r.fulfill(body=html,content_type='text/html'))
        ctx.route('https://**/*',lambda r:r.abort())
        ctx.add_init_script("""const set=Storage.prototype.setItem;window.failWrite=localStorage.getItem('fail-startup')==='yes';window.writes=[];Storage.prototype.setItem=function(k,v){if(k==='my-music-archive-pilot-v03'){writes.push(v);if(window.failWrite)throw Error('INTERNAL_SECRET')}return set.call(this,k,v)}""")
        page=ctx.new_page();alerts=[];errors=[];choice=[True]
        page.on('dialog',lambda d:(alerts.append(d.message),d.accept() if d.type!='confirm' or choice[0] else d.dismiss()))
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(base)
        seed=seed_data()
        def reset(v=seed,old=False):
            page.evaluate('([k,o,v,old])=>{failWrite=false;localStorage.removeItem(k);localStorage.removeItem(o);localStorage.setItem(old?o:k,v)}',[KEY,OLD,json.dumps(v),old])
            page.reload()
        def raw():return page.evaluate('(k)=>localStorage.getItem(k)',KEY)
        def state():return [raw(),memory(page),page.evaluate('writes.length')]
        def imp(raw):
            page.evaluate("async raw=>{const el=document.getElementById('import-json');await el.onchange({target:{files:[{text:async()=>raw}],value:'x'}})}",raw)
        required_count=0
        for area in ['listening','collection','live']:
            for field in ['title','artist']:
                for name,value in [('missing',None),('null',None),('empty',''),('whitespace',' \t '),('number',7),('boolean',False),('array',[]),('object',{})]:
                    candidate=copy.deepcopy(seed)
                    if name=='missing':candidate[area][0].pop(field,None)
                    else:candidate[area][0][field]=value
                    required=field=='title' or area!='live'
                    reject=required and (not isinstance(value,str) or (area=='live' and not value.strip()))
                    reset();before=state();imp(json.dumps(candidate));imported=state()!=before
                    if not os.environ.get('MLA_REQUIRED_OBSERVE'):
                        if reject:
                            assert state()==before,(area,field,name,alerts[-1])
                            assert area+'[1].'+field in alerts[-1]
                        else:assert stored(page)==candidate and memory(page)==candidate
                    reset();before=state();saved=page.evaluate('(v)=>a.saveDB(v)',candidate)
                    if not os.environ.get('MLA_REQUIRED_OBSERVE'):
                        assert saved is not reject,(area,field,name)
                        if reject:assert state()==before
                        else:assert stored(page)==candidate and memory(page)==candidate
                    reset(candidate);stopped=page.locator('#storage-state').is_visible()
                    if os.environ.get('MLA_REQUIRED_OBSERVE'):
                        print('OBSERVE',area,field,name,'import=',imported,'save=',saved,'startup_stopped=',stopped,'expect_reject=',reject)
                    else:
                        assert stopped is reject,(area,field,name)
                        assert raw()==json.dumps(candidate) and page.evaluate('writes.length')==0
                        if reject:
                            assert memory(page)==dict(version=3,listening=[],collection=[],live=[])
                            with page.expect_download() as dl:page.locator('#recover-source').click()
                            assert Path(dl.value.path()).read_bytes()==json.dumps(candidate).encode()
                            assert page.evaluate('a.saveDB(a.db())') is False
                            assert raw()==json.dumps(candidate) and page.evaluate('writes.length')==0
                        else:assert memory(page)==candidate and backup(page)==candidate
                    required_count+=3
        if os.environ.get('MLA_REQUIRED_OBSERVE'):
            browser.close();server.shutdown();return
        print('PASS required-field matrix: import/save/startup + exact recovery:',required_count)
        invalid=['{', 'null','[]x',json.dumps(dict(version=1,listening=[],collection=[],live=[])),json.dumps(dict(listening=[]))]
        for k,v in [('live',None),('collection',{}),('listening',[None]),('live',[dict(entryId=42,title='Live')]),('live',[dict(entryId='a',title='Live',date='2026-02-30')]),('live',[dict(entryId='a',title='Live',artists=None)]),('live',[dict(entryId='a',title='Live',rating='abc')]),('live',[dict(entryId='a',title='Live',rating=-1)]),('live',[dict(entryId='a',title='Live'),dict(entryId='a',title='Live')]),('live',[dict(title='missing')])]:
            d=copy.deepcopy(seed);d[k]=v;invalid.append(json.dumps(d))
        d=copy.deepcopy(seed);del d['live'];invalid.append(json.dumps(d))
        for bad in invalid:
            reset();before=state();imp(bad);assert state()==before,(bad,alerts[-1]);assert 'Invalid data' in alerts[-1];count+=1
            page.evaluate('([k,v])=>localStorage.setItem(k,v)',[KEY,bad]);page.reload()
            expect(page.locator('#storage-state')).to_be_visible();assert raw()==bad;assert page.evaluate('writes.length')==0
            with page.expect_download() as dl:page.locator('#recover-source').click()
            assert Path(dl.value.path()).read_text()==bad
            assert page.evaluate('a.saveDB(a.db())') is False;assert raw()==bad;count+=1
        print('PASS invalid import + startup exact raw recovery:',len(invalid)*2)
        # Every compatibility variant survives import/save/reload/export unchanged.
        variants=copy.deepcopy(seed);variants['unknown']={'keep':[1,None,True]};variants['__proto__']={'safe':True}
        variants['constructor']={'prototype':{'safe':True}}
        variants['listening']=[]
        for i,score in enumerate([0,10,8.5,'8.5','8.55','',None]):
            r=dict(entryId=str(i),id='',title='Manual',artist='A',rating=score,date='2020/01/02',tags=[' a ','a',''],photo='data:image/png;base64,a',memo=None,extra={'__proto__':1})
            variants['listening'].append(r)
        for tags in ['a, b',None]:variants['listening'].append(dict(entryId='tags'+str(tags),title='Tags',artist='Artist',tags=tags))
        variants['listening'].append(dict(entryId='missing',title='Missing',artist='Artist'))
        variants['live']=[dict(entryId='0',title='Old'),dict(entryId='empty',title='Empty',artists=[]),dict(entryId='multi',title='Multi',artists=['B','A','B'])]
        reset();imp(json.dumps(variants));assert stored(page)==variants, (stored(page),variants);assert memory(page)==variants;assert backup(page)==variants
        assert page.evaluate('a.saveDB(a.db())');page.reload();assert backup(page)==variants;count+=1
        assert page.evaluate("a.operationRecord('listening','0').title")=='Manual';assert page.evaluate("a.operationRecord('live','0').title")=='Old';count+=1
        print('PASS compatibility exact import/save/reload/export; cross-area IDs')
        legacy=[dict(id='',title='Manual',artist='Artist',listened='2020/01/02',rating='4.25',tags=None,extra=1),dict(id='same',title='First',artist='Artist',entryId='keep',rating=1),dict(id='same',title='Second',artist='Artist',rating=5)]
        for old in [False,True]:
            reset(legacy if old else seed,old=old)
            if not old:imp(json.dumps(legacy))
            migrated=memory(page);assert [r['title'] for r in migrated['listening']]==['Manual','First','Second'];assert [r['rating'] for r in migrated['listening']]==['8.5','2','10'];assert len({r['entryId'] for r in migrated['listening']})==3;assert migrated['listening'][1]['entryId']=='keep';assert backup(page)==migrated
            if old:assert page.evaluate('(k)=>localStorage.getItem(k)',OLD)==json.dumps(legacy)
            page.reload();assert memory(page)==migrated;count+=1
        reset();before=state();imp(json.dumps(legacy+[None]));assert state()==before;count+=1
        reset(legacy+[None],old=True);assert raw() is None;expect(page.locator('#storage-state')).to_be_visible();assert page.evaluate('writes.length')==0;count+=1
        reset(legacy,old=True);page.evaluate("localStorage.removeItem('"+KEY+"');localStorage.setItem('fail-startup','yes')");page.reload()
        assert raw() is None;expect(page.locator('#storage-state')).to_be_visible()
        with page.expect_download() as dl:page.locator('#recover-source').click()
        assert Path(dl.value.path()).read_text()==json.dumps(legacy);count+=1
        page.evaluate("localStorage.removeItem('fail-startup')");page.reload();assert len(stored(page)['listening'])==3;count+=1
        print('PASS legacy import/startup count/order/IDs/scores and whole rejection')
        reset();before=state();choice[0]=False;imp(json.dumps(variants));choice[0]=True;assert state()==before;assert 'cancelled' in alerts[-1];count+=1
        page.evaluate("async()=>{await document.getElementById('import-json').onchange({target:{files:[{text:async()=>{throw Error('INTERNAL_SECRET')}}],value:'x'}})}")
        assert state()==before;assert 'File could not be read' in alerts[-1];count+=1
        page.evaluate('failWrite=true');imp(json.dumps(variants));assert raw()==before[0];assert memory(page)==before[1];assert page.locator('#save-notice-title').inner_text()=='Couldn’t Save Changes';assert page.locator('#save-notice-reason').is_hidden();count+=1
        page.evaluate('failWrite=false;a.renderFailure(true)');imp(json.dumps(variants));assert stored(page)==variants, (stored(page),variants);assert memory(page)==variants;assert 'Saving completed' in alerts[-1];assert page.evaluate('writes.length')==2;count+=1
        page.evaluate('a.renderFailure(false)');assert page.evaluate('a.saveDB(a.db())');page.reload();assert backup(page)==variants;count+=1
        print('PASS cancel/read/write/render boundaries + subsequent save/reload')
        # Mutation seams simulate unexpected in-memory corruption/races. Never touch real user data.
        for control in ['save','delete','remove-album-photo']:
            reset();page.evaluate("a.openEdit('listening')");page.evaluate("a.mutate(db=>db.listening.push({...db.listening[0]}))")
            before=state();page.locator('#'+control).evaluate('(e)=>e.onclick()');assert state()==before;assert 'duplicate internal ID' in alerts[-1];count+=1
        reset();page.evaluate("a.setSection('live');a.openEdit('live');a.mutate(db=>db.live.push({...db.live[0]}))")
        before=state();page.locator('#remove-photo').evaluate('(e)=>e.onclick()');assert state()==before;count+=1
        for change in ["db.listening.push({...db.listening[0]})", "db.listening=[]"]:
            reset();page.evaluate("a.openEdit('listening');void document.getElementById('delete').onclick()")
            page.evaluate('a.mutate(db=>{'+change+'})');before=state();page.locator('#delete-accept').click();assert state()==before;assert 'target mismatch' in alerts[-1];count+=1
        # Pause asynchronous photo processing and corrupt/remove the selected target.
        for change in ["db.listening.push({...db.listening[0]})", "db.listening=[]"]:
            reset();page.evaluate("a.openEdit('listening');a.pausePhoto();document.getElementById('album-photo').files=new DataTransfer().files")
            page.locator('#album-photo').set_input_files(dict(name='synthetic.png',mimeType='image/png',buffer=b'synthetic'))
            page.evaluate("document.getElementById('save').onclick();a.mutate(db=>{"+change+"})")
            before=state();page.evaluate("finishPhoto('data:image/png;base64,a')");assert state()==before;assert 'target mismatch' in alerts[-1];count+=1
        shared=copy.deepcopy(seed)
        for area in ['listening','collection','live']:shared[area][0]['entryId']='same'
        shared['listening'][0]['id']=shared['listening'][1]['id']='same-work'
        reset(shared);page.evaluate("a.openEdit('same')");page.locator('#memo').fill('Only selected record');page.locator('#save').click()
        page.wait_for_function("!document.getElementById('modal').classList.contains('open')")
        assert stored(page)['listening'][0]['memo']=='Only selected record'
        assert stored(page)['listening'][1]==shared['listening'][1]
        for area in ['collection','live']:assert stored(page)[area]==shared[area]
        count+=1
        page.evaluate("a.openEdit('same');void document.getElementById('delete').onclick()");page.locator('#delete-accept').click()
        page.wait_for_function("!document.getElementById('modal').classList.contains('open')")
        assert stored(page)['listening']==[shared['listening'][1]]
        for area in ['collection','live']:assert stored(page)[area]==shared[area]
        count+=1
        # ID collision regeneration (existing and newly migrated IDs).
        reset()
        result=page.evaluate("""()=>{const original=crypto.randomUUID;let ids=['listening','unique'];crypto.randomUUID=()=>ids.shift();const id=a.newId();crypto.randomUUID=original;return id}""")
        assert result=='unique';count+=1
        result=page.evaluate("""()=>{const original=crypto.randomUUID;let ids=['keep','fresh','fresh','other'];crypto.randomUUID=()=>ids.shift();const out=a.migrate([{id:'',title:'A',artist:'Artist'},{id:'',title:'B',artist:'Artist',entryId:'keep'},{id:'',title:'C',artist:'Artist'}]);crypto.randomUUID=original;return out.listening.map(r=>r.entryId)}""")
        assert result==['fresh','keep','other'];count+=1
        assert all('INTERNAL_SECRET' not in a for a in alerts);assert not errors,errors
        print('PASS ID guards/deletion recheck/generation; total scenarios:',count)
        browser.close()
    server.shutdown()

if __name__=='__main__':main()
