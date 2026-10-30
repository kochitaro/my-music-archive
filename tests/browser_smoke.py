"""Mock-only browser regression tests. Run from the repository root with Playwright installed."""
import json, os, threading, time, urllib.parse
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
ARTISTS=json.loads((ROOT/'tests/fixtures/artists.json').read_text())
MODES=json.loads((ROOT/'tests/fixtures/search-v0.3.21.json').read_text())
KEY='my-music-archive-pilot-v03'
SEED={'version':3,'listening':[{'entryId':'old','id':'old','title':'Existing','artist':'Existing Artist','release':'1999','date':'2024-01-02','rating':'7','memo':'keep','tags':['tag'],'photo':''}],'collection':[],'live':[{'entryId':'live-old','title':'Existing Live','date':'2024-02-03','venue':'Tokyo','rating':'8'}]}
class QuietHandler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
 def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
BASE=f'http://127.0.0.1:{server.server_port}'
rows=[{'id':f'work-{i}','title':f'Work {i:03}','primary-type':['Single','EP','Album'][i%3],'first-release-date':f'{1900+i}-01-02','artist-credit':[{'name':'細野晴臣','joinphrase':''}]} for i in range(145)]
rows[101]=rows[0] # duplicated raw record must not shift API offsets
errors=[];calls=[];fail_next=True
def mock(route):
 u=urllib.parse.urlparse(route.request.url);q=urllib.parse.parse_qs(u.query);calls.append(route.request.url)
 if '/artist/' in u.path:
  query=q.get('query',[''])[0].lower();data={'artists':[]}
  if 'ambiguous' in query:route.fulfill(json={'artists':[{'id':'choice-a','name':'Ambiguous One','aliases':[],'score':90},{'id':'choice-b','name':'Ambiguous Two','aliases':[],'score':100}]});return
  for name in ['大比良瑞希','大比良']:
   if name in query:route.fulfill(json=MODES[name]);return
  for name in ARTISTS:
   if name.lower() in query:data=ARTISTS[name];break
  route.fulfill(json=data);return
 if q.get('artist'):
  assert q.get('inc')==['artist-credits'];off=int(q.get('offset',['0'])[0]);route.fulfill(json={'release-group-count':len(rows),'release-groups':rows[off:off+100]});return
 if '/release-group/' in u.path and not q.get('query'):
  rid=u.path.rsplit('/',1)[-1]
  if rid=='repair':route.fulfill(json={'id':rid,'title':'Repair','first-release-date':'2020-03','artist-credit':[{'artist':{'name':'Recovered Artist'}}]})
  else:route.fulfill(json={'id':rid,'artist-credit':[]})
  return
 query=q.get('query',[''])[0]
 for title in ['Punisher','Hard Life','MMA nonexistent qzxvkwp 0321']:
  if title in query:route.fulfill(json=MODES[title]);return
 if 'failure' in query:route.fulfill(status=503,json={});return
 if 'missing' in query or 'repair' in query:
  rid='missing' if 'missing' in query else 'repair';route.fulfill(json={'count':1,'release-groups':[{'id':rid,'title':rid.title(),'first-release-date':'2020-03','primary-type':'Album'}]});return
 off=int(q.get('offset',['0'])[0]);
 if 'retry' in query and off==100 and fail_next:route.fulfill(status=503,json={});return
 records=[{'id':f'title-{i}','title':f'Title {i:03}','primary-type':'Album','artist-credit':[{'name':'Title Artist'}]} for i in range(135)]
 route.fulfill(json={'count':135,'release-groups':records[off:off+100]})

def search(page,q,count=30):
 page.locator('#query').fill(q);page.locator('#search-btn').click()
 try:expect(page.locator('#results .result')).to_have_count(count,timeout=30000)
 except AssertionError as e:raise AssertionError(f'{q}: {page.locator("#status").text_content()}; JS errors={errors}') from e
 expect(page.locator('#status')).to_contain_text('追加' if page.locator('#ui-language').input_value()=='ja' else 'Select',timeout=30000)
