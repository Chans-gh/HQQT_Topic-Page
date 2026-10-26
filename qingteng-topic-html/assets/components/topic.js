/* Deterministic layout and reading interactions only. No consent or generation APIs. */
(() => {
 'use strict';
 const topic=document.querySelector('.qt-t-topic');if(!topic)return;
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
  const font=num(getComputedStyle(el).fontSize)||14;
  const text=Math.min(measure(el),font*18+chrome(el));
  const img=el.matches('img')?el:el.querySelector('img');
  const ratio=img&&img.naturalHeight?img.naturalWidth/img.naturalHeight:1;
  const media=img?Math.min(img.naturalWidth||font*18,font*18*Math.max(.75,Math.min(1.5,ratio))):0;
  return Math.max(text,media,chrome(el));
 }
 function childrenOf(el){return [...el.children].filter(c=>!c.hidden&&!c.hasAttribute('data-qt-empty'));}
 let frame;
 function layout(){
  // Groups own their full alignment boundary. Compact fitting is an explicit local intent.
  topic.querySelectorAll('[data-qt-group]').forEach(el=>{
   const items=childrenOf(el),n=items.length,host=available(el),gap=14;
   const mediaGroup=n>0&&items.every(item=>item.matches('figure')?!!item.querySelector('img'):item.querySelectorAll('figure').length===1);
   if(mediaGroup&&!el.classList.contains('qt-t-media-group')){el.classList.add('qt-t-media-group');el.dataset.qtMediaAuto='true';}
   if(!mediaGroup&&el.dataset.qtMediaAuto==='true'){el.classList.remove('qt-t-media-group');delete el.dataset.qtMediaAuto;}
   if(!n){el.style.setProperty('--qt-cols',1);el.style.inlineSize='100%';return;}
   const recommended=n<=4?n:([5,6,9].includes(n)?3:4);
   const desired=Math.max(1,...items.map(natural));
   const capacity=Math.max(1,Math.floor((host+gap)/(desired+gap)));
   let cols=Math.max(1,Math.min(recommended,capacity,innerWidth<=700?1:4));
   if(n>cols&&n%cols===1&&cols>2)cols--; // avoid a lone last step when a balanced row is available
   el.style.setProperty('--qt-cols',cols);
   el.style.inlineSize='100%';el.style.marginInline='0';
  });
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
   const stacked=innerWidth<=700||inner<Math.min(leadN,24*14)+gap+Math.min(mainN,24*14);
   const leadSize=Math.min(inner/2,Math.max(leadN,inner*(type==='media'?.45:.35)));
   el.dataset.layout=stacked?'stacked':'columns';
   el.style.setProperty('--qt-lead',Math.max(1,Math.floor(leadSize))+'px');
   el.style.setProperty('--qt-fit-size',(compact?Math.min(host,(stacked?Math.max(leadN,mainN):leadN+gap+mainN)+outer):host)+'px');
  });
  // A shared slot and caption row for each visual row. Measure intrinsic ratios, never output height.
  topic.querySelectorAll('.qt-t-media-group').forEach(el=>{
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
 topic.querySelectorAll('[data-qt-fit],[data-qt-group],.qt-t-scroll').forEach(e=>resize.observe(e.parentElement));
 new MutationObserver(schedule).observe(topic,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class','hidden','src','data-qt-align']});
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
 let dialog=null,opener=null;
 function close(){if(!dialog?.open)return;dialog.close();const target=opener;target?.focus({preventScroll:true});requestAnimationFrame(()=>target?.isConnected&&target.focus({preventScroll:true}));}
 topic.addEventListener('click',e=>{
  const button=e.target.closest('[data-qt-zoom]');if(!button)return;
  if(!dialog){dialog=document.createElement('dialog');dialog.className='qt-t-lightbox';dialog.setAttribute('aria-label','原图查看');dialog.innerHTML='<div class="qt-t-scroll-controls"><button class="qt-btn qt-btn-secondary" type="button" data-close>关闭原图</button><button class="qt-btn qt-btn-secondary" type="button" data-original aria-pressed="false">原尺寸查看</button></div><div class="qt-t-original" tabindex="0" aria-label="可滚动的原图"><img alt=""></div>';document.body.append(dialog);dialog.querySelector('[data-close]').addEventListener('click',close);dialog.addEventListener('cancel',e=>{e.preventDefault();close();});dialog.querySelector('[data-original]').addEventListener('click',e=>{const pressed=e.target.getAttribute('aria-pressed')!=='true';e.target.setAttribute('aria-pressed',String(pressed));dialog.querySelector('.qt-t-original').dataset.original=String(pressed);});}
  opener=button;const img=button.querySelector('img'),target=dialog.querySelector('img');target.src=img.src;target.alt=img.alt;dialog.querySelector('.qt-t-original').dataset.original='false';dialog.querySelector('[data-original]').setAttribute('aria-pressed','false');dialog.showModal();dialog.querySelector('[data-close]').focus();
 });
})();
