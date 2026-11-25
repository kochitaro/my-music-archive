/* Prototype: immutable photo copies. References are published only after readback.
 * Deliberately no GC: failed attempts, old snapshots and rollback keep their bytes.
 */
(()=>{'use strict';
 const areas=['listening','collection','live'];
 class PhotoError extends Error {}
 function open(readOnly=false){return new Promise((resolve,reject)=>{
  const request=indexedDB.open('mla-photos-v1',1);
  request.onupgradeneeded=()=>{if(readOnly)request.transaction.abort();else request.result.createObjectStore('photos')};
  request.onerror=()=>reject(new PhotoError('Photo storage unavailable'));
  request.onblocked=()=>reject(new PhotoError('Photo storage blocked'));
  request.onsuccess=()=>{const db=request.result;db.onversionchange=()=>db.close();resolve(db)};
 })}
 async function access(mode,action,readOnly=false){const db=await open(readOnly);try{return await new Promise((resolve,reject)=>{
  const tx=db.transaction('photos',mode);let result;
  tx.oncomplete=()=>resolve(result);tx.onerror=tx.onabort=()=>reject(new PhotoError('Photo storage failed'));
  try{action(tx.objectStore('photos'),v=>result=v)}catch(e){tx.abort();reject(new PhotoError('Photo storage failed'))}
 })}finally{db.close()}}
 const get=(id,readOnly=false)=>access('readonly',(s,done)=>{const r=s.get(id);r.onsuccess=()=>done(r.result)},readOnly);
 async function idFor(value){const bytes=new TextEncoder().encode(value);return 'sha256-'+Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('')}
 async function copy(value){
  const id=await idFor(value),existing=await get(id);
  if(existing===undefined)await access('readwrite',s=>{const r=s.get(id);r.onsuccess=()=>{try{if(r.result===undefined)s.add(value,id)}catch(e){s.transaction.abort()}}});
  if(await get(id)!==value)throw new PhotoError('Photo readback mismatch');
  return id;
 }
 async function pack(archive){
  const out=structuredClone(archive);
  for(const area of areas)for(const r of out[area]){
   if(r.photoId)throw new PhotoError('Portable JSON must include photo data');
   if(typeof r.photo==='string'&&r.photo.startsWith('data:image/')){r.photoId=await copy(r.photo);delete r.photo}
  }
  out.photoStorage=1;return out;
 }
 async function unpack(archive,readOnly=false){
  const out=structuredClone(archive);delete out.photoStorage;delete out.legacyStamp;delete out.generation;delete out.importedLegacy;
  for(const area of areas)for(const r of out[area])if(Object.hasOwn(r,'photoId')){
   if(typeof r.photoId!=='string'||r.photo)throw new PhotoError('Invalid photo reference');
   const value=await get(r.photoId,readOnly);
   if(typeof value!=='string'||!value.startsWith('data:image/')||await idFor(value)!==r.photoId)throw new PhotoError('Missing or damaged photo: '+r.entryId);
   r.photo=value;delete r.photoId;
  }
  return out;
 }
 // Restore preflight only: never prevent an existing damaged source from being exported.
 // Decode at most two distinct images at once, without re-encoding their bytes.
 async function validateRestore(archive){
  const unique=new Map();
  for(const area of areas)for(const r of archive[area]){
   if(r.photo==null||r.photo==='')continue;
   const path=area+' / '+r.entryId;
   if(typeof r.photo!=='string'||!/^data:image\/[^;,]+(?:;[^,]*)?,[\s\S]+$/i.test(r.photo))throw new PhotoError(path+': 埋め込み画像が必要です / Embedded image required');
   if(!unique.has(r.photo))unique.set(r.photo,path);
  }
  const entries=unique.entries();let failure;
  async function worker(){for(const [value,path] of entries){
   if(failure)return;
   try{await new Promise((resolve,reject)=>{
    const image=new Image();let settled=false;
    const finish=ok=>{if(settled)return;settled=true;clearTimeout(timer);image.onload=image.onerror=null;image.removeAttribute('src');ok?resolve():reject(new PhotoError(path+': 写真を解読できません（非対応形式・破損・時間切れ） / Photo could not be decoded (unsupported, damaged or timed out)'))};
    const timer=setTimeout(()=>finish(false),15000);
    image.onload=()=>finish(image.naturalWidth>0&&image.naturalHeight>0);image.onerror=()=>finish(false);image.src=value;
   })}catch(e){failure=e;return}
  }}
  await Promise.all([worker(),worker()]);if(failure)throw failure;
 }
 globalThis.MLAPhotos=Object.freeze({pack,unpack,PhotoError,idFor,validateRestore});
})();
