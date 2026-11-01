const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync('index.html','utf8');
const start=html.indexOf('function migrate('),end=html.indexOf('// Set the initial language',start);
function migrate(v){const ctx={crypto:{randomUUID:()=> 'generated'},newId:()=> 'generated'};vm.createContext(ctx);vm.runInContext(html.slice(start,end)+';this.run=migrate',ctx);return ctx.run(v)}
const db=()=>({version:3,listening:[],collection:[],live:[]});
for(const value of [null,{}, {version:2,listening:[]},{version:3,listening:[]}, {...db(),live:null},{...db(),listening:[null]},{...db(),listening:[{entryId:'a',date:123}]},{...db(),live:[{entryId:'a',artists:'A'}]},{...db(),live:[{entryId:'a',rating:'NaN'}]},{...db(),live:[{entryId:'a',rating:11}]},{...db(),live:[{}]},{...db(),live:[{entryId:'a'},{entryId:'a'}]}])test('reject '+JSON.stringify(value),()=>assert.throws(()=>migrate(value)));
test('legacy invalid row refuses whole array',()=>assert.throws(()=>migrate([{id:'a',title:'A'},null])));
test('v3 preserves unknown root and special keys',()=>{const v=JSON.parse('{"version":3,"listening":[],"collection":[],"live":[],"extra":1,"__proto__":{"polluted":true}}');assert.equal(JSON.stringify(migrate(v)),JSON.stringify(v))});
test('legacy manual entry, order, optional values retained',()=>{const v=[{id:'',title:'Manual',tags:null,memo:null,rating:'4.25',entryId:'keep',extra:1},{id:'a',title:'A'}];const before=JSON.stringify(v);const out=migrate(v);assert.equal(out.listening.length,2);assert.equal(out.listening[0].entryId,'keep');assert.equal(out.listening[0].rating,'8.5');assert.equal(out.listening[0].tags,null);assert.equal(JSON.stringify(v),before)});

test('overflowing JSON number refuses unknown property conversion to null',()=>assert.throws(()=>migrate(JSON.parse('{"version":3,"listening":[],"collection":[],"live":[],"extra":1e400}'))));

test('nonempty legacy ID is preserved verbatim, including whitespace',()=>{const out=migrate([{id:'',title:'Manual',entryId:'  '}]);assert.equal(out.listening[0].entryId,'  ')});
test('v3 optional and score variants remain exact without mutating frozen source',()=>{const v=db();v.live=[{entryId:'same',artists:[],rating:'8.55'},{entryId:'other',artists:['B','A','B'],rating:null}];v.listening=[{entryId:'same',id:'',rating:0,tags:' a, a ',date:'2020/01/02'}];Object.freeze(v);const before=JSON.stringify(v);assert.equal(JSON.stringify(migrate(v)),before);assert.equal(JSON.stringify(v),before)});

test('properties only known in another area remain arbitrary JSON',()=>{const v=db();v.listening=[{entryId:'a',artists:{keep:true},price:{keep:true},venue:['keep']}];v.live=[{entryId:'a',tags:{keep:true},release:{keep:true},artist:['keep']}];assert.equal(JSON.stringify(migrate(v)),JSON.stringify(v))});
