"""Isolated real browser + mocked API; no external requests. Includes timing evidence."""
import json, threading, subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright, expect
from ui_v0322 import ROOT, KEY, QuietHandler, SEED, stored

OUT=ROOT/'docs/search-performance-evidence'
def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    evidence=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for phase in ['before','after']:
          html=subprocess.check_output(['git','show','3db1183:index.html'],cwd=ROOT).decode() if phase=='before' else (ROOT/'index.html').read_text()
          js=subprocess.check_output(['git','show','3db1183:search.js'],cwd=ROOT).decode() if phase=='before' else (ROOT/'search.js').read_text()
          # Instrument only served test copy. Production code contains no telemetry.
          html=html.replace("function status(v){$('status').textContent=v}", "function status(v){$('status').textContent=v;window.statusAt=performance.now()}")
          html=html.replace('async function fetchSearch(', """const renderMeasured=renderResults;renderResults=function(){const t=performance.now();try{return renderMeasured()}finally{window.domMs=performance.now()-t}};
async function fetchSearch(""")
          for lang in ['ja','en']:
            ctx=browser.new_context(viewport=dict(width=320,height=844))
            ctx.route('https://**/*',lambda r:r.abort())
            ctx.route(base+'/',lambda r:r.fulfill(body=html,content_type='text/html'))
            ctx.route('**/search.js',lambda r:r.fulfill(body=js,content_type='text/javascript'))
            state=dict(code=200,fail=0,header=None,empty=False,choices=False,requests=[])
            rows=[dict(id=str(i),title='Twin',**{'primary-type':'Album','artist-credit':[dict(name='Twin')]}) for i in range(105)]
            def api(r):
                from urllib.parse import urlparse,parse_qs
                u=urlparse(r.request.url);q=parse_qs(u.query);state['requests'].append(r.request.url)
                if state['fail']:
                    state['fail']-=1;r.fulfill(status=state['code'],headers={'Retry-After':state['header']} if state['header'] else {},json={});return
                if state['empty']:data={'artists':[],'count':0,'release-groups':[]}
                elif '/artist/' in u.path:data={'artists':[dict(id='a',name='Twin',aliases=[]),dict(id='b',name='Twin',aliases=[])] if state['choices'] else [dict(id='a',name='Twin',aliases=[])]}
                else:
                    off=int(q.get('offset',['0'])[0]);data={'count':105,'release-group-count':105,'release-groups':rows[off:off+100]}
                r.fulfill(json=data)
            ctx.route('https://musicbrainz.org/**',api)
            p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
            p.goto(base);p.evaluate('([k,d,l])=>{localStorage.setItem(k,JSON.stringify(d));localStorage.setItem("mma-ui-language",l)}',[KEY,SEED,lang]);p.reload()
            p.evaluate("""()=>{window.net=[];const f=fetch;window.fetch=async(...a)=>{const start=performance.now();const r=await f(...a);const received=performance.now();const j=r.json.bind(r);r.json=async()=>{const t=performance.now();const d=await j();net.push({start,apiMs:received-start,jsonMs:performance.now()-t});return d};return r}}""")
            def submit(mode='title',query='Twin'):
                p.locator(f'[data-search-mode={mode}]').click();p.locator('#query').fill(query)
                p.evaluate("()=>{window.actionAt=performance.now();document.querySelector('#search-form').requestSubmit()}")
            for mode in ['title','artist']:
              for repeat in [False,True]:
                submit(mode)
                expect(p.locator('#results .result')).to_have_count(30)
                expect(p.locator('#status')).not_to_contain_text('Searching' if lang=='en' else '検索中')
                m=p.evaluate("()=>({elapsedMs:statusAt-actionAt,firstFetchDelayMs:net.length?net[0].start-actionAt:null,domMs,net})")
                cpu=p.evaluate('''async()=>{const rows=Array.from({length:100},(_,i)=>({id:String(i%90),title:'Twin','primary-type':'Album'}));const t=performance.now();MMASearch.unique(rows);const dedupMs=performance.now()-t;const u=performance.now();MMASearch.sortTitles(rows,'Twin');const sortMs=performance.now()-u;return {dedupMs,sortMs}}''')
                if mode=='artist':
                    cpu['cachedArtistCandidateMs']=p.evaluate("async()=>{const t=performance.now();await MMASearch.artistSearch('Twin');return performance.now()-t}")
                m.update(cpu)
                evidence.append(dict(phase=phase,lang=lang,mode=mode,repeat=repeat,**m))
                p.evaluate('()=>{net=[]}')
            if phase=='before':ctx.close();continue
            # The clock accelerates existing backoffs; API calls still go through production code.
            p.clock.install()
            def settle():
                for _ in range(20):
                    p.clock.run_for(1500)
                    if p.locator('#status').inner_text() not in ['検索中…','Searching…']:return
                raise AssertionError('search remained pending')
            searching='検索中…' if lang=='ja' else 'Searching…'
            failed='検索できませんでした。時間をおいて再度お試しください。' if lang=='ja' else 'Search failed. Please try again later.'
            for code in [429,502,503,504]:
                state.update(code=code,fail=1,header='5' if code==503 else None)
                submit(query='retry'+str(code));expect(p.locator('#status')).to_have_text(searching)
                p.clock.run_for(300);expect(p.locator('#status')).to_have_text(searching)
                settle();expect(p.locator('#results .result')).to_have_count(30)
            # A real AbortSignal from the production 20-second timeout, no network sent.
            p.evaluate('''()=>{const real=fetch;let first=true;window.fetch=(...a)=>{if(first){first=false;return new Promise((resolve,reject)=>a[1].signal.addEventListener('abort',()=>reject(new DOMException('timeout','AbortError'))))}return real(...a)}}''')
            submit(query='timeout');expect(p.locator('#status')).to_have_text(searching);settle()
            expect(p.locator('#results .result')).to_have_count(30)
            state.update(code=503,fail=4,header=None)
            submit(query='failure');settle();expect(p.locator('#status')).to_have_text(failed)
            other='en' if lang=='ja' else 'ja'
            p.locator('#ui-language').select_option(other)
            expect(p.locator('#status')).to_have_text('Search failed. Please try again later.' if other=='en' else '検索できませんでした。時間をおいて再度お試しください。')
            p.locator('#ui-language').select_option(lang)
            state.update(fail=0,empty=True)
            submit(query='empty');settle();assert p.locator('#status').inner_text()!=failed
            state.update(empty=False,choices=True)
            submit('artist','Twin candidates');settle()
            # Matching candidate name must equal query for exact selection.
            state['choices']=True;submit('artist','Twin');settle()
            # Clear cache by reloading so candidate fixture is used.
            p.reload();submit('artist','Twin');settle()
            expect(p.locator('#artist-candidates button')).to_have_count(2)
            p.locator('#artist-candidates button').first.click();settle();expect(p.locator('#results .result')).to_have_count(30)
            # Local batches, then second raw page.
            for count in [60,90,105]:
                p.locator('#more-results').click();settle();expect(p.locator('#results .result')).to_have_count(count)
            for action in ['mode','clear','section','research']:
                state.update(code=503,fail=1,choices=False)
                submit(query='cancel '+action);p.clock.run_for(1400);expect(p.locator('#status')).to_have_text(searching)
                if action=='mode':p.locator('[data-search-mode=artist]').click()
                elif action=='clear':p.locator('#clear-search').click()
                elif action=='section':p.locator('[data-section=collection]').click()
                else:state['fail']=0;submit(query='replacement')
                if action=='research':settle();expect(p.locator('#results .result')).to_have_count(30)
                else:
                    p.clock.run_for(20000);expect(p.locator('#status')).to_have_text('');expect(p.locator('#results .result')).to_have_count(0)
            state.update(code=503,fail=1,choices=False)
            submit(query='language wait');expect(p.locator('#status')).to_have_text(searching)
            p.locator('#ui-language').select_option(other)
            expect(p.locator('#status')).to_have_text('Searching…' if other=='en' else '検索中…')
            p.locator('#ui-language').select_option(lang)
            for width in [320,1280]:
                p.set_viewport_size(dict(width=width,height=844))
                assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
                p.screenshot(path=str(OUT/f'searching-{lang}-{width}.png'),full_page=True)
            settle()
            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert p.evaluate("async()=>MLAPhotos.unpack(JSON.parse(localStorage.getItem('my-music-archive-photos-v1')))")==SEED and not errors,errors
            print('PASS',lang,'retry codes, Retry-After, terminal failure, empty, candidates, pagination, cancellation, re-search, no writes, layout')
            ctx.close()
        browser.close()
    (OUT/'browser-timing.json').write_text(json.dumps(evidence,indent=2))
    server.shutdown()
if __name__=='__main__':main()
