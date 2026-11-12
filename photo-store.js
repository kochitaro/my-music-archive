/* Prototype: immutable photo copies. References are published only after readback.
 * Deliberately no GC: failed attempts, old snapshots and rollback keep their bytes.
 */
(()=>{'use strict';
 const areas=['listening','collection','live'];
 class PhotoError extends Error {}
 function open(){return new Promise((resolve,reject)=>{
  const request=indexedDB.open('mla-photos-v1',1);
  request.onupgradeneeded=()=>request.result.createObjectStore('photos');
  request.onerror=()=>reject(new PhotoError('Photo storage unavailable'));
  request.onblocked=()=>reject(new PhotoError('Photo storage blocked'));
  request.onsuccess=()=>{const db=request.result;db.onversionchange=()=>db.close();resolve(db)};
 })}
 async function access(mode,action){const db=await open();try{return await new Promise((resolve,reject)=>{
  const tx=db.transaction('photos',mode);let result;
  tx.oncomplete=()=>resolve(result);tx.onerror=tx.onabort=()=>reject(new PhotoError('Photo storage failed'));
  try{action(tx.objectStore('photos'),v=>result=v)}catch(e){tx.abort();reject(new PhotoError('Photo storage failed'))}
 })}finally{db.close()}}
 const get=id=>access('readonly',(s,done)=>{const r=s.get(id);r.onsuccess=()=>done(r.result)});
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
 async function unpack(archive){
  const out=structuredClone(archive);delete out.photoStorage;delete out.legacyStamp;
  for(const area of areas)for(const r of out[area])if(Object.hasOwn(r,'photoId')){
   if(typeof r.photoId!=='string'||r.photo)throw new PhotoError('Invalid photo reference');
   const value=await get(r.photoId);
   if(typeof value!=='string'||!value.startsWith('data:image/')||await idFor(value)!==r.photoId)throw new PhotoError('Missing or damaged photo: '+r.entryId);
   r.photo=value;delete r.photoId;
  }
  return out;
 }
 globalThis.MLAPhotos=Object.freeze({pack,unpack,PhotoError,idFor});
})();
