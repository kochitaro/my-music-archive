/* Read-only Insights. Inputs are never mutated; UI state exists only in memory. */
(function(root){
'use strict';
const clean=v=>typeof v==='string'?v.trim():'';
const key=v=>v.toLocaleLowerCase();
const genres=v=>clean(v).split(/[,，]/);
const tags=v=>Array.isArray(v)?v.filter(x=>typeof x==='string'):clean(v).split(',');
function counts(records,values){
 const map=new Map();
 for(const record of records){
  const seen=new Set();
  for(const value of values(record)){const name=clean(value),id=key(name);if(!name||seen.has(id))continue;seen.add(id);
   if(!map.has(id))map.set(id,{name,count:0});map.get(id).count++;
  }
 }
 return [...map.values()].sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name,'en',{sensitivity:'base'})||(a.name<b.name?-1:a.name>b.name?1:0));
}
function dateParts(value){
 const match=/^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(clean(value));if(!match)return null;
 const year=Number(match[1]),month=match[2]?Number(match[2]):null,day=match[3]?Number(match[3]):null;
 if(year<1||month!==null&&(month<1||month>12))return null;
 const leap=year%4===0&&(year%100!==0||year%400===0);
 if(day!==null&&(day<1||day>[31,leap?29:28,31,30,31,30,31,31,30,31,30,31][month-1]))return null;
 return {year,month};
}
function aggregate(records,area){
 const scalar=field=>r=>[r[field]];
 const artists=counts(records,area==='live'?r=>Array.isArray(r.artists)?r.artists:[]:scalar('artist'));
 const fields=area==='live'?['venue']:['genre','tags','label',...(area==='collection'?['store','format']:[])];
 const categories=Object.fromEntries(fields.map(field=>[field,counts(records,(field==='genre'||field==='label')?r=>genres(r[field]):field==='tags'?r=>tags(r.tags):scalar(field))]));
 const months=new Map(),years=new Map(),release=new Map();
 const add=(map,k)=>map.set(k,(map.get(k)||0)+1);
 for(const record of records){const date=dateParts(record.date),rel=dateParts(record.release);
  if(date){add(years,date.year);if(date.month)add(months,date.year*12+date.month-1)}
  if(rel&&area!=='live')add(release,rel.year);
 }
 return {total:records.length,artists,categories,months,years,release};
}
function pie(entries){const result=entries.slice(0,15).map(x=>({...x}));if(entries.length>15)result.push({name:'',other:true,count:entries.slice(15).reduce((sum,x)=>sum+x.count,0)});return result}
function timeline(stats,mode,limit,now=new Date()){
 const monthly=mode==='monthly',current=monthly?now.getFullYear()*12+now.getMonth():now.getFullYear(),map=monthly?stats.months:stats.years;
 const keys=[...map.keys()].filter(k=>k<=current);
 if(!keys.length)return {rows:[],more:false};
 const earliest=Math.min(...keys),available=current-earliest+1;
 const length=Math.min(monthly?12:limit,available);
 const rows=Array.from({length},(_,i)=>{const k=current-i;return {name:monthly?String(Math.floor(k/12)).padStart(4,'0')+'-'+String(k%12+1).padStart(2,'0'):String(k),count:map.get(k)||0}});
 return {rows,more:!monthly&&length<available};
}
function scoreRanking(records,mode='release',year='',score=recordScore){
 const scored=records.map(record=>({record,score:score(record)})).filter(x=>x.score!==null);
 const years=[...new Set(scored.map(x=>dateParts(x.record[mode])?.year).filter(Boolean))].sort((a,b)=>b-a);
 const rows=scored.filter(x=>!year||dateParts(x.record[mode])?.year===Number(year)).sort((a,b)=>b.score-a.score);
 let rank=0;rows.forEach((row,i)=>{if(!i||row.score!==rows[i-1].score)rank=i+1;row.rank=rank});
 return {years,rows};
}
function recordScore(r){if(r.rating===''||r.rating===undefined||r.rating===null)return null;const n=Number(r.rating);return Number.isFinite(n)?Math.round(n*5)/10:null}

