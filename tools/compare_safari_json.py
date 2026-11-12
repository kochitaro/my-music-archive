"""Codex compares the two final iPhone JSON uploads; exits nonzero on any mismatch."""
import argparse, base64, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'docs/safari-cbce1e1/fixtures/expected-final.json'

def compare(path,expected):
 value=json.loads(Path(path).read_text());differences=[];photos=[]
 def visit(a,b,p):
  if type(a)!=type(b):differences.append(p+': type differs');return
  if isinstance(a,dict):
   if a.keys()!=b.keys():differences.append(p+': fields differ')
   for k in a.keys()&b.keys():visit(a[k],b[k],p+'.'+k)
  elif isinstance(a,list):
   if len(a)!=len(b):differences.append(p+': count differs')
   for i,(x,y) in enumerate(zip(a,b)):visit(x,y,f'{p}[{i}]')
  elif a!=b:differences.append(p+': value differs')
 visit(value,expected,'archive')
 for area in ['listening','collection','live']:
  rows=value.get(area,[])
  if isinstance(rows,list):
   for r in rows:
    if not isinstance(r,dict):continue
    photo=r.get('photo','')
    try:digest=hashlib.sha256(base64.b64decode(photo.split(',',1)[1],validate=True)).hexdigest()
    except Exception:digest=None
    photos.append(dict(area=area,entryId=r.get('entryId'),sha256=digest))
 return dict(file=Path(path).name,match=not differences,differences=differences,photos=photos)

def main():
 p=argparse.ArgumentParser();p.add_argument('migration_final');p.add_argument('restore_final');p.add_argument('--expected',type=Path,default=DEFAULT);p.add_argument('--report',type=Path);a=p.parse_args()
 expected=json.loads(a.expected.read_text());results=[compare(f,expected) for f in [a.migration_final,a.restore_final]]
 result=dict(allMatch=all(x['match'] for x in results),results=results)
 encoded=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
 if a.report:a.report.write_text(encoded)
 print(encoded,end='');raise SystemExit(0 if result['allMatch'] else 1)
if __name__=='__main__':main()
