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
 function natural(el){
  const img=el.querySelector('img');let width=measure(el);
  if(img&&img.naturalHeight){const h=num(getComputedStyle(img).height);width=Math.max(width,Math.min(img.naturalWidth,h*img.naturalWidth/img.naturalHeight));}
  return width;
 }
 let frame;
 function layout(){
  // Parent before nested child, then groups use actual current content rather than text-length buckets.
  topic.querySelectorAll('[data-qt-fit]').forEach(el=>{
   const host=available(el),outer=chrome(el),inner=Math.max(0,host-outer),children=[...el.children].filter(c=>!c.hidden),gap=14;
   if(!children.length)return;
   const type=el.dataset.qtFit;
   if(type==='prose'||children.length===1){el.dataset.layout='stacked';el.style.setProperty('--qt-fit-size',Math.min(host,Math.max(...children.map(natural))+outer)+'px');return;}
   const person=type==='person',lead=person?children[children.length-1]:children[0],main=person?children[0]:children[1];
   const leadN=natural(lead),mainN=natural(main),leadSize=Math.min(leadN,inner/2);
   const stacked=innerWidth<=700||inner<leadSize+gap+Math.min(mainN,leadSize);
   el.dataset.layout=stacked?'stacked':'columns';
   el.style.setProperty('--qt-lead',Math.max(0,Math.ceil(leadSize))+'px');
   el.style.setProperty('--qt-fit-size',Math.min(host,(stacked?Math.max(leadN,mainN):leadSize+gap+mainN)+outer)+'px');
  });
  topic.querySelectorAll('[data-qt-group]').forEach(el=>{
   const items=[...el.children],n=items.length,host=available(el);
   if(!n)return;
   const recommended=n<=4?n:([5,6,9].includes(n)?3:4);
   const desired=Math.min(host,Math.max(...items.map(natural)));
   const capacity=Math.max(1,Math.floor((host+14)/(Math.max(1,desired)+14)));
   const cols=Math.max(1,Math.min(recommended,capacity,innerWidth<=700?1:innerWidth<=1000?2:4));
   el.style.setProperty('--qt-cols',cols);
   el.style.inlineSize=Math.min(host,cols*desired+(cols-1)*14)+'px';
   el.style.marginInline='auto';
  });
  topic.querySelectorAll('.qt-t-scroll').forEach(el=>{
   const viewport=el.querySelector('.qt-t-scroll-viewport');
   if(!viewport)return;
   if(el.dataset.axis==='x'){
    const max=Math.max(0,...[...viewport.children].map(natural));
    el.style.setProperty('--qt-item-size',Math.min(viewport.clientWidth,max)+'px');
   }
   sync(el);
  });
 }
 const schedule=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(layout);};
 const resize=new ResizeObserver(schedule);resize.observe(topic);
 topic.querySelectorAll('[data-qt-fit],[data-qt-group],.qt-t-scroll').forEach(e=>resize.observe(e.parentElement));
 new MutationObserver(schedule).observe(topic,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class']});
 addEventListener('resize',schedule);document.fonts.ready.then(schedule);topic.querySelectorAll('img').forEach(i=>i.addEventListener('load',schedule));schedule();
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
