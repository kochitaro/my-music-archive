/* Review prototype: file readback receipts are session-local; deletion intent is durable.
 * No photo GC. All record publication/deletion shares the existing main save lock.
 */
(()=>{'use strict';
 globalThis.MLALifecycle=({key,legacyKeys,lockName,validate,stable,photos})=>{
  const receipts=new Map();
  const fail=message=>{throw Error(message)};
  const raws=()=>[localStorage.getItem(key),...legacyKeys.map(k=>localStorage.getItem(k))];
  const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  async function journal(value,write=false){
   const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('mla-photo-maintenance-v1',1);r.onupgradeneeded=()=>r.result.createObjectStore('state');r.onerror=()=>reject(r.error);r.onblocked=()=>reject(Error('Maintenance storage blocked'));r.onsuccess=()=>resolve(r.result)});
   try{return await new Promise((resolve,reject)=>{const tx=db.transaction('state',write?'readwrite':'readonly');let result;tx.oncomplete=()=>resolve(result);tx.onerror=tx.onabort=()=>reject(Error('Maintenance storage failed'));const store=tx.objectStore('state');if(write)store.put(value,'cleanup');else{const r=store.get('cleanup');r.onsuccess=()=>result=r.result}})}finally{db.close()}
  }
  async function portable(raw,index){
   if(raw===null)fail('この保存元はありません / Source is absent');
   const value=JSON.parse(raw);
   // v1 may lack IDs. Stable export IDs make independent file readback repeatable.
   if(index!==0&&Array.isArray(value))for(let i=0;i<value.length;i++)if(!value[i].entryId)value[i].entryId='legacy-'+await photos.idFor(raw+'#'+i);
   const result=validate(index===0?await photos.unpack(value):value);
   if(['listening','collection','live'].some(a=>result[a].some(r=>Object.hasOwn(r,'photoId'))))fail('写真本体が必要です / Photo data required');
   return result;
  }
  function validateImports(proof){
   if(!proof||proof.version!==1||!Array.isArray(proof.sources))fail('移行元の記録が不正です。旧データは保持しました / Invalid migration provenance; legacy data retained');
   const seen=new Set();
   for(const source of proof.sources){if(!source||!legacyKeys.includes(source.key)||seen.has(source.key)||!/^sha256-[0-9a-f]{64}$/.test(source.sha256))fail('移行元の記録が不正です / Invalid migration provenance');seen.add(source.key)}
   return structuredClone(proof);
  }
  async function recordImports(candidate){
   const snapshot=raws(),sources=[];
   for(let i=1;i<snapshot.length;i++)if(snapshot[i]!==null){
    let equivalent=false;
    try{equivalent=stable(await portable(snapshot[i],i))===stable(candidate)}catch(e){/* Unreadable unrelated legacy keys are retained. */}
    if(equivalent)sources.push({key:legacyKeys[i-1],sha256:await photos.idFor(snapshot[i])});
   }
   check(snapshot);return {version:1,sources};
  }
  async function importsFor(candidate,previousRaw,reset=false){
   if(reset||previousRaw===null)return recordImports(candidate);
   const previous=JSON.parse(previousRaw);
   if(Object.hasOwn(previous,'importedLegacy'))return validateImports(previous.importedLegacy);
   // Older prototypes have no historical receipt. Establish equivalence BEFORE editing,
   // never by assuming that their combined legacyStamp proves an import took place.
   return recordImports(await portable(previousRaw,0));
  }
  async function guard(snapshot=raws()){
   if(snapshot[0]===null)return true;
   const state=await journal();
   // Intent is published BEFORE removal. Incomplete deletion fails closed on reload.
   if(state?.raw===snapshot[0])return same(state.after,snapshot.slice(1));
   return JSON.parse(snapshot[0]).legacyStamp===await photos.idFor(JSON.stringify(snapshot.slice(1)));
  }
  async function exclusive(action){
   if(!isSecureContext||!navigator.locks?.request)fail('安全な保存ロックを利用できません / Safe save lock unavailable');
   return navigator.locks.request(lockName,{ifAvailable:true},async lock=>{if(!lock)fail('別タブが保存中です。入力を残して再試行してください / Save lock busy');return action()});
  }
  function check(snapshot){if(!same(raws(),snapshot))fail('保存元が更新されました。両方を退避・読み戻し確認してください / Sources changed; export and verify both branches again')}
  function needReceipts(snapshot){snapshot.forEach((raw,i)=>{if(raw!==null&&receipts.get(i)!==raw)fail('新旧すべてのJSONを保存し、ファイルから読み戻して確認してください / Export and read back every branch JSON first')})}
  async function verify(fileText){
   const value=validate(JSON.parse(fileText));
   if(['listening','collection','live'].some(a=>value[a].some(r=>Object.hasOwn(r,'photoId'))))fail('写真IDのみのファイルは使用できません / Embedded photo data required');
   const snapshot=raws(),matched=[];
   for(let i=0;i<snapshot.length;i++)if(snapshot[i]!==null&&stable(value)===stable(await portable(snapshot[i],i)))matched.push(i);
   check(snapshot);
   if(!matched.length)fail('現在の保存元と一致しません。最新JSONを書き出してください / File does not match a current branch');
   for(const i of matched)receipts.set(i,snapshot[i]);return matched;
  }
  async function exportBranch(index){const snapshot=raws();const data=await portable(snapshot[index],index);check(snapshot);return data}
  async function cleanup(loadedRaw){return exclusive(async()=>{
   const snapshot=raws();
   if(!snapshot[0]||loadedRaw!==snapshot[0])fail('移行・保存後に再読み込みし、記録と写真を確認してください / Reload to verify saved records and photos first');
   if(!await guard(snapshot))fail('新旧の分岐を復旧してから整理してください / Resolve branch conflict before cleanup');
   needReceipts(snapshot);
   const current=await portable(snapshot[0],0),stored=JSON.parse(snapshot[0]),remove=[];
   const proof=Object.hasOwn(stored,'importedLegacy')?validateImports(stored.importedLegacy):null;
   for(let i=1;i<snapshot.length;i++)if(snapshot[i]!==null){
    // Current records may have been added, edited or deliberately deleted since import.
    // Only the imported source's exact contents, and current backup/readback, matter.
    const source=proof?.sources.find(s=>s.key===legacyKeys[i-1]);
    const imported=proof?source&&source.sha256===await photos.idFor(snapshot[i]):stable(await portable(snapshot[i],i))===stable(current);
    if(imported)remove.push(i);
   }
   if(!remove.length)fail('移行元の記録と一致する旧キーがありません。旧データは保持しました / No unchanged imported legacy key; retained');
   const after=snapshot.slice(1);for(const i of remove)after[i-1]=null;
   check(snapshot);
   await journal({raw:snapshot[0],after},true);
   check(snapshot); // Journal write awaited: legacy tabs may have updated meanwhile.
   for(const i of remove){if(localStorage.getItem(legacyKeys[i-1])!==snapshot[i])fail('旧データが変更されました / Legacy source changed');localStorage.removeItem(legacyKeys[i-1])}
   receipts.clear();return remove;
  })}
  async function recover(value){
   const candidate=validate(value);
   return exclusive(async()=>{
    const snapshot=raws();needReceipts(snapshot);
    const packed=await photos.pack(candidate),verified=validate(await photos.unpack(packed));
    if(stable(candidate)!==stable(verified))fail('復元の読み戻し照合に失敗しました / Restore readback mismatch');
    packed.importedLegacy=await recordImports(candidate);
    packed.legacyStamp=await photos.idFor(JSON.stringify(snapshot.slice(1)));
    packed.generation=crypto.randomUUID();check(snapshot);needReceipts(snapshot);
    const raw=JSON.stringify(packed);localStorage.setItem(key,raw);receipts.clear();
    return {raw,data:candidate};
   });
  }
  return Object.freeze({guard,verify,cleanup,recover,exportBranch,importsFor,invalidate:()=>receipts.clear(),raws});
 };
})();