def stored(page):return page.evaluate('(key)=>JSON.parse(localStorage.getItem(key))',KEY)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':390,'height':844},device_scale_factor=3,is_mobile=True,has_touch=True,locale='ja-JP')
 context.route('https://musicbrainz.org/**',mock);context.route('https://coverartarchive.org/**',lambda r:r.abort())
 # Accelerate retry/spacing waits, preserving the 20s request-abort timeout.
 context.add_init_script('''const nativeTimeout=window.setTimeout;window.setTimeout=(fn,ms,...args)=>nativeTimeout(fn,ms>=1000&&ms<20000?Math.min(ms,15):ms,...args);''')
 page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 print('Loading MMA',flush=True);page.goto(BASE);print('Loaded MMA',flush=True);page.evaluate('([key,seed])=>localStorage.setItem(key,JSON.stringify(seed))',[KEY,SEED]);page.reload()
 assert stored(page)==SEED
 expect(page.locator('[data-search-mode=artist]')).to_have_attribute('aria-pressed','true')
 assert page.locator('#query').get_attribute('placeholder') is None
 assert page.locator('#search-modes').evaluate('(el)=>el.previousElementSibling.contains(document.getElementById("search-title"))&&el.nextElementSibling.id==="search-form"')
 for name in ['大比良瑞希','大比良']:search(page,name)
 page.locator('#query').fill('ambiguous');page.locator('#search-btn').click();expect(page.locator('#artist-candidates button')).to_have_count(2)
 expect(page.locator('#results .result')).to_have_count(0);page.locator('#artist-candidates button').first.click();expect(page.locator('#results .result')).to_have_count(30)
 page.locator('#query').fill('keep this input');before=len(calls);page.locator('[data-search-mode=title]').click()
 expect(page.locator('#query')).to_have_value('keep this input');expect(page.locator('#results .result')).to_have_count(0);expect(page.locator('#artist-candidates')).to_have_class('search-candidates hidden');page.wait_for_timeout(50);assert len(calls)==before
 for title,name in [('Punisher','Phoebe Bridgers'),('Hard Life','The Tubs')]:
  before=len(calls);search(page,title);assert name in page.locator('#results').inner_text();assert all('/artist/' not in call for call in calls[before:])
  assert page.locator('#query').get_attribute('placeholder') is None
 page.locator('#query').fill('MMA nonexistent qzxvkwp 0321');page.locator('#search-btn').click();expect(page.locator('#status')).to_contain_text('作品が見つかりませんでした');expect(page.locator('#results .result')).to_have_count(0)
 page.screenshot(path='/tmp/mma-v0321-ja.png',full_page=True)
 page.locator('[data-search-mode=artist]').click()
 print('PASS modes, short prefix, candidate choice, input preservation, actual album fixtures and nonexistent title')
 for name in ARTISTS:
  print('Searching',name,flush=True)
  search(page,name)
  expected='細野晴臣' # the catalog is deliberately synthetic for both fixture artists
  assert expected in page.locator('#results').inner_text()
  assert 'Unknown Artist' not in page.locator('#results').inner_text()
  titles=page.locator('#results .title').all_text_contents();assert titles[0]=='Work 143'
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 print('PASS actual artist fixtures, same artist IDs, whole-catalog sorting, 390px width')
 for count in [60,90,120,144]:page.locator('#more-results').click();expect(page.locator('#results .result')).to_have_count(count)
 assert len(set(page.locator('#results .title').all_text_contents()))==144
 assert page.locator('#more-results').is_hidden()
 page.locator('#results .result button').first.click();expect(page.locator('#modal')).to_have_class('modal open')
 assert page.locator('#manual-artist').input_value()=='細野晴臣';assert page.locator('#release-edit').input_value()=='2043-01-02'
 page.locator('#save').click();expect(page.locator('#modal')).not_to_have_class('modal open')
 saved=stored(page);assert saved['listening'][0]['artist']=='細野晴臣';assert saved['listening'][1]==SEED['listening'][0]
 page.locator('[data-section="collection"]').click();page.locator('#ui-language').select_option('en');search(page,'Haruomi Hosono')
 page.locator('#results .result button').first.click();expect(page.locator('#modal')).to_have_class('modal open');assert page.locator('#manual-title').input_value()=='Work 143'
 page.locator('#save').click();expect(page.locator('#modal')).not_to_have_class('modal open');assert stored(page)['collection'][0]['release']=='2043-01-02'
 print('PASS Listening/Collection saves, metadata/date inheritance, Japanese/English, existing data intact')
 page.locator('[data-search-mode=title]').click();search(page,'missing',1);page.locator('#results button').click();expect(page.locator('#modal')).to_have_class('modal open');assert page.locator('#manual-artist').input_value()==''
 dialogs=[];page.on('dialog',lambda d:(dialogs.append(d.message),d.accept()))
 page.locator('#save').click();assert dialogs;assert len(stored(page)['collection'])==1
 page.locator('#manual-artist').fill('Manual Artist');page.locator('#save').click();expect(page.locator('#modal')).not_to_have_class('modal open');assert stored(page)['collection'][0]['artist']=='Manual Artist'
 search(page,'repair',1);page.locator('#results button').click();expect(page.locator('#modal')).to_have_class('modal open');assert page.locator('#manual-artist').input_value()=='Recovered Artist';page.locator('#close').click()
 search(page,'title fallback');
 for count in [60,90,120,135]:page.locator('#more-results').click();expect(page.locator('#results .result')).to_have_count(count,timeout=10000)
 assert page.locator('#more-results').is_hidden();assert len(set(page.locator('#results .title').all_text_contents()))==135
 print('PASS missing-credit guard/manual correction, extra metadata lookup, title mode and 30-item pagination')
 search(page,'retry-page')
 for count in [60,90]:page.locator('#more-results').click();expect(page.locator('#results .result')).to_have_count(count)
 page.locator('#more-results').click();expect(page.locator('#status')).to_contain_text('Search failed',timeout=10000);expect(page.locator('#results .result')).to_have_count(90)
 fail_next=False;page.locator('#more-results').click();expect(page.locator('#results .result')).to_have_count(120,timeout=10000)
 assert len(set(page.locator('#results .title').all_text_contents()))==120
 print('PASS failed next page preserves offset/results and can retry without duplicates')
 page.locator('#query').fill('failure');page.locator('#search-btn').click();expect(page.locator('#status')).to_contain_text('Search failed',timeout=15000)
 assert page.locator('#search-btn').is_enabled();page.locator('[data-search-mode=artist]').click();search(page,'Number Girl')
 # Hold one artist request in the browser before submitting a newer query.
 page.evaluate('''()=>{const fetch=window.fetch;window.fetch=async(...args)=>{if(String(args[0]).includes('artist/')&&String(args[0]).includes('old'))await new Promise(r=>{window.releaseOld=r});return fetch(...args)}}''')
 page.locator('#query').fill('old-query');page.locator('#search-btn').click();page.wait_for_function('window.releaseOld!==undefined')
 page.locator('[data-search-mode=title]').click();expect(page.locator('#query')).to_have_value('old-query');page.locator('#query').fill('new-title');page.locator('#search-btn').click();page.evaluate('window.releaseOld()')
 expect(page.locator('#results .title').first).to_have_text('Title 000',timeout=10000)
 # Tab changes and clearing invalidate queued and in-flight results.
 page.locator('[data-search-mode=artist]').click();page.locator('#query').fill('細野晴臣');page.locator('#search-btn').click();page.locator('[data-section="live"]').click();page.wait_for_timeout(150);expect(page.locator('#results .result')).to_have_count(0)
 assert stored(page)['live']==SEED['live']
 page.locator('[data-section="listening"]').click();page.locator('#manual-add-trigger').click();expect(page.locator('#manual-artist')).to_have_value('');page.locator('#close').click()
 page.screenshot(path='/tmp/mma-v0321-en.png',full_page=True)
 assert not errors,errors
 print('PASS final API failure/re-search, stale-result race, tab reset, manual entry, no page errors')
 # Save actual response titles in both archives and check the exact artist credits.
 for archive,title,artist in [('listening','Punisher','Phoebe Bridgers'),('collection','Hard Life','The Tubs')]:
  page.locator(f'[data-section="{archive}"]').click();page.locator('[data-search-mode=title]').click();search(page,title)
  page.locator('#results .result').filter(has_text=artist).first.locator('button').click();expect(page.locator('#modal')).to_have_class('modal open')
  expect(page.locator('#manual-artist')).to_have_value(artist);expect(page.locator('#manual-title')).to_have_value(title)
  release=page.locator('#release-edit').input_value();page.locator('#save').click();expect(page.locator('#modal')).not_to_have_class('modal open')
  saved=stored(page)[archive][0];assert saved['artist']==artist and saved['title']==title and saved['release']==release
 assert SEED['listening'][0] in stored(page)['listening'];assert stored(page)['live']==SEED['live']
 print('PASS Punisher/Hard Life from API fixtures save correct artists and release dates in Listening/Collection')
 # Lab shares the same core, renders credits, and survives switching modes.
 page.goto(BASE+'/search-test/');page.locator('#q').fill('細野晴臣');page.locator('#submit').click();expect(page.locator('#results .result')).to_have_count(30,timeout=15000)
 assert '細野晴臣' in page.locator('#results .meta').first.inner_text();page.locator('#loadMore').click();expect(page.locator('#results .result')).to_have_count(60)
 page.locator('#mode button').first.click();expect(page.locator('#results .title').first).to_have_text('Title 000',timeout=10000)
 assert not errors,errors
 print('PASS Search Lab shared core, artist credits, pagination and title-mode switch')
 browser.close()
server.shutdown()
