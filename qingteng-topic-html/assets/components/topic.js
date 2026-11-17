/* Deterministic layout and reading interactions only. No consent or generation APIs. */
(() => {
 'use strict';
 const topic=document.querySelector('.qt-t-topic');if(!topic)return;
 const fieldGroups='[data-qt-group],.qt-t-group,.qt-t-production,[data-qt-composition="parallel"]';
 const canvas=document.createElement('canvas').getContext('2d');
 const num=x=>parseFloat(x)||0;
 const chrome=el=>{const s=getComputedStyle(el);return num(s.paddingLeft)+num(s.paddingRight)+num(s.borderLeftWidth)+num(s.borderRightWidth);};
 function measure(el){
  const selector='h1,h2,h3,p,li,dt,dd,button,a,strong,summary';
  const leaves=[...(el.matches(selector)?[el]:[]),...el.querySelectorAll(selector)].filter(n=>n.getClientRects().length&&!n.querySelector('h1,h2,h3,p,li,dt,dd,button,a,strong'));
  return Math.max(0,...leaves.map(n=>{const s=getComputedStyle(n);canvas.font=s.font||`${s.fontWeight} ${s.fontSize} ${s.fontFamily}`;let width=canvas.measureText(n.textContent.replace(/\s+/g,' ').trim()).width;for(let p=n;p&&p!==el.parentElement;p=p.parentElement)width+=chrome(p);return width;}));
 }
 function available(el){const p=el.parentElement,s=getComputedStyle(p);return Math.max(0,p.clientWidth-num(s.paddingLeft)-num(s.paddingRight));}
 // Readable wrapping budget, in the current font, rather than a whole unbroken sentence.
 // Media uses intrinsic ratio only: a previous rendered height must never feed the next width.
 function natural(el){
  const font=num(getComputedStyle(el).fontSize)||16;
  const text=Math.min(measure(el),font*18+chrome(el));
  const img=el.matches('img')?el:el.querySelector('img');
  const ratio=img&&img.naturalHeight?img.naturalWidth/img.naturalHeight:1;
  const media=img?Math.min(img.naturalWidth||font*18,font*18*Math.max(.75,Math.min(1.5,ratio))):0;
  return Math.max(text,media,chrome(el));
 }
 function childrenOf(el){return [...el.children].filter(c=>!c.hidden&&!c.hasAttribute('data-qt-empty'));}
 function prepareClusters(){
  topic.querySelectorAll('.qt-t-cluster').forEach(el=>{
   const items=childrenOf(el),support=items[1];
   delete el.dataset.qtEmptySupport;
   if(items.length!==2){el.dataset.qtLayout=items.length<2?'single':'stacked';return;}
   const flow=support.matches('.qt-t-stack,.qt-t-group,.qt-t-production')?support:support.matches('.qt-t-cluster-support')?support.firstElementChild:support;
   const empty=!support.textContent.trim()&&!support.querySelector('img,video,button,input');
   if(empty){el.dataset.qtLayout='single';el.dataset.qtEmptySupport='true';return;}
   if(flow?.matches('.qt-t-stack,.qt-t-group,.qt-t-production')&&!flow.classList.contains('qt-t-support-flow'))flow.classList.add('qt-t-support-flow');
   // Probe intrinsic content at the proposed column widths, never at the last output height.
   const budget=natural(items[0])+natural(support)+14;
   el.dataset.qtLayout=innerWidth<=1000||available(el)-chrome(el)<budget?'stacked':'probe';
  });
 }
 function balanceClusters(){
  let changed=false;
  topic.querySelectorAll('.qt-t-cluster[data-qt-layout="probe"]').forEach(el=>{
   const [a,b]=childrenOf(el),ah=a.getBoundingClientRect().height,bh=b.getBoundingClientRect().height;
   // A very sparse opposite column becomes its own reading row, not a tall empty card.
   const unbalanced=Math.abs(ah-bh)>32&&Math.min(ah,bh)<Math.max(ah,bh)*.8;
   el.dataset.qtLayout=unbalanced?'stacked':'columns';changed=changed||unbalanced;
  });
  return changed;
 }
 function alignFields(){
  topic.querySelectorAll('[data-qt-field]').forEach(e=>e.style.removeProperty('min-block-size'));
  topic.querySelectorAll(fieldGroups).forEach(group=>{
   const rows=new Map();for(const item of childrenOf(group)){const key=Math.round(item.getBoundingClientRect().top);if(!rows.has(key))rows.set(key,[]);rows.get(key).push(item);}
   for(const row of rows.values()){
    if(row.length<2)continue;
    const names=[...new Set(row.flatMap(item=>[...item.querySelectorAll('[data-qt-field]')].filter(e=>e.closest(fieldGroups)===group).map(e=>e.dataset.qtField)))];
    for(const name of names){
     const fields=row.map(item=>[...item.querySelectorAll('[data-qt-field]')].find(e=>e.dataset.qtField===name&&e.closest(fieldGroups)===group));
     if(fields.some(e=>!e))continue;
     const height=Math.max(...fields.map(e=>e.getBoundingClientRect().height));
     fields.forEach(e=>e.style.setProperty('min-block-size',height+'px'));
    }
   }
  });
 }
 let frame;
 function layoutGroups(){
  // Groups own their full alignment boundary. Compact fitting is an explicit local intent.
  topic.querySelectorAll('[data-qt-group],.qt-t-group,.qt-t-production').forEach(el=>{
   const items=childrenOf(el),n=items.length,host=available(el),gap=14;
   const mediaGroup=n>0&&items.every(item=>item.matches('figure')?!!item.querySelector('img'):item.querySelectorAll('figure').length===1);
   if(mediaGroup&&!el.classList.contains('qt-t-media-group')){el.classList.add('qt-t-media-group');el.dataset.qtMediaAuto='true';}
   if(!mediaGroup&&el.dataset.qtMediaAuto==='true'){el.classList.remove('qt-t-media-group');delete el.dataset.qtMediaAuto;}
   if(!n){el.style.setProperty('--qt-cols',1);el.style.inlineSize='100%';return;}
   const recommended=n<=4?n:([5,6,9].includes(n)?3:4);
   const desired=Math.max(1,...items.map(natural));
   const capacity=Math.max(1,Math.floor((host+gap)/(desired+gap)));
   const symbols=el.classList.contains('qt-t-artifacts')&&items.every(item=>!item.querySelector('p,ul,ol'));
   let cols=Math.max(1,Math.min(recommended,capacity,innerWidth<=700?(symbols?2:1):4));
   if(n>cols&&n%cols===1&&cols>2)cols--; // avoid a lone last step when a balanced row is available
   el.style.setProperty('--qt-cols',cols);
   el.style.inlineSize='100%';el.style.marginInline='0';
  });
 }
 function layout(){
  topic.querySelectorAll('[data-qt-field]').forEach(e=>e.style.removeProperty('min-block-size'));
  prepareClusters();layoutGroups();
  if(balanceClusters())layoutGroups();
  alignFields();
  topic.querySelectorAll('[data-qt-fit]').forEach(el=>{
   const host=available(el),outer=chrome(el),inner=Math.max(0,host-outer),children=childrenOf(el),gap=14;
   if(!children.length)return;
   const compact=el.dataset.qtAlign==='compact',type=el.dataset.qtFit;
   if(type==='prose'||children.length===1){
    el.dataset.layout='stacked';
    el.style.setProperty('--qt-fit-size',(compact?Math.min(host,Math.max(...children.map(natural))+outer):host)+'px');return;
   }
   const person=type==='person',lead=person?children[children.length-1]:children[0],main=person?children[0]:children[1];
   const leadN=natural(lead),mainN=natural(main);
   const readingFont=num(getComputedStyle(main).fontSize)||16;
   const stacked=innerWidth<=700||inner<Math.min(leadN,24*readingFont)+gap+Math.min(mainN,24*readingFont);
   const leadSize=Math.min(inner/2,Math.max(leadN,inner*(type==='media'?.45:.35)));
   el.dataset.layout=stacked?'stacked':'columns';
   el.style.setProperty('--qt-lead',Math.max(1,Math.floor(leadSize))+'px');
   el.style.setProperty('--qt-fit-size',(compact?Math.min(host,(stacked?Math.max(leadN,mainN):leadN+gap+mainN)+outer):host)+'px');
  });
  // A shared slot and caption row for each visual row. Measure intrinsic ratios, never output height.
  topic.querySelectorAll('.qt-t-media-group').forEach(el=>{
   if(el.dataset.qtAlign==='natural'){for(const f of el.querySelectorAll('figure')){f.style.removeProperty('--qt-media-slot');f.style.removeProperty('--qt-caption-size');}return;}
   const items=childrenOf(el),rows=new Map();
   for(const item of items){const key=Math.round(item.offsetTop);if(!rows.has(key))rows.set(key,[]);rows.get(key).push(item);}
   for(const row of rows.values()){
    const figures=row.map(item=>item.matches('figure')?item:item.querySelector('figure')).filter(Boolean);
    const height=Math.max(0,...figures.map(f=>{const i=f.querySelector('img');return i&&i.naturalWidth?f.clientWidth*i.naturalHeight/i.naturalWidth:0;}));
    // A viewport-sized slot keeps portrait evidence complete without making adjacent images enormous.
    const slot=Math.min(height,innerWidth<=700?420:360);
    for(const f of figures){if(slot>0)f.style.setProperty('--qt-media-slot',slot+'px');f.style.removeProperty('--qt-caption-size');}
    const caption=Math.max(0,...figures.map(f=>f.querySelector('figcaption')?.getBoundingClientRect().height||0));
    for(const f of figures)f.style.setProperty('--qt-caption-size',caption+'px');
   }
  });
  // Probe at each width; a sparse evidence column becomes a reading row.
  topic.querySelectorAll('.qt-t-evidence').forEach(el=>{
   el.dataset.qtEvidenceLayout='probe';
   const items=childrenOf(el);if(items.length!==2)return;
   const [a,b]=items.map(e=>e.getBoundingClientRect());
   if(Math.min(a.right,b.right)<=Math.max(a.left,b.left)+2&&Math.abs(a.height-b.height)>Math.max(32,Math.max(a.height,b.height)*.2))el.dataset.qtEvidenceLayout='stacked';
  });
  topic.querySelectorAll('.qt-t-scroll').forEach(el=>{
   const viewport=el.querySelector('.qt-t-scroll-viewport');
   if(!viewport)return;
   if(el.dataset.axis==='x'){
    const max=Math.max(0,...[...viewport.children].map(natural));
    el.style.setProperty('--qt-item-size',Math.max(1,Math.min(viewport.clientWidth,max))+'px');
   }
   sync(el);
  });
 }
 const schedule=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(layout);};
 const resize=new ResizeObserver(schedule);resize.observe(topic);
 topic.querySelectorAll(fieldGroups+', [data-qt-fit],.qt-t-cluster,.qt-t-evidence,.qt-t-scroll').forEach(e=>resize.observe(e.parentElement));
 new MutationObserver(schedule).observe(topic,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class','hidden','src','data-qt-align','data-qt-composition']});
 addEventListener('resize',schedule);document.fonts.ready.then(schedule);topic.addEventListener('load',schedule,true);schedule();
 const review=topic.querySelector('[data-qt-review-toggle]');
 if(review)review.addEventListener('click',()=>{const show=review.getAttribute('aria-pressed')!=='true';review.setAttribute('aria-pressed',String(show));review.textContent=show?'隐藏策划批注与索引':'显示策划批注与索引';topic.querySelectorAll('[data-review-only]').forEach(n=>n.hidden=!show);schedule();});
 function sync(el){
  const v=el.querySelector('.qt-t-scroll-viewport'),x=el.dataset.axis==='x',full=el.dataset.expanded==='true';
  const pos=x?v.scrollLeft:v.scrollTop,max=x?v.scrollWidth-v.clientWidth:v.scrollHeight-v.clientHeight;
  const prev=el.querySelector('[data-scroll-prev]'),next=el.querySelector('[data-scroll-next]'),status=el.querySelector('[data-scroll-status]');
  if(prev)prev.disabled=full||pos<=1;if(next)next.disabled=full||pos>=max-1;
  const children=[...v.children].filter(c=>!c.hasAttribute('data-qt-empty')),bounds=v.getBoundingClientRect();
  const visible=children.map((c,i)=>({i:i+1,r:c.getBoundingClientRect()})).filter(o=>x?o.r.right>bounds.left+1&&o.r.left<bounds.right-1:o.r.bottom>bounds.top+1&&o.r.top<bounds.bottom-1);
  if(status)status.textContent=children.length?`共 ${children.length} 项；${full?'已完整展开':`可见 ${visible[0]?.i||1}–${visible.at(-1)?.i||children.length}；${pos<=1?'起点':pos>=max-1?'终点':'中间'}`}`:'暂无内容';
 }
 topic.querySelectorAll('.qt-t-scroll').forEach(el=>{
  const v=el.querySelector('.qt-t-scroll-viewport');if(!v)return;
  v.tabIndex=0;v.addEventListener('scroll',()=>sync(el),{passive:true});
  const move=(delta,edge=false)=>{const x=el.dataset.axis==='x';v.scrollTo({[x?'left':'top']:edge?(delta<0?0:(x?v.scrollWidth:v.scrollHeight)):(x?v.scrollLeft:v.scrollTop)+delta*(x?v.clientWidth:v.clientHeight),behavior:'instant'});sync(el);};
  el.addEventListener('click',e=>{if(e.target.closest('[data-scroll-prev]'))move(-1);if(e.target.closest('[data-scroll-next]'))move(1);const b=e.target.closest('[data-scroll-expand]');if(b){const expanded=el.dataset.expanded!=='true';el.dataset.expanded=String(expanded);b.setAttribute('aria-expanded',String(expanded));b.textContent=expanded?'恢复局部浏览':'完整展开';schedule();}});
  v.addEventListener('keydown',e=>{if(e.target!==v)return;const keys=el.dataset.axis==='x'?['ArrowLeft','ArrowRight']:['ArrowUp','ArrowDown'];if(keys.includes(e.key)){e.preventDefault();move(e.key===keys[0]?-1:1);}if(['Home','End'].includes(e.key)){e.preventDefault();move(e.key==='Home'?-1:1,true);}});
 });
 // Page/Day navigation is a progressive enhancement over real anchors. Sections stay visible and searchable.
 const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
 function anchorTarget(link){
  const href=link.getAttribute('href')||'';if(!href.startsWith('#')||href.length<2)return null;
  try{const target=document.getElementById(decodeURIComponent(href.slice(1)));return target&&topic.contains(target)?target:null;}catch{return null;}
 }
 topic.querySelectorAll('[data-qt-page-nav]').forEach(nav=>{
  const pairs=[...nav.querySelectorAll('a[href^="#"]')].map(link=>({link,target:anchorTarget(link)})).filter(item=>item.target);
  const sections=pairs.filter(item=>!item.link.classList.contains('qt-t-back-top'));
  if(!sections.length)return;
  let current=null;
  const select=item=>{
   if(!item||item===current)return;current=item;
   for(const pair of sections){if(pair===item)pair.link.setAttribute('aria-current','location');else pair.link.removeAttribute('aria-current');}
   if(nav.classList.contains('qt-t-stage-nav'))item.link.scrollIntoView({block:'nearest',inline:'nearest',behavior:reducedMotion?'auto':'smooth'});
  };
  const fromHash=()=>select(sections.find(item=>item.link.hash===location.hash)||sections[0]);
  if('IntersectionObserver' in window){
   const observer=new IntersectionObserver(entries=>{
    const visible=entries.filter(entry=>entry.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
    if(visible)select(sections.find(item=>item.target===visible.target));
   },{rootMargin:'-86px 0px -65% 0px',threshold:[0,.01]});
   sections.forEach(item=>observer.observe(item.target));
  }
  nav.addEventListener('click',event=>{const link=event.target.closest('a[href^="#"]');const item=sections.find(candidate=>candidate.link===link);if(item)select(item);});
  addEventListener('hashchange',fromHash);fromHash();
 });
 let dialog=null,opener=null,focusRegion=null,zoomTicket=0,readingPoint=null,zoomBusy=false,programmedScroll=null;
 function rememberReading(force=false){
  if(zoomBusy||!dialog?.open)return;
  const v=dialog.querySelector('.qt-t-original'),r=v.querySelector('img').getBoundingClientRect(),b=v.getBoundingClientRect();
  if(v.dataset.mode==='fit'||!r.width||!r.height)return;
  if(force!==true&&programmedScroll&&Math.abs(v.scrollLeft-programmedScroll.left)<1&&Math.abs(v.scrollTop-programmedScroll.top)<1)return;
  readingPoint={x:Math.max(0,Math.min(1,(b.left+v.clientLeft+v.clientWidth/2-r.left)/r.width)),y:Math.max(0,Math.min(1,(b.top+v.clientTop+v.clientHeight/2-r.top)/r.height))};
  programmedScroll={left:v.scrollLeft,top:v.scrollTop};
 }
 function close(){if(!dialog?.open)return;zoomTicket++;dialog.close();const target=opener;target?.focus({preventScroll:true});requestAnimationFrame(()=>target?.isConnected&&target.focus({preventScroll:true}));}
 async function zoomMode(mode,{initial=false,resize=false}={}){
  if(!initial&&!resize)rememberReading();
  zoomBusy=true;
  const ticket=++zoomTicket,v=dialog.querySelector('.qt-t-original'),img=v.querySelector('img');
  if(mode==='focus'&&!focusRegion)mode='fit';
  // Establish intent before decode so rapid mode changes can retain it too.
  if(mode==='focus'&&!resize)readingPoint={x:(focusRegion[0]+focusRegion[2])/2,y:(focusRegion[1]+focusRegion[3])/2};
  v.dataset.mode=mode;v.dataset.original=String(mode==='original');img.style.removeProperty('width');v.style.removeProperty('height');
  dialog.querySelector('[data-original]').setAttribute('aria-pressed',String(mode==='original'));
  dialog.querySelector('[data-fit]').setAttribute('aria-pressed',String(mode==='fit'));
  dialog.querySelector('[data-focus]').setAttribute('aria-pressed',String(mode==='focus'));
  try{await img.decode();}catch{if(ticket===zoomTicket)zoomBusy=false;return;}
  if(ticket!==zoomTicket||!dialog.open)return;
  if(mode==='fit')img.style.width=Math.min(img.naturalWidth,v.clientWidth,innerHeight*.65*img.naturalWidth/img.naturalHeight)+'px';
  if(mode==='focus'){
   const [x0,y0,x1,y1]=focusRegion;
   const scale=Math.min(1,v.clientWidth/(img.naturalWidth*(x1-x0)),v.clientHeight/(img.naturalHeight*(y1-y0)));
   img.style.width=img.naturalWidth*scale+'px';
   v.style.height=Math.min(innerHeight*.65,img.naturalHeight*scale*(y1-y0)+32)+'px';
   v.scrollLeft=Math.max(0,img.naturalWidth*scale*x0-Math.min(16,(v.clientWidth-img.naturalWidth*scale*(x1-x0))/2));
   v.scrollTop=Math.max(0,img.naturalHeight*scale*y0-Math.min(16,(v.clientHeight-img.naturalHeight*scale*(y1-y0))/2));
  }else{v.scrollTop=0;v.scrollLeft=0;}
  // Fit is an overview: retain the last reading point for the next detailed view.
  // Resize also retains it; only an explicit focus action resets to the source region.
  if(mode!=='fit'&&(mode==='original'||resize)&&readingPoint){
   const r=img.getBoundingClientRect(),b=v.getBoundingClientRect();
   v.scrollLeft+=r.left+readingPoint.x*r.width-(b.left+v.clientLeft+v.clientWidth/2);
   v.scrollTop+=r.top+readingPoint.y*r.height-(b.top+v.clientTop+v.clientHeight/2);
  }
  programmedScroll={left:v.scrollLeft,top:v.scrollTop};
  requestAnimationFrame(()=>{if(ticket===zoomTicket){zoomBusy=false;if(mode==='original'&&!readingPoint)rememberReading(true);}});
 }
 topic.addEventListener('click',e=>{
  const button=e.target.closest('[data-qt-zoom]');if(!button)return;
  if(!dialog){
   dialog=document.createElement('dialog');dialog.className='qt-t-lightbox';dialog.setAttribute('aria-label','原图查看');
   dialog.innerHTML='<div class="qt-t-scroll-controls"><button class="qt-btn qt-btn-secondary" type="button" data-close>关闭原图</button><button class="qt-btn qt-btn-secondary" type="button" data-focus aria-pressed="false">查看相关区域</button><button class="qt-btn qt-btn-secondary" type="button" data-fit aria-pressed="false">适应窗口</button><button class="qt-btn qt-btn-secondary" type="button" data-original aria-pressed="false">原尺寸查看</button></div><p class="qt-t-zoom-context"></p><div class="qt-t-original" tabindex="0" aria-label="可滚动的原图"><img alt=""></div>';
   document.body.append(dialog);dialog.querySelector('[data-close]').addEventListener('click',close);dialog.addEventListener('cancel',e=>{e.preventDefault();close();});
   for(const [attr,mode] of [['data-focus','focus'],['data-fit','fit'],['data-original','original']])dialog.querySelector('['+attr+']').addEventListener('click',()=>zoomMode(mode));
   dialog.querySelector('.qt-t-original').addEventListener('scroll',()=>rememberReading(),{passive:true});
   addEventListener('resize',()=>{if(dialog.open)zoomMode(dialog.querySelector('.qt-t-original').dataset.mode,{resize:true});});
  }
  opener=button;const img=button.querySelector('img'),target=dialog.querySelector('img');target.src=button.dataset.qtOriginalSrc||img.src;target.alt=img.alt;
  try{focusRegion=JSON.parse(button.dataset.qtFocusRegion||'null');}catch{focusRegion=null;}
  dialog.querySelector('[data-focus]').hidden=!focusRegion;
  const caption=button.closest('figure')?.querySelector('figcaption')?.textContent||img.alt;
  dialog.querySelector('.qt-t-zoom-context').textContent=caption+(button.dataset.qtFocusNote?' · '+button.dataset.qtFocusNote:'');
  readingPoint=null;zoomBusy=false;programmedScroll=null;
  dialog.showModal();zoomMode(focusRegion?'focus':'fit',{initial:true});dialog.querySelector('[data-close]').focus();
 });
})();
