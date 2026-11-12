/** Reading/coverage probes, shared by preview and complete Chromium runs. */
import path from 'node:path';
export async function captureModule(page,section,width,out,report){
 const id=await section.getAttribute('data-module-id');let box=await section.boundingBox();
 if(!box||box.height<1)throw new Error('Module has no capture bounds: '+id);
 const parts=[];
 if(box.height<=12000){
  await page.setViewportSize({width,height:Math.max(950,Math.ceil(box.height)+172)});
  box=await section.boundingBox();
 }
 if(box.height<=16000){
  const file=path.join(out,`module-${id}-${width}.png`);
  await section.screenshot({path:file,style:'#qt-official-header { visibility:hidden!important }'});
  report.screenshots.push(file);parts.push({file,start:0,end:box.height});
 }else{
  await page.setViewportSize({width,height:950});
  box=await section.evaluate(e=>{const r=e.getBoundingClientRect();return {x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height};});
  for(let start=0,part=1;start<box.height;start+=8000,part++){
   const end=Math.min(box.height,start+8000),file=path.join(out,`module-${id}-${width}-part${part}.png`);
   await page.screenshot({path:file,clip:{x:box.x,y:box.y+start,width:box.width,height:end-start},fullPage:true,style:'#qt-official-header { visibility:hidden!important }'});
   report.screenshots.push(file);parts.push({file,start,end});
  }
 }
 report.captures.push({module:id,width,height:box.height,parts,complete:parts[0].start===0&&parts.at(-1).end>=box.height-1});
 await page.setViewportSize({width,height:950});
}
export function readingMetrics(){
 const titles=[...document.querySelectorAll('main h1,main h2,main h3')].map(e=>{
  const lines=new Map(),walker=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let n;
  while((n=walker.nextNode()))for(let i=0;i<n.length;i++){
   const r=document.createRange();r.setStart(n,i);r.setEnd(n,i+1);
   const b=r.getBoundingClientRect();if(!b.width||!b.height)continue;
   const k=Math.round(b.top);lines.set(k,(lines.get(k)||'')+n.data[i]);
  }
  const phrases=[...e.querySelectorAll('.qt-t-title-phrase')].map(p=>{const r=document.createRange();r.selectNodeContents(p);return {text:p.textContent,lines:new Set([...r.getClientRects()].filter(r=>r.width&&r.height).map(r=>Math.round(r.top))).size};});
  return {module:e.closest('[data-module-id]')?.dataset.moduleId,text:e.textContent,lines:[...lines].sort((a,b)=>a[0]-b[0]).map(([top,text])=>({top,text})),phrases};
 });
 const media=[...document.querySelectorAll('main figure[data-media-id]')].map(f=>{
  const img=f.querySelector('img'),r=img?.getBoundingClientRect();if(!r)return {id:f.dataset.mediaId,missing:true};
  const scale=Math.min(r.width/img.naturalWidth,r.height/img.naturalHeight),w=img.naturalWidth*scale,h=img.naturalHeight*scale,objectPosition=getComputedStyle(img).objectPosition;
  let bounds;try{bounds=JSON.parse(f.dataset.qtSubjectBounds||'null');}catch{}
  return {id:f.dataset.mediaId,role:f.dataset.mediaRole,bytes:Number(f.dataset.mediaBytes||0),natural:[img.naturalWidth,img.naturalHeight],frame:[r.width,r.height],image:[w,h],object_position:objectPosition,subject:bounds?[(bounds[2]-bounds[0])*w,(bounds[3]-bounds[1])*h]:null,subject_bounds:bounds||null,caption:f.querySelector('figcaption')?.textContent||'',requires_manual_review:['explanation added by this image','visible subject weight and safe margins','evidence matches nearby claim',...(!/^(?:[+-]?(?:\d*\.)?\d+(?:%|px)|left|right|center) (?:[+-]?(?:\d*\.)?\d+(?:%|px)|top|bottom|center)$/.test(objectPosition)?['Complex object-position: image/caption alignment not automatically certified']:[])]};
 });
 const chapters=[...document.querySelectorAll('main [data-module-id]')].map(e=>{const h=e.querySelector('h1,h2'),r=h?.getBoundingClientRect();return {module:e.dataset.moduleId,titleLeft:r?.left,titleRight:r?.right,declaredBaseline:h?.dataset.qtBaseline||null};});
 const groups=[...document.querySelectorAll('main .qt-t-group,main .qt-t-production')].map(e=>({module:e.closest('[data-module-id]')?.dataset.moduleId,mode:e.dataset.qtAlign||'aligned',peers:[...e.children].filter(c=>c.getClientRects().length).map(c=>{const r=c.getBoundingClientRect();return {top:r.top,left:r.left,width:r.width,height:r.height};})}));
 return {width:innerWidth,titles,media,composition:{chapters,groups,requires_manual_review:['Chapter baselines: intentional indentation or inconsistent padding?','Sparse last row, cramped copy and excessive card repetition','Actual image content edge versus caption and nearby text']},notice:'Line boxes, row geometry and alpha subject geometry are measurements, not semantic/visual acceptance.'};
}
export async function buttonStates(page,width,check,report){
 const buttons=page.locator('main button,main a.qt-btn');
 for(let i=0;i<await buttons.count();i++){
  const b=buttons.nth(i);if(!await b.isVisible()||!await b.isEnabled())continue;
  const states={};
  for(const state of ['default','hover']){
   if(state==='hover')await b.hover();else await page.mouse.move(1,1);
   await page.waitForTimeout(180);
   states[state]=await b.evaluate(e=>{const s=getComputedStyle(e);return {text:e.textContent.trim().slice(0,100),module:e.closest('[data-module-id]')?.dataset.moduleId,color:s.color,background:s.backgroundColor,border:s.borderColor,hover:e.matches(':hover'),variant:e.matches('.qt-btn-secondary,.qt-btn-inverse')?'secondary':e.matches('.qt-btn-primary')?'primary':'other',children:[...e.querySelectorAll('*')].filter(n=>[...n.childNodes].some(t=>t.nodeType===3&&t.textContent.trim())).map(n=>getComputedStyle(n).color)};});
  }
  const s=states,expected=s.default.variant==='secondary'?'rgb(23, 34, 30)':'rgb(255, 255, 255)';
  const valid=Object.values(s).every(v=>v.variant==='other'||v.color===expected&&v.children.every(c=>c===expected)&&(v.variant==='secondary'?v.background==='rgb(255, 255, 255)':(()=>{const c=v.background.match(/[\d.]+/g)?.map(Number)||[];return c[1]>c[0]&&c[1]>c[2]&&(c[3]??1)===1;})()));
  check(`body-button-${width}-${i}`,valid&&!s.default.hover&&s.hover.hover,{index:i,width,...s});
  report.coverage.buttons.push({index:i,width,states:['default','hover'],module:s.default.module});
 }
}
export async function checkEvidence(page,width,check,report,out){
 const zooms=page.locator('[data-qt-zoom]');
 for(let i=0;i<await zooms.count();i++){
  const zoom=zooms.nth(i);if(!await zoom.isVisible())continue;
  const id=await zoom.evaluate(e=>e.closest('figure')?.dataset.mediaId||'image-'+e.dataset.qtZoom);
  const expected=await zoom.evaluate(e=>({src:e.dataset.qtOriginalSrc||e.querySelector('img').src,context:e.closest('figure')?.querySelector('figcaption')?.textContent||e.querySelector('img').alt,focus:e.dataset.qtFocusRegion?JSON.parse(e.dataset.qtFocusRegion):null,note:e.dataset.qtFocusNote||''}));
  await zoom.click();const dialog=page.locator('.qt-t-lightbox'),img=dialog.locator('img');await img.evaluate(i=>i.decode());await page.waitForTimeout(80);
  const source=await img.getAttribute('src'),context=await dialog.locator('.qt-t-zoom-context').textContent();
  if([1440,390].includes(width)){const file=path.join(out,`evidence-${id}-${i}-${width}-reading.png`);await dialog.screenshot({path:file});report.screenshots.push(file);}
  if(expected.focus){
   const region=await dialog.locator('.qt-t-original').evaluate((v,b)=>{const r=v.querySelector('img').getBoundingClientRect(),a=v.getBoundingClientRect();return {mode:v.dataset.mode,scrollTop:v.scrollTop,topGap:r.top+b[1]*r.height-a.top,contained:r.left+b[0]*r.width>=a.left-2&&r.left+b[2]*r.width<=a.right+2&&r.top+b[1]*r.height>=a.top-2&&r.top+b[3]*r.height<=a.bottom+2};},expected.focus);
   check(`evidence-focus-${width}-${i}`,region.mode==='focus'&&region.contained&&region.topGap<=34,{id,...region});
  }
  const center=()=>dialog.locator('.qt-t-original').evaluate(v=>{const r=v.querySelector('img').getBoundingClientRect(),b=v.getBoundingClientRect();return {x:Math.max(0,Math.min(1,(b.left+v.clientLeft+v.clientWidth/2-r.left)/r.width)),y:Math.max(0,Math.min(1,(b.top+v.clientTop+v.clientHeight/2-r.top)/r.height))};});
  // At a natural-image edge, scrolling cannot keep the same center. The reading
  // point must remain visible, including when the entire original fits already.
  const containsReading=point=>dialog.locator('.qt-t-original').evaluate((v,p)=>{const r=v.querySelector('img').getBoundingClientRect(),b=v.getBoundingClientRect(),x=r.left+p.x*r.width,y=r.top+p.y*r.height;return x>=b.left+v.clientLeft-2&&x<=b.left+v.clientLeft+v.clientWidth+2&&y>=b.top+v.clientTop-2&&y<=b.top+v.clientTop+v.clientHeight+2;},point);
  const initial=await center();
  if(expected.focus){
   await dialog.locator('button[data-original]').click();await page.waitForTimeout(80);const detailed=await center();
   check(`evidence-focus-original-position-${width}-${i}`,await containsReading(initial),{id,initial,detailed});
  }
  const beforeFit=await center();
  await dialog.locator('[data-fit]').click();await page.waitForTimeout(80);
  const fit=await img.evaluate(i=>{const a=i.getBoundingClientRect(),b=i.parentElement.getBoundingClientRect();return a.width<=b.width+1&&a.height<=b.height+1;});
  await dialog.locator('button[data-original]').click();await page.waitForTimeout(80);
  const natural=await img.evaluate(i=>Math.abs(i.getBoundingClientRect().width-i.naturalWidth)<1&&i.parentElement.dataset.original==='true');
  if(expected.focus){const returned=await center();check(`evidence-fit-return-position-${width}-${i}`,await containsReading(beforeFit),{id,beforeFit,returned});}
  if([1440,390].includes(width)){const file=path.join(out,`evidence-${id}-${i}-${width}.png`);await dialog.screenshot({path:file});report.screenshots.push(file);}
  await page.keyboard.press('Escape');await page.waitForTimeout(30);
  const focused=await zoom.evaluate(e=>document.activeElement===e);
  check(`evidence-all-${width}-${i}`,source===expected.src&&context===expected.context+(expected.note?' · '+expected.note:'')&&fit&&natural&&focused,{id,sourceMatches:source===expected.src,fit,natural,focusReturned:focused});
  report.coverage.evidence.push({id,index:i,width,modes:expected.focus?['focus','fit','original']:['fit','original']});
 }
}
