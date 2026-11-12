/* Read-only emergency export. Never import this envelope as a version 3 backup. */
(()=>{'use strict';
 async function collect(keys,captured){
  const out={format:'mla-recovery-sources',version:1,sources:[],photos:{},captured};
  for(const key of keys){
   const source={key};out.sources.push(source);
   try{source.raw=localStorage.getItem(key)}catch(e){source.error='Source read failed';continue}
   if(source.raw===null)continue;
   try{
    const value=JSON.parse(source.raw);
    for(const area of ['listening','collection','live'])for(const r of value[area]||[]){
     if(!r?.photoId||Object.hasOwn(out.photos,r.photoId))continue;
     try{
      const data=await MLAPhotos.unpack({[area]:[r],...Object.fromEntries(['listening','collection','live'].filter(a=>a!==area).map(a=>[a,[]]))});
      out.photos[r.photoId]={data:data[area][0].photo};
     }catch(e){out.photos[r.photoId]={error:'Photo unavailable or damaged'}}
    }
   }catch(e){source.error='Source parse failed; raw text retained'}
  }
  // Record concurrent changes rather than presenting a mixed read as a verified backup.
  for(const source of out.sources)try{source.changed=localStorage.getItem(source.key)!==source.raw}catch(e){source.changed=true}
  return out;
 }
 globalThis.MLARescue=Object.freeze({collect});
})();