function releaseRows(stats,decades=false){const map=new Map();for(const [year,count] of stats.release){const k=decades?Math.floor(year/10)*10:year;map.set(k,(map.get(k)||0)+count)}return [...map].sort((a,b)=>b[0]-a[0]).map(([year,count])=>({name:String(year),count}))}
const states=new Map();
// Every accepted save/restore replaces db with validated data (index.html commitDB).
// Weak keys release old snapshots and prevent stale counts after those replacements.
const snapshots=new WeakMap();
const colors=['#97C4CE','#C9AE8B','#ADA0BD','#8CAA98','#BD919C','#859BB7','#B6B18B','#BA9B83','#79AAA9','#BBA9B4','#9AA9BF','#A5BA88','#C49FAD','#8D9D8A','#ABA28C'];
const otherColor='#414951';
function render(container,records,area,ja,now=new Date(),ui={}){
 let snapshot=snapshots.get(records);
 if(!snapshot||snapshot.area!==area){snapshot={area,stats:aggregate(records,area)};snapshots.set(records,snapshot)}
 const stats=snapshot.stats,t=(jp,en)=>ja?jp:en;
 const el=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n};
 const state=(id,mode,limit)=>{const k=area+':'+id;if(!states.has(k))states.set(k,{mode,limit});return states.get(k)};
 const redraw=()=>render(container,records,area,ja,now,ui);
 const button=(title,fn)=>{const b=el('button','btn alt',title);b.type='button';b.onclick=fn;return b};
 const block=(id,title)=>{const n=el('section','insight-block');n.dataset.insight=id;n.append(el('h3','',title));container.append(n);return n};
 const switches=(node,s,options,initial)=>{const group=el('div','insight-switch');group.setAttribute('role','group');group.setAttribute('aria-label',node.querySelector('h3').textContent);for(const [value,title] of options){const b=button(title,()=>{s.mode=value;s.limit=typeof initial==='function'?initial(value):initial;redraw()});b.setAttribute('aria-pressed',String(s.mode===value));group.append(b)}node.append(group)};
 const empty=node=>node.append(el('p','insight-note',t('集計できる登録データがありません。','No registered data to summarize.')));
 const bars=(node,rows,rank=false,horizontal=false)=>{if(!rows.length){empty(node);return}const max=Math.max(1,...rows.map(x=>x.count));const list=el('ol','insight-bars'+(horizontal?' insight-horizontal':''));for(const [i,row] of rows.entries()){const li=el('li','insight-bar');li.append(el('span','insight-name',(rank?(i+1)+'. ':'')+row.name),el('span','insight-count',String(row.count)));const track=el('div','insight-track'),fill=el('div','insight-fill');fill.style.width=(row.count/max*100)+'%';track.append(fill);li.append(track);list.append(li)}node.append(list)};
 const svgNode=(tag,attrs={},value)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(value!==undefined)n.textContent=value;return n};
 const columns=(node,source,monthly=false)=>{
  if(!source.length){empty(node);return}
  const rows=[...source].reverse(),max=Math.max(1,...rows.map(r=>r.count));
  const rough=max/4,power=10**Math.floor(Math.log10(rough)),step=Math.max(1,[1,2,5,10].find(n=>n*power>=rough)*power),top=Math.ceil(max/step)*step;
  // Multiple decade panels retain readable labels without horizontal scrolling; all share a scale.
  const chunk=monthly?12:8;
  for(let start=0;start<rows.length;start+=chunk){
   const part=rows.slice(start,start+chunk),width=Math.max(260,node.clientWidth||300),left=String(top).length*7+10,right=12,plot=width-left-right,height=154,dense=String(max).length>2&&part.length>6,base=height+(dense?String(max).length*7+16:40);
   const svg=svgNode('svg',{viewBox:`0 0 ${width} ${base+50}`,class:'insight-columns',role:'img','aria-label':part.map(r=>r.name+': '+r.count).join(', ')});
   for(let tick=0;tick<=top;tick+=step){const y=base-tick/top*height;svg.append(svgNode('line',{x1:left,x2:width-right,y1:y,y2:y,class:'insight-gridline'}),svgNode('text',{x:left-7,y:y+4,'text-anchor':'end',class:'insight-axis'},tick))}
   const slot=plot/part.length;
   part.forEach((r,i)=>{const x=left+slot*(i+.5),h=r.count/top*height,w=Math.min(24,slot*.58);
    svg.append(svgNode('rect',{x:x-w/2,y:base-h,width:w,height:h,rx:2,class:'insight-column'}));
    svg.append(svgNode('text',{x,y:base-h-7,'text-anchor':dense?'start':'middle',class:'insight-column-count',...(dense?{transform:`rotate(-90 ${x} ${base-h-7})`}:{})},r.count));
    const label=monthly?String(Number(r.name.slice(5))):r.name;
    svg.append(svgNode('text',{x,y:base+19,'text-anchor':'middle',class:'insight-axis'},label));
   });
   if(monthly){
    for(let first=0;first<part.length;){let end=first+1;const year=part[first].name.slice(0,4);while(end<part.length&&part[end].name.startsWith(year+'-'))end++;
     svg.append(svgNode('text',{x:left+slot*(first+end)/2,y:base+36,'text-anchor':'middle',class:'insight-axis'},year));first=end;
    }
   }
   node.append(svg);
  }
 };
 const paging=(node,s,total,step,more=s.limit<total)=>{const controls=el('div','insight-actions');if(more)controls.append(button(t('さらに表示','Show more'),()=>{s.limit+=step;redraw()}));if(s.limit>step)controls.append(button(t('折りたたむ','Collapse'),()=>{s.limit=step;redraw()}));node.append(controls)};
 container.replaceChildren();container.append(el('h2','',({listening:t('リスニング','Listening'),collection:t('コレクション','Collection'),live:t('ライブ','Live')})[area]+t('の統計',' Insights')));
 const metrics=el('div','insight-metrics');for(const [name,value] of [[area==='live'?t('ライブ公演数','Live shows'):area==='collection'?t('所有作品数','Owned records'):t('鑑賞作品数','Listening records'),stats.total],[area==='live'?t('観たアーティスト数','Artists seen'):t('アーティスト数','Artists'),stats.artists.length]]){const metric=el('div','');metric.append(el('strong','',String(value)),el('span','',name));metrics.append(metric)}container.append(metrics);
 const artists=block('artists',t('アーティスト','Artists')),as=state('artists','ranking',15);
 bars(artists,stats.artists.slice(0,as.limit),true);paging(artists,as,stats.artists.length,15);
 const names={genre:t('ジャンル','Genres'),tags:t('タグ','Tags'),label:t('レーベル','Labels'),store:t('購入店舗','Stores'),format:t('フォーマット','Formats'),venue:t('会場','Venues')};
 for(const [field,entries] of Object.entries(stats.categories)){
  const node=block(field,names[field]),s=state(field,'pie',15);switches(node,s,[['pie',t('円グラフ','Pie Chart')],['ranking',t('ランキング','Ranking')]],15);
  if(!entries.length){empty(node);continue}
  if(s.mode==='ranking'){bars(node,entries.slice(0,s.limit));paging(node,s,entries.length,15);continue}
  const slices=pie(entries),total=entries.reduce((sum,x)=>sum+x.count,0);
  let offset=0;
  const donut=el('div','insight-donut'),svg=svgNode('svg',{viewBox:'0 0 180 180','aria-hidden':'true'}),circ=2*Math.PI*76;
  for(const [i,row] of slices.entries()){
   const length=row.count/total*circ,gap=slices.length===1?0:Math.min(1.7,length*.18);
   svg.append(svgNode('circle',{cx:90,cy:90,r:76,fill:'none',stroke:row.other?otherColor:colors[i],'stroke-width':22,'stroke-dasharray':`${length-gap} ${circ-length+gap}`,'stroke-dashoffset':-offset-gap/2,transform:'rotate(-90 90 90)'}));offset+=length;
  }
  const center=el('div','insight-center');center.append(el('strong','',String(total)),el('span','',t('合計','Total')));donut.append(svg,center);node.append(donut);
  const legend=el('ul','insight-legend');for(const [i,row] of slices.entries()){const li=el('li',''),swatch=el('span','insight-swatch');swatch.style.background=row.other?otherColor:colors[i];const value=el('span','insight-value');value.append(el('span','',String(row.count)),el('span','insight-percent',(row.count/total*100).toFixed(1)+'%'));li.append(swatch,el('span','insight-name',row.other?t('その他','Other'):row.name),value);legend.append(li)}node.append(legend);
 }
 const time=block('time',area==='live'?t('公演時期','Show dates'):area==='collection'?t('購入時期','Purchase dates'):t('鑑賞時期','Listening dates')),ts=state('time','monthly',12);
 switches(time,ts,[['monthly',t('月別','Monthly')],['yearly',t('年別','Yearly')]],value=>value==='monthly'?12:5);
 const period=timeline(stats,ts.mode,ts.limit,now);if(ts.mode==='monthly')columns(time,period.rows,true);else{bars(time,period.rows,false,true);paging(time,ts,0,5,period.more)}
 if(area!=='live'){
  const rel=block('release',t('リリース年','Release years')),rs=state('release','yearly',10);switches(rel,rs,[['yearly',t('年別','Yearly')],['decade',t('年代別','By Decade')]],10);
  const rows=releaseRows(stats,rs.mode==='decade');
  if(rs.mode==='yearly'){bars(rel,rows.slice(0,rs.limit),false,true);paging(rel,rs,rows.length,10)}
  else columns(rel,rows);
 }
 if(area==='listening'){
  const node=block('score',t('スコアランキング','Score Ranking')),s=state('score','release',15);
  switches(node,s,[['date',t('鑑賞年','Listening Year')],['release',t('リリース年','Release Year')]],15);
  let ranking=scoreRanking(records,s.mode,s.year||'',ui.score||recordScore);
  if(s.year&&!ranking.years.includes(Number(s.year))){s.year='';ranking=scoreRanking(records,s.mode,'',ui.score||recordScore)}
  const label=el('label','insight-year-label',t('対象年','Year')),select=el('select','field insight-year');select.setAttribute('aria-label',t('対象年','Year'));
  for(const year of ['',...ranking.years]){const option=el('option','',year||t('すべての年','All Years'));option.value=year;select.append(option)}
  select.value=s.year||'';select.onchange=()=>{s.year=select.value;s.limit=15;redraw()};label.append(select);node.append(label);
  if(!ranking.rows.length)node.append(el('p','insight-note',t('対象となるスコア設定済みの記録はありません。','No scored records for this selection.')));
  else{
   const list=el('ol','insight-scores');for(const {record,rank,score} of ranking.rows.slice(0,s.limit)){
    const li=el('li','insight-score-row'),info=el('div','insight-score-info');
    info.append(el('div','insight-score-title',record.title||t('タイトル未設定','Untitled')),el('div','insight-score-artist',record.artist||t('アーティスト不明','Unknown Artist')));
    li.append(el('span','insight-rank',String(rank)),ui.art?ui.art(record):el('div','art placeholder','♫'),info,ui.rating?ui.rating(record):el('span','',score.toFixed(1)));list.append(li);
   }node.append(list);paging(node,s,ranking.rows.length,15);
  }
 }

}
const api={counts,dateParts,aggregate,pie,timeline,releaseRows,scoreRanking,recordScore,colors,otherColor,render};if(typeof module==='object'&&module.exports)module.exports=api;else root.MLAInsights=api;
})(globalThis);

