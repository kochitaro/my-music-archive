"""Reproduce the DP-05 lost update on the exact PR-A base (synthetic data only)."""
import json, os, subprocess, threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
from ui_v0322 import KEY, QuietHandler
from data_preservation import seed_data

html=subprocess.check_output(['git','show','6b52d1bc36c13c350165d3a44b92d350c5370628:index.html'],text=True)
html=html.replace("setSection('listening');showStorageState();","window.beforeSave=saveDB;setSection('listening');showStorageState();")
server=ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('MMA_CHROMIUM','/usr/bin/chromium'),args=['--no-sandbox'])
    ctx=browser.new_context();ctx.route(base+'/',lambda r:r.fulfill(body=html,content_type='text/html'));ctx.route('https://**/*',lambda r:r.abort())
    a=ctx.new_page();b=ctx.new_page();a.goto(base)
    seed=seed_data();a.evaluate('([k,v])=>localStorage.setItem(k,v)',[KEY,json.dumps(seed)]);a.reload();b.goto(base)
    first=seed_data();first['listening'][0]['memo']='Tab A committed'
    second=seed_data();second['collection'][0]['memo']='Tab B stale'
    assert a.evaluate('(v)=>beforeSave(v)',first)
    assert b.evaluate('(v)=>beforeSave(v)',second)
    actual=json.loads(a.evaluate('(k)=>localStorage.getItem(k)',KEY))
    assert actual['listening'][0]['memo']=='Original'
    print('REPRODUCED on 6b52d1b: Tab B reports success and silently loses Tab A Listening change while saving Collection.')
    browser.close()
server.shutdown()
