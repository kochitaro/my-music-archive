"""Build isolated Safari test assets from exact Git blobs, without editing either app."""
import base64, copy, hashlib, io, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs/safari-cbce1e1'
OLD='c2c719dd1bd25583402e0a2db948e168018ce34e'
NEW='cbce1e1fefd5017e8c9efa84e43a08c4c1c5041f'
MIGRATION='https://mla-safari-cbce1e1.wigglyfrost4096.chatgpt.site'
RESTORE='https://mla-safari-restore-cbce1e1.wigglyfrost4096.chatgpt.site'
FIRST='Safari編集1'
FINAL='Safari編集1・再読み込み後保存'

def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def fixture():
 data=dict(version=3,listening=[],collection=[],live=[])
 for i,(area,color,shape) in enumerate([('listening','#286acb','circle'),('collection','#e28b25','square'),('live','#238751','triangle')],1):
  im=Image.new('RGB',(160,160),'#faf8f1');d=ImageDraw.Draw(im)
  if shape=='circle':d.ellipse((20,20,140,140),fill=color)
  elif shape=='square':d.rectangle((25,25,135,135),fill=color)
  else:d.polygon([(80,16),(146,140),(14,140)],fill=color)
  d.text((71,66),str(i),fill='white',font_size=36)
  b=io.BytesIO();im.save(b,format='PNG');(DOC/'fixtures'/f'{area}.png').write_bytes(b.getvalue())
  r=dict(entryId=f'safari-cbce1e1-{area}',title=f'Safari {area.title()} {i}',date='2026-11-12',added='2026-11-12T00:00:00.000Z',rating='',memo=f'合成データ {area.title()}',photo='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode())
  if area=='live':r.update(artists=['Synthetic Trio'],venue='合成ホール')
  else:r.update(id='',artist='Synthetic Artist',release='2026',genre='Jazz',label='Synthetic',tags=[])
  if area=='collection':r.update(store='Synthetic Store',format='CD',price='0',condition='New')
  data[area]=[r]
 dump(DOC/'fixtures/mla-safari-legacy.json',data)
 final=copy.deepcopy(data);final['listening'][0]['memo']=FINAL;dump(DOC/'fixtures/expected-final.json',final)
 return data

def main():
 DOC.mkdir(parents=True,exist_ok=True);(DOC/'fixtures').mkdir(exist_ok=True);fixture()
 checks={}
 for name,has_old in [('mla-safari-cbce1e1',True),('mla-safari-restore-cbce1e1',False)]:
  dist=Path('/workspace/sites')/name/'dist';dist.mkdir(exist_ok=True)
  hashes={}
  for label,sha in ([('old',OLD),('new',NEW)] if has_old else [('new',NEW)]):
   for file in ['index.html','insights.js','insights.css','search.js']+(['photo-store.js','photo-lifecycle.js'] if label=='new' else []):
    value=subprocess.check_output(['git','show',f'{sha}:{file}'],cwd=ROOT)
    target=dist/label/file;target.parent.mkdir(exist_ok=True);target.write_bytes(value)
    hashes[f'{label}/{file}']=hashlib.sha256(value).hexdigest()
  for p in (DOC/'fixtures').iterdir():
   t=dist/'fixtures'/p.name;t.parent.mkdir(exist_ok=True);t.write_bytes(p.read_bytes())
  (dist/'index.html').write_text((DOC/'index.html').read_text())
  if (DOC/'download.html').exists():(dist/'download.html').write_bytes((DOC/'download.html').read_bytes())
  manifest=dict(legacyCommit=OLD if has_old else None,prototypeCommit=NEW,siteOrigin=MIGRATION if has_old else RESTORE,migrationOrigin=MIGRATION,restoreOrigin=RESTORE,assetsSHA256=hashes)
  dump(dist/'build.json',manifest);checks[name]=manifest
 dump(DOC/'source-manifest.json',checks)
 print(json.dumps({'assetsVerified':sum(len(v['assetsSHA256']) for v in checks.values()),'origins':[MIGRATION,RESTORE],'prototype':NEW,'legacy':OLD}))
if __name__=='__main__':main()
