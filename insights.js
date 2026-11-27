/* Read-only Insights records. View state is in memory; layout uses separate browser preferences. */
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
 const length=Math.min(limit,available);
 const rows=Array.from({length},(_,i)=>{const k=current-i;return {name:monthly?String(Math.floor(k/12)).padStart(4,'0')+'-'+String(k%12+1).padStart(2,'0'):String(k),count:map.get(k)||0}});
 return {rows,more:length<available};
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
const sectionIds=area=>['artists',...(area!=='collection'?['score']:[]),...(area==='live'?['venue']:['genre','tags','label',...(area==='collection'?['store','format']:[])]),'time',...(area==='live'?[]:['release'])];
const layoutKey=area=>'mla-insights-layout-v1:'+area;
function normalizeLayout(value,area){
 const ids=sectionIds(area),defaults=()=>ids.map(id=>({id,visible:true}));
 if(!value||value.version!==1||!Array.isArray(value.items)||value.items.some(x=>!x||typeof x.id!=='string'||typeof x.visible!=='boolean'))return defaults();
 const seen=new Set(),items=[];
 for(const x of value.items){if(!ids.includes(x.id)||seen.has(x.id))continue;seen.add(x.id);items.push({id:x.id,visible:x.visible})}
 return [...items,...ids.filter(id=>!seen.has(id)).map(id=>({id,visible:true}))];
}
const sessionLayouts=new Map();let activeView=null,layoutDialog=null;
function readLayout(area){if(sessionLayouts.has(area))return sessionLayouts.get(area);try{return normalizeLayout(JSON.parse(localStorage.getItem(layoutKey(area))),area)}catch(e){return normalizeLayout(null,area)}}
function saveLayout(area,items){const value={version:1,items};try{localStorage.setItem(layoutKey(area),JSON.stringify(value));sessionLayouts.delete(area);return true}catch(e){sessionLayouts.set(area,normalizeLayout(value,area));return false}}
if(root.addEventListener)root.addEventListener('storage',e=>{
 if(e.key===null||['listening','collection','live'].some(a=>e.key===layoutKey(a))){
  for(const area of ['listening','collection','live'])if(e.key===null||e.key===layoutKey(area))sessionLayouts.delete(area);
  if(layoutDialog&&(e.key===null||e.key===layoutKey(layoutDialog.area)))layoutDialog.conflict();
  if(activeView&&(e.key===null||e.key===layoutKey(activeView.area)))activeView.refresh();
 }
});
function liveMonthRows(stats,now=new Date()){
 const current=now.getFullYear()*12+now.getMonth(),keys=[...stats.months.keys()].filter(k=>k<=current);
 if(!keys.length)return [];
 const first=Math.min(...keys);
 return Array.from({length:current-first+1},(_,i)=>{const k=first+i;return {name:String(Math.floor(k/12)).padStart(4,'0')+'-'+String(k%12+1).padStart(2,'0'),count:stats.months.get(k)||0}});
}
function columnColor(name,kind='year'){
 const p=dateParts(name),index=kind==='month'&&p?.month?p.year*12+p.month-1:kind==='decade'?Math.floor(Number(name)/10):Number(name);
 return colors[((index%colors.length)+colors.length)%colors.length];
}
const chartCleanups=new WeakMap();
function disposeCharts(node){for(const chart of node.querySelectorAll('[data-monthly-chart]')){chartCleanups.get(chart)?.();chartCleanups.delete(chart)}}
function chartScale(rows){
 const max=Math.max(1,...rows.map(r=>r.count)),rough=max/4,power=10**Math.floor(Math.log10(rough));
 const step=Math.max(1,[1,2,5,10].find(n=>n*power>=rough)*power);
 return {step,top:Math.ceil(max/step)*step};
}
const states=new Map();
// Every accepted save/restore replaces db with validated data (index.html commitDB).
// Weak keys release old snapshots and prevent stale counts after those replacements.
const snapshots=new WeakMap();
const colors=['#97C4CE','#C9AE8B','#ADA0BD','#8CAA98','#BD919C','#859BB7','#B6B18B','#BA9B83','#79AAA9','#BBA9B4','#9AA9BF','#A5BA88','#C49FAD','#8D9D8A','#ABA28C'];
const otherColor='#414951';
function render(container,records,area,ja,now=new Date(),ui={},onlyId=null){
 let snapshot=snapshots.get(records);
 if(!snapshot||snapshot.area!==area){snapshot={area,stats:aggregate(records,area)};snapshots.set(records,snapshot)}
 const host=container,widthHint=container.clientWidth||300;
 if(onlyId)container=document.createElement('div');
 else{container.style.minHeight='';activeView={area,refresh:()=>render(host,records,area,ja,now,ui)}};
 const stats=snapshot.stats,t=(jp,en)=>ja?jp:en;
 const el=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n};
 const state=(id,mode,limit)=>{const k=area+':'+id;if(!states.has(k))states.set(k,{mode,limit});return states.get(k)};
 const redraw=id=>{
  const old=host.querySelector('[data-insight="'+id+'"]');if(!old)return;
  const top=old.getBoundingClientRect().top,focus=document.activeElement;
  const focusIndex=[...old.querySelectorAll('button,select')].indexOf(focus);
  // Keep enough document height during a shrinking update to avoid browser scroll clamping.
  const previousMin=host.style.minHeight;host.style.minHeight=host.offsetHeight+'px';
  render(host,records,area,ja,now,ui,id);
  const next=host.querySelector('[data-insight="'+id+'"]');
  if(focusIndex>=0)next.querySelectorAll('button,select')[focusIndex]?.focus({preventScroll:true});
  const anchor=Math.max(16,top),targetY=Math.max(0,window.scrollY+next.getBoundingClientRect().top-anchor);window.scrollTo({top:targetY,behavior:'instant'});
  const needed=Math.max(0,window.scrollY+innerHeight-(document.documentElement.scrollHeight-host.offsetHeight));
  host.style.minHeight=needed?needed+'px':previousMin;
  window.scrollTo({top:targetY,behavior:'instant'});
 };
 const button=(title,fn)=>{const b=el('button','btn alt',title);b.type='button';b.onclick=fn;return b};
 const block=(id,title)=>{const n=el('section','insight-block');n.dataset.insight=id;n.append(el('h3','',title));container.append(n);return n};
 const switches=(node,s,options,initial)=>{const group=el('div','insight-switch');group.setAttribute('role','group');group.setAttribute('aria-label',node.querySelector('h3').textContent);for(const [value,title] of options){const b=button(title,()=>{s.mode=value;s.limit=typeof initial==='function'?initial(value):initial;redraw(node.dataset.insight)});b.setAttribute('aria-pressed',String(s.mode===value));group.append(b)}node.append(group)};
 const empty=node=>node.append(el('p','insight-note',t('集計できる登録データがありません。','No registered data to summarize.')));
 const bars=(node,rows,rank=false,horizontal=false,scale=null)=>{if(!rows.length){empty(node);return}const max=scale||Math.max(1,...rows.map(x=>x.count));const list=el('ol','insight-bars'+(horizontal?' insight-horizontal':'')+(horizontal&&rows.some(r=>r.name.length>4)?' insight-wide-label':''));for(const [i,row] of rows.entries()){const li=el('li','insight-bar');li.append(el('span','insight-name',(rank?(i+1)+'. ':'')+row.name),el('span','insight-count',String(row.count)));const track=el('div','insight-track'),fill=el('div','insight-fill');fill.style.width=(row.count/max*100)+'%';track.append(fill);li.append(track);list.append(li)}node.append(list)};
 const svgNode=(tag,attrs={},value)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(value!==undefined)n.textContent=value;return n};
 const columns=(node,source,kind='year',interactive=null)=>{
  if(!source.length){empty(node);return}
  const rows=[...source].reverse(),{step,top}=chartScale(rows),width=Math.max(260,widthHint),left=String(top).length*7+10,right=15,plot=width-left-right,height=154;
  const parts=kind==='decade'?Array.from({length:Math.ceil(rows.length/8)},(_,i)=>rows.slice(i*8,i*8+8)):[rows];
  for(const part of parts){
   const slot=plot/part.length,dense=kind==='decade'&&(String(top).length>2||slot<35),base=height+(dense?String(top).length*7+16:40);
   const svg=svgNode('svg',{viewBox:`0 0 ${width} ${base+42}`,class:'insight-columns',...(interactive?{role:'slider',tabindex:0,'aria-label':t('公演年を選択','Select show year'),'aria-valuemin':rows[0].name,'aria-valuemax':rows.at(-1).name}:{role:'img','aria-label':part.map(r=>r.name+t('年代','s')+': '+r.count).join(', ')})});
   for(let tick=0;tick<=top;tick+=step){const y=base-tick/top*height;svg.append(svgNode('line',{x1:left,x2:width-right,y1:y,y2:y,class:'insight-gridline'}),svgNode('text',{x:left-7,y:y+4,'text-anchor':'end',class:'insight-axis'},tick))}
   const marks=[],minYears=Math.ceil(48/slot),labelStep=[1,2,5,10,20,25,50,100,200,500,1000,2000,5000,10000].find(n=>n>=minYears)||10000;
   part.forEach((r,i)=>{const x=left+slot*(i+.5),h=r.count/top*height,w=Math.min(24,slot*.65);
    const mark=svgNode('rect',{x:x-w/2,y:base-h,width:w,height:h,rx:Math.min(2,w/4),class:'insight-column',fill:columnColor(r.name,kind),'data-period':r.name});svg.append(mark);marks.push(mark);
    if(kind==='decade'){
     svg.append(svgNode('text',{x,y:base-h-7,'text-anchor':dense?'start':'middle',class:'insight-column-count',...(dense?{transform:`rotate(-90 ${x} ${base-h-7})`}:{})},r.count));
     svg.append(svgNode('text',{x,y:base+21,'text-anchor':'middle',class:'insight-axis'},r.name));
    }else if(Number(r.name)%labelStep===0||rows.length===1)svg.append(svgNode('text',{x,y:base+21,'text-anchor':'middle',class:'insight-axis'},r.name));
   });
   node.append(svg);
   if(interactive){
    const controls=el('div','insight-year-selection'),select=el('select','field insight-year'),detail=el('span','insight-year-detail');select.setAttribute('aria-label',t('公演年を選択','Select show year'));detail.setAttribute('role','status');detail.setAttribute('aria-live','polite');
    for(const row of [...rows].reverse()){const option=el('option','',row.name+t('年',''));option.value=row.name;select.append(option)}controls.append(select,detail);node.append(controls);
    const indicator=svgNode('rect',{y:base-height,width:Math.max(slot,2),height:height+4,'fill-opacity':'.18','pointer-events':'none'});svg.insertBefore(indicator,svg.firstChild);
    const choose=index=>{const i=Math.max(0,Math.min(rows.length-1,index)),row=rows[i];interactive.selected=row.name;select.value=row.name;detail.textContent=ja?row.count+'件':row.count+(row.count===1?' show':' shows');const description=ja?row.name+'年　'+row.count+'件':row.name+' · '+detail.textContent;detail.setAttribute('aria-label',description);svg.setAttribute('aria-valuenow',row.name);svg.setAttribute('aria-valuetext',description);marks.forEach((m,j)=>m.classList.toggle('is-selected',j===i));indicator.setAttribute('x',left+slot*i);indicator.setAttribute('fill',columnColor(row.name,'year'))};
    choose(Math.max(0,rows.findIndex(r=>r.name===(interactive.selected||rows.at(-1).name))));
    select.onchange=()=>choose(rows.findIndex(r=>r.name===select.value));
    svg.onclick=e=>{const x=(e.clientX-svg.getBoundingClientRect().left)/svg.getBoundingClientRect().width*width;choose(Math.floor((x-left)/slot))};
    svg.onkeydown=e=>{let i=rows.findIndex(r=>r.name===interactive.selected);if(e.key==='ArrowLeft'||e.key==='ArrowDown')i--;else if(e.key==='ArrowRight'||e.key==='ArrowUp')i++;else if(e.key==='Home')i=0;else if(e.key==='End')i=rows.length-1;else return;e.preventDefault();choose(i)};
   }
  }
 };
 const monthlyHistory=(node,rows,s)=>{
  if(!rows.length){empty(node);return}
  const {step,top}=chartScale(rows),first=dateParts(rows[0].name),firstKey=first.year*12+first.month-1,lastYear=dateParts(rows.at(-1).name).year;
  const height=154,base=height+Math.max(40,String(top).length*7+16),chartHeight=base+48,axisWidth=Math.max(42,String(top).length*7+8);
  const controls=el('div','insight-month-controls'),jump=el('select','field insight-year'),range=el('span','insight-month-range');jump.setAttribute('aria-label',t('公演年へ移動','Jump to show year'));
  const all=el('option','',t('年を指定して移動','Jump to year'));all.value='';jump.append(all);
  for(let year=lastYear;year>=first.year;year--){const option=el('option','',year+t('年',''));option.value=year;jump.append(option)}controls.append(jump,range);node.append(controls);
  const chart=el('div','insight-month-chart'),axis=svgNode('svg',{width:axisWidth,height:chartHeight,viewBox:`0 0 ${axisWidth} ${chartHeight}`,class:'insight-month-axis','aria-hidden':'true'}),viewport=el('div','insight-month-viewport'),spacer=el('div','insight-month-spacer');chart.dataset.monthlyChart='';
  viewport.tabIndex=0;viewport.setAttribute('role','region');viewport.setAttribute('aria-label',t('公演月別グラフ。左右キーで移動できます。','Monthly shows chart. Use left and right arrow keys to scroll.'));viewport.append(spacer);chart.append(axis,viewport);node.append(chart);
  spacer.style.height=chartHeight+'px';for(let tick=0;tick<=top;tick+=step){const y=base-tick/top*height;axis.append(svgNode('text',{x:axisWidth-7,y:y+4,'text-anchor':'end',class:'insight-axis'},tick))}
  let slot=20,windowStart=-1,windowEnd=-1,windowSvg=null,observer=null,frame=0;
  const draw=()=>{
   if(!viewport.isConnected||!viewport.clientWidth)return;
   const start=Math.max(0,Math.floor(viewport.scrollLeft/slot)-2),end=Math.min(rows.length,Math.ceil((viewport.scrollLeft+viewport.clientWidth)/slot)+2);
   const visibleStart=Math.min(rows.length-1,Math.floor((viewport.scrollLeft+1)/slot)),visibleEnd=Math.min(rows.length-1,Math.ceil((viewport.scrollLeft+viewport.clientWidth-1)/slot)-1);
   s.monthPosition=firstKey+viewport.scrollLeft/slot;range.textContent=rows[visibleStart].name+'–'+rows[visibleEnd].name;
   if(start===windowStart&&end===windowEnd)return;windowStart=start;windowEnd=end;
   const width=(end-start)*slot,svg=svgNode('svg',{width,height:chartHeight,viewBox:`0 0 ${width} ${chartHeight}`,class:'insight-month-window',role:'img','aria-label':rows.slice(start,end).map(r=>r.name+': '+r.count).join(', ')});svg.style.left=start*slot+'px';
   for(let tick=0;tick<=top;tick+=step){const y=base-tick/top*height;svg.append(svgNode('line',{x1:0,x2:width,y1:y,y2:y,class:'insight-gridline'}))}
   const dense=String(top).length>2;
   for(let i=start;i<end;i++){const r=rows[i],x=(i-start+.5)*slot,h=r.count/top*height,w=Math.min(24,slot*.65);
    const bar=svgNode('rect',{x:x-w/2,y:base-h,width:w,height:h,rx:2,class:'insight-column',fill:columnColor(r.name,'month'),'data-period':r.name});const title=svgNode('title',{},r.name+': '+r.count);bar.append(title);svg.append(bar);
    svg.append(svgNode('text',{x,y:base-h-7,'text-anchor':dense?'start':'middle',class:'insight-column-count',...(dense?{transform:`rotate(-90 ${x} ${base-h-7})`}:{})},r.count));
    svg.append(svgNode('text',{x,y:base+19,'text-anchor':'middle',class:'insight-axis'},Number(r.name.slice(5))));
   }
   // Place each visible year's label under its month group, keeping full four-digit labels inside the viewport.
   for(let begin=visibleStart;begin<=visibleEnd;){let endYear=begin+1;const year=rows[begin].name.slice(0,4);while(endYear<=visibleEnd&&rows[endYear].name.startsWith(year+'-'))endYear++;
    const worldX=Math.max(viewport.scrollLeft+15,Math.min(viewport.scrollLeft+viewport.clientWidth-15,(begin+endYear)*slot/2));
    svg.append(svgNode('text',{x:worldX-start*slot,y:base+36,'text-anchor':'middle',class:'insight-axis'},year));begin=endYear;
   }
   if(windowSvg)windowSvg.replaceWith(svg);else spacer.append(svg);windowSvg=svg;
  };
  const resize=()=>{if(!viewport.isConnected||!viewport.clientWidth)return;const position=s.monthPosition??null;slot=viewport.clientWidth/Math.min(12,rows.length);spacer.style.width=rows.length*slot+'px';windowStart=-1;
   viewport.scrollLeft=position===null||position===undefined?viewport.scrollWidth-viewport.clientWidth:Math.max(0,(position-firstKey)*slot);draw()};
  viewport.onscroll=()=>{if(frame)cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>{frame=0;draw()})};
  viewport.onkeydown=e=>{let left=viewport.scrollLeft;if(e.key==='ArrowLeft')left-=slot;else if(e.key==='ArrowRight')left+=slot;else if(e.key==='PageUp')left-=slot*12;else if(e.key==='PageDown')left+=slot*12;else if(e.key==='Home')left=0;else if(e.key==='End')left=viewport.scrollWidth;else return;e.preventDefault();viewport.scrollTo({left,behavior:'instant'})};
  jump.onchange=()=>{if(!jump.value)return;viewport.scrollTo({left:Math.max(0,(Number(jump.value)*12-firstKey)*slot),behavior:'instant'});draw()};
  requestAnimationFrame(()=>{if(!chart.isConnected)return;resize();observer=new ResizeObserver(resize);observer.observe(viewport)});
  chartCleanups.set(chart,()=>{observer?.disconnect();if(frame)cancelAnimationFrame(frame)});
 };
 const paging=(node,s,total,step,more=s.limit<total)=>{const controls=el('div','insight-actions');if(more)controls.append(button(t('さらに表示','Show more'),()=>{s.limit+=step;redraw(node.dataset.insight)}));if(s.limit>step)controls.append(button(t('折りたたむ','Collapse'),()=>{s.limit=step;redraw(node.dataset.insight)}));node.append(controls)};
 let settingsButton;
 if(!onlyId){
 disposeCharts(container);container.replaceChildren();const heading=el('div','insight-heading');heading.append(el('h2','',({listening:t('リスニング','Listening'),collection:t('購入','Collection'),live:t('ライブ','Live')})[area]+t('の統計',' Insights')));container.append(heading);
 settingsButton=button('',()=>openSettings());settingsButton.className='btn ghost insight-settings';settingsButton.setAttribute('aria-label',t('表示設定','Display Settings'));settingsButton.setAttribute('aria-haspopup','dialog');
 const icon=svgNode('svg',{viewBox:'0 0 24 24','aria-hidden':'true'});icon.append(svgNode('path',{d:'M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6'}));settingsButton.append(icon);heading.append(settingsButton);
 const metrics=el('div','insight-metrics');for(const [name,value] of [[area==='live'?t('ライブ公演数','Live shows'):area==='collection'?t('所有作品数','Owned records'):t('鑑賞作品数','Listening records'),stats.total],[area==='live'?t('観たアーティスト数','Artists seen'):t('アーティスト数','Artists'),stats.artists.length]]){const metric=el('div','');metric.append(el('strong','',String(value)),el('span','',name));metrics.append(metric)}container.append(metrics);
 }
 if(!onlyId||onlyId==='artists'){const artists=block('artists',t('アーティスト','Artists')),as=state('artists','ranking',15);
 bars(artists,stats.artists.slice(0,as.limit),true);paging(artists,as,stats.artists.length,15);}
 const names={genre:t('ジャンル','Genres'),tags:t('タグ','Tags'),label:t('レーベル','Labels'),store:t('購入店舗','Stores'),format:t('フォーマット','Formats'),venue:t('会場','Venues')};
 for(const [field,entries] of Object.entries(stats.categories)){
  if(onlyId&&onlyId!==field)continue;
  const node=block(field,names[field]),s=state(field,'pie',15);switches(node,s,[['pie',t('円グラフ','Pie Chart')],['ranking',t('ランキング','Ranking')]],15);
  if(!entries.length){empty(node);continue}
  if(s.mode==='ranking'){bars(node,entries.slice(0,s.limit));paging(node,s,entries.length,15);continue}
  const slices=pie(entries),total=entries.reduce((sum,x)=>sum+x.count,0);
  let offset=0;
  const donut=el('div','insight-donut'),svg=svgNode('svg',{viewBox:'0 0 180 180','aria-hidden':'true'}),circ=2*Math.PI*72.5;
  for(const [i,row] of slices.entries()){
   const length=row.count/total*circ,gap=slices.length===1?0:Math.min(1.7,length*.18);
   svg.append(svgNode('circle',{cx:90,cy:90,r:72.5,fill:'none',stroke:row.other?otherColor:colors[i],'stroke-width':35,'stroke-dasharray':`${length-gap} ${circ-length+gap}`,'stroke-dashoffset':-offset-gap/2,transform:'rotate(-90 90 90)'}));offset+=length;
  }
  const center=el('div','insight-center');center.append(el('strong','',String(total)),el('span','',t('合計','Total')));const grooves=el('div','insight-record-grooves');grooves.setAttribute('aria-hidden','true');donut.append(svg,grooves,center);node.append(donut);
  const legend=el('ul','insight-legend');for(const [i,row] of slices.entries()){const li=el('li',''),swatch=el('span','insight-swatch');swatch.style.background=row.other?otherColor:colors[i];const value=el('span','insight-value');value.append(el('span','',String(row.count)),el('span','insight-percent',(row.count/total*100).toFixed(1)+'%'));li.append(swatch,el('span','insight-name',row.other?t('その他','Other'):row.name),value);legend.append(li)}node.append(legend);
 }
 if(!onlyId||onlyId==='time'){const time=block('time',area==='live'?t('公演時期','Show dates'):area==='collection'?t('購入時期','Purchase dates'):t('鑑賞時期','Listening dates')),ts=state('time','monthly',12);
 switches(time,ts,[['monthly',t('月別','Monthly')],['yearly',t('年別','Yearly')]],value=>value==='monthly'?12:5);
 if(area==='live'){
  if(ts.mode==='monthly'){monthlyHistory(time,liveMonthRows(stats,now),ts);
  }else{
   const period=timeline(stats,'yearly',Infinity,now);
   if(period.rows.length)time.append(el('p','insight-period',period.rows.at(-1).name+'–'+period.rows[0].name));
   columns(time,period.rows,'year',ts);
  }
 }else{
  const period=timeline(stats,ts.mode,ts.limit,now),map=ts.mode==='monthly'?stats.months:stats.years;
  const current=ts.mode==='monthly'?now.getFullYear()*12+now.getMonth():now.getFullYear();
  const scale=Math.max(1,...[...map].filter(([k])=>k<=current).map(([,n])=>n));
  bars(time,period.rows,false,true,scale);paging(time,ts,0,ts.mode==='monthly'?12:5,period.more);
 }
 }
 if(area!=='live'&&(!onlyId||onlyId==='release')){
  const rel=block('release',t('リリース年','Release years')),rs=state('release','yearly',10);switches(rel,rs,[['yearly',t('年別','Yearly')],['decade',t('年代別','By Decade')]],10);
  const rows=releaseRows(stats,rs.mode==='decade');
  if(rs.mode==='yearly'){bars(rel,rows.slice(0,rs.limit),false,true);paging(rel,rs,rows.length,10)}
  else columns(rel,rows,'decade');
 }
 if(area!=='collection'&&(!onlyId||onlyId==='score')){
  const node=block('score',t('スコアランキング','Score Ranking')),s=state('score',area==='live'?'date':'release',15);
  if(area==='listening')switches(node,s,[['date',t('鑑賞年','Listening Year')],['release',t('リリース年','Release Year')]],15);
  let ranking=scoreRanking(records,s.mode,area==='live'?'':s.year||'',ui.score||recordScore);
  if(area==='listening'&&s.year&&!ranking.years.includes(Number(s.year))){s.year='';ranking=scoreRanking(records,s.mode,'',ui.score||recordScore)}
  if(area==='listening'){const label=el('label','insight-year-label'),select=el('select','field insight-year');select.setAttribute('aria-label',t('対象年','Year'));
  for(const year of ['',...ranking.years]){const option=el('option','',year||t('すべての年','All Years'));option.value=year;select.append(option)}
  select.value=s.year||'';select.onchange=e=>{s.year=e.target.value;s.limit=15;redraw(node.dataset.insight)};label.append(select);node.append(label);}
  if(!ranking.rows.length)node.append(el('p','insight-note',t('対象となるスコア設定済みの記録はありません。','No scored records for this selection.')));
  else{
   const list=el('ol','insight-scores');for(const {record,rank,score} of ranking.rows.slice(0,s.limit)){
    const li=el('li','insight-score-row'),info=el('div','insight-score-info');
    if(area==='live'){
     const artists=(Array.isArray(record.artists)?record.artists:[]).map(clean).filter(Boolean).join(' / ');
     info.append(el('div','insight-score-title',clean(record.title)||artists||t('公演名未設定','Untitled show')),el('div','insight-score-date',record.date||t('日付不明','Unknown date')),el('div','insight-score-venue',record.venue||t('会場未設定','Venue not set')));
    }else info.append(el('div','insight-score-title',record.title||t('タイトル未設定','Untitled')),el('div','insight-score-artist',record.artist||t('アーティスト不明','Unknown Artist')));
    li.append(el('span','insight-rank',String(rank)),ui.art?ui.art(area==='live'?{...record,id:''}:record):el('div','art placeholder','♫'),info,ui.rating?ui.rating(record):el('span','',score.toFixed(1)));list.append(li);
   }node.append(list);paging(node,s,ranking.rows.length,15);
  }
 }

 const titleFor=id=>({artists:t('アーティスト','Artists'),score:t('スコアランキング','Score Ranking'),...names,time:area==='live'?t('公演時期','Show dates'):area==='collection'?t('購入時期','Purchase dates'):t('鑑賞時期','Listening dates'),release:t('リリース年','Release years')})[id];
 function openSettings(){
  if(layoutDialog)return;
  const modal=el('div','modal open insight-layout-modal'),dialog=el('div','dialog'),title=el('h2','',t('表示設定','Display Settings')),list=el('ul','insight-layout-list'),status=el('p','insight-note');
  title.id='insight-layout-title';modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');modal.setAttribute('aria-labelledby',title.id);status.setAttribute('role','status');
  let draft=readLayout(area).map(x=>({...x}));const done=button(t('完了','Done'),()=>{
   const saved=saveLayout(area,draft);close();render(host,records,area,ja,now,ui);
   if(!saved){const note=el('p','insight-note insight-layout-error',t('表示設定を保存できませんでした。今回の表示にのみ適用しています。','Display settings could not be saved. Applied for this session only.'));note.setAttribute('role','status');host.querySelector('.insight-heading').after(note)}
   host.querySelector('.insight-settings').focus({preventScroll:true});
  });
  const cancel=button(t('キャンセル','Cancel'),()=>close()),reset=button(t('初期設定に戻す','Reset to Default'),()=>{draft=normalizeLayout(null,area);draw();reset.focus()});
  const close=()=>{modal.remove();layoutDialog=null;host.inert=false;host.querySelector('.insight-settings')?.focus({preventScroll:true})};
  const draw=(focusId=null,move=null)=>{list.replaceChildren();for(const [i,item] of draft.entries()){
   const li=el('li','insight-layout-row'),label=el('label',''),input=el('input');input.type='checkbox';input.checked=item.visible;input.dataset.item=item.id;input.onchange=()=>{item.visible=input.checked};label.append(input,document.createTextNode(titleFor(item.id)));li.append(label);
   for(const [delta,symbol] of [[-1,'↑'],[1,'↓']]){const b=button(symbol,()=>{[draft[i],draft[i+delta]]=[draft[i+delta],draft[i]];draw(item.id,delta)});b.className='btn ghost';b.dataset.item=item.id;b.dataset.direction=delta;b.disabled=i+delta<0||i+delta>=draft.length;b.setAttribute('aria-label',titleFor(item.id)+(ja?(delta<0?'を上へ':'を下へ'):(delta<0?' up':' down')));li.append(b)}list.append(li);
  }if(focusId){const target=list.querySelector('button[data-item="'+focusId+'"][data-direction="'+move+'"]');(target&&!target.disabled?target:list.querySelector('input[data-item="'+focusId+'"]')).focus({preventScroll:true})}};
  layoutDialog={area,conflict:()=>{done.disabled=true;status.textContent=t('別のタブで設定が変わりました。キャンセルして開き直してください。','Settings changed in another tab. Cancel and reopen to continue.')}};
  const actions=el('div','insight-actions');actions.append(reset,cancel,done);dialog.append(title,list,status,actions);modal.append(dialog);document.body.append(modal);host.inert=true;draw();cancel.focus();
  modal.onclick=e=>{if(e.target===modal)close()};modal.onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();close()}if(e.key==='Tab'){const controls=[...modal.querySelectorAll('button:not(:disabled),input')],first=controls[0],last=controls.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}};
 }
 if(onlyId){
  const old=host.querySelector('[data-insight="'+onlyId+'"]'),next=container.querySelector('[data-insight="'+onlyId+'"]');
  // Retain section and heading nodes so browser scroll anchors remain connected.
  const oldTitle=old.querySelector('h3');next.querySelector('h3').replaceWith(oldTitle);
  // Retain the native year select itself (including Safari focus/picker identity).
  const oldSelect=old.querySelector(':scope > .insight-year-label select'),nextSelect=next.querySelector(':scope > .insight-year-label select');
  if(oldSelect&&nextSelect&&onlyId==='score'){
   const selected=nextSelect.value;oldSelect.replaceChildren(...nextSelect.childNodes);oldSelect.value=selected;oldSelect.onchange=nextSelect.onchange;nextSelect.replaceWith(oldSelect);
  }
  disposeCharts(old);old.replaceChildren(...next.childNodes);return;
 }
 const layout=readLayout(area);let visible=0;for(const item of layout){const node=container.querySelector('[data-insight="'+item.id+'"]');if(!node)continue;if(item.visible){container.append(node);visible++}else node.remove()}
 if(!visible)container.append(el('p','insight-note',t('表示する統計項目がありません。表示設定から選択できます。','No statistics selected. Choose items in Display Settings.')));

}
const api={counts,dateParts,aggregate,pie,timeline,releaseRows,scoreRanking,recordScore,colors,otherColor,sectionIds,normalizeLayout,liveMonthRows,columnColor,chartScale,render};if(typeof module==='object'&&module.exports)module.exports=api;else root.MLAInsights=api;
})(globalThis);

