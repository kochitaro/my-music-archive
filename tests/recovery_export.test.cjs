const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('recovery-export.js','utf8');

test('rescue keeps raw text independently when one source cannot be read, and preserves available photos',async()=>{
 const raw=JSON.stringify({listening:[{entryId:'ok',photoId:'good'},{entryId:'bad',photoId:'bad'}],collection:[],live:[]});
 const ctx={localStorage:{getItem(k){if(k==='blocked')throw Error('denied');return k==='new'?raw:'malformed raw'}},MLAPhotos:{async unpack(v){if(v.listening[0].photoId==='bad')throw Error('missing');return {listening:[{photo:'data:image/png;base64,exact'}]}}}};
 vm.createContext(ctx);vm.runInContext(source,ctx);
 const result=JSON.parse(JSON.stringify(await ctx.MLARescue.collect(['new','blocked','old'],{key:'blocked',raw:'startup original'})));
 assert.equal(result.sources[0].raw,raw);assert.equal(result.sources[1].error,'Source read failed');assert.equal(result.sources[2].raw,'malformed raw');
 assert.deepEqual(result.photos.good,{data:'data:image/png;base64,exact'});assert.ok(result.photos.bad.error);
 assert.deepEqual(result.captured,{key:'blocked',raw:'startup original'});assert.equal(result.sources[0].changed,false);
});

test('rescue reports concurrent source changes without writing or deleting anything',async()=>{
 let reads=0;
 const ctx={localStorage:{getItem(){return ++reads===1?'[]':'changed'}},MLAPhotos:{}};
 vm.createContext(ctx);vm.runInContext(source,ctx);
 const result=await ctx.MLARescue.collect(['old'],null);
 assert.equal(result.sources[0].raw,'[]');assert.equal(result.sources[0].changed,true);
});
