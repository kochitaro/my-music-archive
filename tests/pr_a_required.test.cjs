// Required-field policy and executable historical producer evidence.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),cp=require('node:child_process');
const html=fs.readFileSync(process.env.MLA_TEST_HTML||'index.html','utf8');
const start=html.indexOf('function migrate('),end=html.indexOf('// Set the initial language',start);
function migrate(value){const ctx={newId:()=> 'generated'};vm.createContext(ctx);vm.runInContext(html.slice(start,end)+';this.run=migrate',ctx);return ctx.run(value)}
const cases=[['missing',undefined],['null',null],['empty',''],['whitespace',' \t '],['number',7],['boolean',false],['array',[]],['object',{}]];
for(const area of ['listening','collection','live'])for(const field of ['title','artist'])for(const [name,value] of cases)test(`${area}.${field}: ${name}`,()=>{
 const record={entryId:'row',id:'',title:'Title',...(area==='live'?{}:{artist:'Artist'})};
 if(value===undefined)delete record[field];else record[field]=value;
 const db={version:3,listening:[],collection:[],live:[],unknown:{keep:true}};db[area]=[record];
 const before=JSON.stringify(db);
 const required=field==='title'||area!=='live';
 const rejected=required&&(typeof value!=='string'||(area==='live'&&!value.trim()));
 if(rejected)assert.throws(()=>migrate(db),e=>e.message.includes(area+'[1].'+field));else assert.equal(JSON.stringify(migrate(db)),before);
 assert.equal(JSON.stringify(db),before);
});
for(const field of ['title','artist'])for(const [name,value] of cases)test(`legacy.${field}: ${name}`,()=>{
 const record={id:'work',title:'Title',artist:'Artist',entryId:'keep'};if(value===undefined)delete record[field];else record[field]=value;
 if(typeof value!=='string')assert.throws(()=>migrate([record]));else assert.equal(migrate([record]).listening[0][field],value);
});
function history(sha){return cp.execFileSync('git',['show',sha+':index.html'],{encoding:'utf8'})}
test('historical v3 direct album producer preserves empty title and whitespace credits',()=>{
 const source=history('a0e35db');const lines=source.split('\n');
 const ctx={db:{listening:[],collection:[]},section:'listening',newId:()=> 'row',saveDB:()=>true,clearSearch(){},render(){},status(){}};
 vm.createContext(ctx);vm.runInContext(lines.find(x=>x.startsWith('function artist('))+lines.find(x=>x.startsWith('function addAlbum(')),ctx);
 ctx.addAlbum({id:'work',title:'','artist-credit':[{name:'  '}]});
 assert.equal(ctx.db.listening[0].title,'');assert.equal(ctx.db.listening[0].artist,'  ');
 assert.equal(migrate({...ctx.db,version:3,live:[]}).listening[0].title,'');
});
test('official legacy import saved empty artist and whitespace title',async()=>{
 const source=history('32946ca');const a=source.indexOf("$('import-json').onchange=")+"$('import-json').onchange=".length;
 const b=source.indexOf(';render()})();',a);assert.ok(b>a);
 const ctx={library:[],confirm:()=>true,store:()=>{ctx.saved=JSON.stringify(ctx.library)},render:()=>{},alert:message=>{throw Error(message)}};vm.createContext(ctx);
 vm.runInContext('this.restore='+source.slice(a,b),ctx);
 await ctx.restore({target:{files:[{text:async()=>JSON.stringify([{id:'work',title:' ',artist:''}])}]}});
 assert.equal(JSON.parse(ctx.saved)[0].artist,'');assert.equal(ctx.library[0].artist,'');assert.equal(ctx.library[0].title,' ');
 const migrated=migrate(ctx.library);assert.equal(migrated.listening[0].artist,'');assert.equal(migrated.listening[0].title,' ');
});
