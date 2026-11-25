/* Unified archive persistence. No writes/deletes to legacy storage, no photo GC.
 * All asynchronous conversion/hashing is outside IDB transactions. Publication is
 * atomic across archive/photos/settings/meta, then verified before enabling writes.
 */
(()=>{'use strict';
 const NAME='mla-archive-v1',STORES=['archive','photos','settings','meta'];
 const KEYS=['my-music-archive-photos-v1','my-music-archive-pilot-v03','my-music-archive-pilot-v1','mma-ui-language','mma-ui-grid-display-v1'];
 const LOCK='mla:my-music-archive-pilot-v03:write',AREAS=['listening','collection','live'];
 class StorageError extends Error {}
 class PublicationError extends StorageError {
  constructor(cause,phase,recoveryAvailable){super(cause.message);this.name='PublicationError';this.published=true;this.phase=phase;this.recoveryAvailable=recoveryAvailable;this.cause=cause}
 }
 const fail=message=>{throw new StorageError(message)};
 globalThis.MLAArchive=({validate,stable,legacy,photos})=>{
  let ready=false,observed=null,baseline=null,onchange=()=>{};
  const receipts=new Map();
  const rawSources=()=>KEYS.map(k=>localStorage.getItem(k));
  const equal=(a,b)=>stable(a)===stable(b);
  const check=s=>{if(!equal(rawSources(),s))fail('旧保存元が変更されました / Legacy sources changed')};
  const hashes=async s=>Promise.all(s.map(v=>v===null?null:photos.idFor(v)));
  function open(recovery=false){return new Promise((resolve,reject)=>{
   let cancelled=false;const r=recovery?indexedDB.open(NAME):indexedDB.open(NAME,1);
   r.onupgradeneeded=()=>{if(cancelled||recovery){r.transaction.abort();return}for(const name of STORES)r.result.createObjectStore(name)};
   r.onblocked=()=>{cancelled=true;ready=false;reject(new StorageError('保存DBが使用中です / Archive database blocked'))};
   r.onerror=()=>reject(new StorageError('保存DBを開けません / Archive database unavailable'));
   r.onsuccess=()=>{const db=r.result;if(cancelled){db.close();return}db.onversionchange=()=>{ready=false;db.close();onchange()};resolve(db)};
  })}
  async function transaction(mode,action,recovery=false){const db=await open(recovery);try{return await new Promise((resolve,reject)=>{
   let result,error;const tx=db.transaction(recovery?Array.from(db.objectStoreNames):STORES,mode);
   tx.oncomplete=()=>resolve(result);tx.onerror=tx.onabort=()=>reject(error||new StorageError('保存処理が中断されました / Archive transaction failed'));
   const abort=e=>{error=e;try{tx.abort()}catch(_){};};
   try{action(tx,v=>result=v,abort)}catch(e){abort(e)}
  })}finally{db.close()}}
  const request=(tx,store,key,done,abort)=>{const r=tx.objectStore(store).get(key);r.onsuccess=()=>{try{done(r.result)}catch(e){abort(e)}}};
  // Read every component in ONE snapshot, including all referenced photos.
  async function read(key='current'){return transaction('readonly',(tx,done,abort)=>{
   const out={};let remaining=3;
   const finish=()=>{if(--remaining)return;
    if(!out.meta){if(out.archive!==undefined||out.settings!==undefined)fail('移行状態がありません / Missing archive metadata');if(key!=='current'){done(null);return}const q=tx.objectStore('photos').count();q.onsuccess=()=>{if(q.result){abort(new StorageError('移行状態がありません / Missing archive metadata'))}else done(null)};return}
    if(out.meta.schema!==1||!['pending','ready'].includes(out.meta.status)||typeof out.meta.generation!=='string'||!Array.isArray(out.meta.sources)||out.meta.sources.length!==KEYS.length||!out.settings||!out.archive)fail('保存構造が不正です / Invalid archive state');
    out.photoValues=Object.create(null);const ids=new Set();
    for(const area of AREAS){if(!Array.isArray(out.archive[area]))fail('記録構造が不正です / Invalid archive');for(const r of out.archive[area])if(Object.hasOwn(r,'photoId'))ids.add(r.photoId)}
    let left=ids.size;if(!left){done(out);return}
    for(const id of ids)request(tx,'photos',id,v=>{out.photoValues[id]=v;if(!--left)done(out)},abort);
   };
   for(const [store,name] of [['archive','archive'],['settings','settings'],['meta','meta']])request(tx,store,key,v=>{out[name]=v;finish()},abort);
  })}
  function validSettings(s){
   if(!s||!['ja','en'].includes(s.language))fail('言語設定が不正です / Invalid language setting');
   const fields=a=>a==='live'?['date','venue','artists','rating','memo']:['rating','date','release','label','genre','tags',...(a==='collection'?['format','store']:[])];
   for(const a of AREAS){const v=s.display?.[a];if(v!==null&&(!Array.isArray(v)||v.length>3||new Set(v).size!==v.length||!v.every(k=>fields(a).includes(k))))fail('表示設定が不正です / Invalid display setting')}
   return structuredClone(s);
  }
  function legacySettings(s){
   const result={language:s[3]??((navigator.language||'en').toLowerCase().startsWith('ja')?'ja':'en'),display:{listening:null,collection:null,live:[]}};
   if(s[4]!==null){const saved=JSON.parse(s[4]);if(!saved||typeof saved!=='object'||Array.isArray(saved))fail('表示設定が不正です / Invalid display setting');for(const a of AREAS)if(Object.hasOwn(saved,a))result.display[a]=saved[a]}
   return validSettings(result);
  }
  async function unpack(state){
   if(!state)fail('保存元がありません / Archive absent');
   const out=structuredClone(state.archive);
   for(const a of AREAS)for(const r of out[a])if(Object.hasOwn(r,'photoId')){
    const value=state.photoValues[r.photoId];
    if(typeof r.photoId!=='string'||Object.hasOwn(r,'photo')||typeof value!=='string'||!value.startsWith('data:image/')||await photos.idFor(value)!==r.photoId)throw new photos.PhotoError('写真が欠落・破損しています / Missing or damaged photo');
    r.photo=value;delete r.photoId;
   }
   const data=validate(out),settings=validSettings(state.settings);
   if(await photos.idFor(stable({data,settings}))!==state.meta.digest)fail('保存内容が一致しません / Archive readback mismatch');
   return {data,settings};
  }
  async function prepare(value,settings){
   const data=validate(value),packed=structuredClone(data),photoValues=new Map();
   for(const a of AREAS)for(const r of packed[a]){
    if(Object.hasOwn(r,'photoId'))throw new photos.PhotoError('写真本体が必要です / Embedded photo required');
    if(typeof r.photo==='string'&&r.photo.startsWith('data:image/')){const id=await photos.idFor(r.photo);photoValues.set(id,r.photo);delete r.photo;r.photoId=id}
   }
   return {data,packed,photoValues,settings:validSettings(settings),digest:await photos.idFor(stable({data,settings}))};
  }
  async function exclusive(action){
   if(!isSecureContext||!navigator.locks?.request)fail('安全な保存ロックを利用できません / Safe save lock unavailable');
   return navigator.locks.request(LOCK,{mode:'exclusive',ifAvailable:true},lock=>{if(!lock)fail('別タブが保存中です。入力を保持して再試行してください / Save lock busy');return action()});
  }
  async function finish(state,sources){
   const resumed=state.meta.status==='pending';
   const value=await unpack(state);check(sources);
   if(!equal(await hashes(sources),state.meta.sources))fail('新旧の保存元が分岐しています / Legacy branches diverged');
   check(sources);
   if(state.meta.status==='pending')await transaction('readwrite',(tx,done,abort)=>request(tx,'meta','current',m=>{
    check(sources);if(!equal(m,state.meta))fail('保存世代が変わりました / Archive generation changed');
    tx.objectStore('meta').put({...m,status:'ready'},'current');
   },abort));
   observed=state.meta.generation;baseline=sources;ready=true;return {...value,raw:observed,resumed,resumedRestore:resumed&&state.meta.restorePublication===true,recoveryAvailable:state.meta.restoreBackup===true};
  }
  async function publish(prepared,expected,sources,settingsRevision,allowPending=false,restoring=false){
   const meta={schema:1,status:'pending',generation:crypto.randomUUID(),sources:await hashes(sources),digest:prepared.digest};check(sources);
   await transaction('readwrite',(tx,done,abort)=>request(tx,'meta','current',m=>{
    check(sources);
    if((m?.generation??null)!==expected||m&&m.status!=='ready'&&!(allowPending&&m.status==='pending'))fail('保存世代が変わりました / Archive generation changed');
    // A separate settings generation prevents a queued settings write being lost.
    if(settingsRevision!==undefined&&(m?.settingsRevision??0)!==settingsRevision)fail('設定が更新されました / Settings changed');
    meta.settingsRevision=(m?.settingsRevision??0)+1;
    meta.restorePublication=restoring;
    // Preserve the last verified snapshot until and after readback. Failed or
    // interrupted publication must not erase the latest recoverable original.
    if(m?.status==='ready'&&(restoring||!m.restoreBackup)){
     for(const name of ['archive','settings'])request(tx,name,'current',v=>tx.objectStore(name).put(v,'previous'),abort);
     tx.objectStore('meta').put(m,'previous');
    }
    // Pin the same previous slot across edits/settings until the next explicit restore.
    meta.restoreBackup=!!m&&(m.restoreBackup===true||restoring&&m.status==='ready');
    for(const [id,value] of prepared.photoValues){const store=tx.objectStore('photos'),r=store.get(id);r.onsuccess=()=>{try{if(r.result===undefined){const add=store.add(value,id);add.onerror=()=>abort(new photos.PhotoError('写真を保存できません / Photo storage failed'))}else if(r.result!==value)throw new photos.PhotoError('写真が一致しません / Photo mismatch')}catch(e){abort(e instanceof photos.PhotoError?e:new photos.PhotoError('写真を保存できません / Photo storage failed'))}}}
    tx.objectStore('archive').put(prepared.packed,'current');tx.objectStore('settings').put(prepared.settings,'current');
    if(restoring&&m?.status==='pending'&&!meta.restoreBackup){
     // A stopped, older publication may already have a verified previous slot.
     request(tx,'meta','previous',previous=>{meta.restoreBackup=previous?.status==='ready';tx.objectStore('meta').put(meta,'current')},abort);
    }else tx.objectStore('meta').put(meta,'current');
   },abort));
   try{
   ready=false;
   const state=await read();if(state?.meta.generation!==meta.generation)fail('保存世代が変わりました / Archive generation changed');
    const result=await finish(state,sources);receipts.clear();broadcast();return {...result,resumed:false,resumedRestore:false};
   }catch(e){throw new PublicationError(e,'verification-or-finalization',meta.restoreBackup)}
  }
  async function init(){ready=false;return exclusive(async()=>{
   const sources=rawSources(),state=await read();
   if(state)return finish(state,sources);
   // Existing photo DB is read-only. Never pack into it as part of this migration.
   let data={version:3,listening:[],collection:[],live:[]};
   const index=sources.slice(0,3).findIndex(v=>v!==null);
   if(index!==-1){if(index===0&&!await legacy.guard())fail('新旧の保存元が分岐しています / Legacy branches diverged');data=await legacy.exportBranch(index)}
   const prepared=await prepare(data,legacySettings(sources));check(sources);
   return publish(prepared,null,sources);
  })}
  async function save(value,expected,{restore=false}={}){
   const data=validate(value);if(restore)await photos.validateRestore(data);return exclusive(async()=>{
    if(!ready||expected!==observed)fail('保存が停止しています / Saving stopped');
    const sources=rawSources();check(baseline);let state;try{state=await read();await unpack(state)}catch(e){ready=false;throw e}
    if(!state||state.meta.generation!==expected||state.meta.status!=='ready')fail('保存世代が変わりました / Archive generation changed');
    // Validate current photos too, even when the proposed edit deletes their references.
    await unpack(state);check(sources);
    return publish(await prepare(data,state.settings),expected,sources,state.meta.settingsRevision??0,false,restore);
   });
  }
  async function setSetting(key,value){return exclusive(async()=>{
   if(!ready)fail('保存が停止しています / Saving stopped');check(baseline);
   let state;try{state=await read();await unpack(state)}catch(e){ready=false;throw e}if(state?.meta.generation!==observed||state.meta.status!=='ready')fail('保存世代が変わりました / Archive generation changed');
   const current=await unpack(state),settings=validSettings({...current.settings,[key]:structuredClone(value)});
   // Settings use the same verified publication boundary as records.
   return publish(await prepare(current.data,settings),observed,baseline,state.meta.settingsRevision??0);
  })}
  async function exportBranch(index){
   const sources=rawSources();
   if(index!==0&&index!==4)return legacy.exportBranch(index-1);
   const key=index===4?'previous':'current';
   const state=await read(key),value=await unpack(state);check(sources);
   const after=await read(key);if(!equal(state?.meta,after?.meta))fail('保存世代が変わりました / Archive generation changed');return value.data;
  }
  // Exact current-branch receipts are session-local and invalidated by any write.
  async function branches(){const state=await read();return [state?.meta.generation??null,...rawSources().slice(0,3)]}
  async function verify(fileText){
   const value=validate(JSON.parse(fileText)),snapshot=await branches(),matched=[];
   for(let i=0;i<snapshot.length;i++)if(snapshot[i]!==null&&equal(value,await exportBranch(i)))matched.push(i);
   if(!equal(snapshot,await branches()))fail('保存元が更新されました / Sources changed');
   if(!matched.length)throw Error('File does not match a current branch');
   for(const i of matched)receipts.set(i,snapshot[i]);return matched;
  }
  async function recover(value){const data=validate(value);await photos.validateRestore(data);return exclusive(async()=>{
   const snapshot=await branches(),sources=rawSources(),state=await read();
   snapshot.forEach((v,i)=>{if(v!==null&&receipts.get(i)!==v)fail('新旧すべてのJSONを退避・読み戻し確認してください / Export and verify every branch first')});
   if(!state)fail('保存元がありません / Archive absent');
   const current=await unpack(state),prepared=await prepare(data,current.settings);
   if(!equal(snapshot,await branches()))fail('保存元が更新されました / Sources changed');
   return publish(prepared,state.meta.generation,sources,state.meta.settingsRevision??0,true,true);
  })}
  async function rescue(){
   const out={format:'mla-unified-recovery',version:1,legacy:await MLARescue.collect(KEYS,null)};
   // Raw cursor reads preserve malformed metadata and unreferenced photos as well.
   try{out.unified=await transaction('readonly',(tx,done,abort)=>{const names=Array.from(tx.objectStoreNames),all={};let left=names.length;for(const name of names){all[name]=[];const r=tx.objectStore(name).openCursor();r.onsuccess=()=>{try{const c=r.result;if(c){all[name].push({key:c.key,value:c.value});c.continue()}else if(!--left)done(all)}catch(e){abort(e)}}}},true)}catch(e){out.unifiedError=String(e.message)}
   return out;
  }
  let channel;try{channel=new BroadcastChannel(NAME);channel.onmessage=()=>{receipts.clear();onchange()}}catch(_){}
  function broadcast(){try{channel?.postMessage({generation:observed})}catch(_){}}
  async function changed(){const sources=rawSources(),state=await read();return !equal(sources,baseline)||state?.meta.generation!==observed||state?.meta.status!=='ready'}
  return Object.freeze({init,save,setSetting,exportBranch,verify,recover,rescue,changed,StorageError,
   onChange:fn=>onchange=fn,invalidate:()=>receipts.clear(),isReady:()=>ready});
 };
})();
