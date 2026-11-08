const {test}=require('node:test');
const assert=require('node:assert/strict');
const {aggregate,pie}=require('../insights.js');
for(const area of ['listening','collection'])test(area+' labels count per record and retain display order/spelling',()=>{
 const records=[{label:' 4AD， Warp Records, 4ad, , '},{label:'4ad'},{label:null},{},{label:' , ， '}];
 const before=JSON.stringify(records);
 const stats=aggregate(records,area);
 assert.deepEqual(stats.categories.label,[{name:'4AD',count:2},{name:'Warp Records',count:1}]);
 assert.equal(stats.total,5);
 assert.equal(JSON.stringify(records),before);
 assert.equal(stats.categories.label.reduce((n,x)=>n+x.count,0),3);
});
test('label pie top ten/other and ranking retain all memberships',()=>{
 const records=Array.from({length:22},(_,i)=>({label:'Shared, Label '+i+', SHARED'}));
 const entries=aggregate(records,'collection').categories.label;
 assert.equal(entries.length,23);
 assert.equal(entries[0].count,22);
 const slices=pie(entries);
 assert.equal(slices.length,11);
 assert.equal(slices.at(-1).other,true);
 assert.equal(slices.reduce((n,x)=>n+x.count,0),44);
});
