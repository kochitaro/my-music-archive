"""Meaningful positive/negative checks for comparing the final iPhone uploads."""
import copy, importlib.util, json, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compare',ROOT/'tools/compare_safari_json.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
expected=json.loads((ROOT/'docs/safari-cbce1e1/fixtures/expected-final.json').read_text())
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp)/'returned.json'
 def check(value,want,label):
  p.write_text(json.dumps(value,ensure_ascii=False));r=module.compare(p,expected);assert r['match'] is want,(label,r['differences']);print('PASS',label)
 check(expected,True,'exact final records and distinct synthetic photos')
 hashes=[x['sha256'] for x in module.compare(p,expected)['photos']];assert len(set(hashes))==3 and None not in hashes
 for area in ['listening','collection','live']:
  bad=copy.deepcopy(expected);bad[area][0].pop('photo');check(bad,False,area+' missing photo rejected')
  bad=copy.deepcopy(expected);bad[area][0]['photo']=expected['live' if area!='live' else 'listening'][0]['photo'];check(bad,False,area+' swapped photo rejected')
 bad=copy.deepcopy(expected);bad['listening'][0]['memo']='Safari編集1';check(bad,False,'missing post-reload save rejected')
 bad=copy.deepcopy(expected);bad['collection']=[];check(bad,False,'missing record rejected')
 bad=copy.deepcopy(expected);bad['live'][0]['unexpected']='x';check(bad,False,'extra fields rejected')
 print('PASS 10 comparison cases; all three image byte hashes are distinct')
