#!/usr/bin/env node
/** Actual Chromium checks. Allows scoped official services; never installs dependencies. */
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {installNetworkPolicy,checkOfficialHeader,safeUrl} from './browser_header.mjs';
import {captureModule,readingMetrics,buttonStates,checkEvidence} from './browser_reading.mjs';
import {alignmentIssues,buttonIssues} from './browser_layout.mjs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
const [input,outArg,...options]=process.argv.slice(2);
let offline=false,profile='full',extraWidths=[],requestedModules=[];
try{
 for(let i=0;i<options.length;i++){
  const k=options[i];
  if(k==='--offline')offline=true;
  else if(k==='--profile'){profile=options[++i];if(!['preview','full'].includes(profile))throw Error('Invalid profile');}
  else if(k==='--widths'){const value=options[++i]||'';if(!/^\d+(,\d+)*$/.test(value))throw Error('Widths must be comma-separated integers');extraWidths=value.split(',').map(Number);if(extraWidths.length>20||extraWidths.some(w=>w<280||w>2560))throw Error('Widths must be 280..2560, at most 20');}
  else if(k==='--modules'){requestedModules=(options[++i]||'').split(',');if(requestedModules.some(m=>!/^M\d+$/.test(m)))throw Error('Invalid module scope');}
  else throw Error('Unknown option: '+k);
 }
 if(profile==='full'&&requestedModules.length)throw Error('Full profile must cover all modules; --modules is preview-only');
 if(!input||!outArg)throw Error('Usage: node check_browser.mjs HTML OUTPUT_DIR [--offline] [--profile preview|full] [--widths 320,390] [--modules M01,M03]');
}catch(e){console.error(String(e));process.exit(2);}
const started=performance.now();
const out=path.resolve(outArg),skill=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const resolvedOut=await fs.realpath(out).catch(()=>out);
if(resolvedOut===skill||resolvedOut.startsWith(skill+path.sep)||resolvedOut===path.dirname(path.resolve(input))&&path.basename(input)==='report.json'){console.error('Output must be outside Skill and must not overwrite inputs');process.exit(2);}
if((await fs.readdir(out).catch(()=>[])).length){console.error('Output directory must be new or empty; preserve previous HTML/screenshots/reports');process.exit(2);}
await fs.mkdir(out,{recursive:true});
const artifact=path.join(out,'artifact.html'),artifactBytes=await fs.readFile(path.resolve(input));
await fs.writeFile(artifact,artifactBytes);
const typeSpec=JSON.parse(await fs.readFile(path.join(skill,'assets/components/catalog.json'),'utf8')).typography;
const report={profile,completion_eligible:profile==='full',coverage:{modules:[],buttons:[],evidence:[],requiredWidths:[]},captures:[],reading:[],timings:{measurement_ms:0,capture_ms:0,interaction_ms:0},html_sha256:createHash('sha256').update(artifactBytes).digest('hex'),scope:'automated Chromium checks only',layers:Object.fromEntries(['content','visual','layout','function','delivery'].map(k=>[k,{status:'not-run'}])),geometry:[],status:'not-run',engine:'Chromium',checks:[],screenshots:[],not_run:['Safari','iOS real device','Android real device','semantic/factual review','manual screenshot review']};
const check=(id,ok,evidence)=>report.checks.push({id,status:ok?'pass':'fail',evidence});
let browser;
try{
 const module=process.env.QT_PLAYWRIGHT_MODULE;
 const loaded=await import(module?pathToFileURL(path.resolve(module)).href:'playwright');
 const {chromium}=loaded.chromium?loaded:loaded.default;
 browser=await chromium.launch({headless:true,...(process.env.QT_CHROMIUM_EXECUTABLE?{executablePath:process.env.QT_CHROMIUM_EXECUTABLE}:{})});
 const context=await browser.newContext({reducedMotion:'reduce'});
 const networkAudit=await installNetworkPolicy(context,offline);
 const page=await context.newPage(),errors=[],network=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(/^https?:/.test(r.url()))networkAudit.responses.push({url:safeUrl(r.url()),status:r.status()});});
 page.on('request',r=>{if(/^https?:/.test(r.url()))network.push(safeUrl(r.url()));});
 const url=pathToFileURL(artifact).href;
 await page.goto(url);await page.evaluate(()=>document.fonts.ready);
 const decoded=await page.evaluate(async()=>Promise.all([...document.querySelectorAll('main img')].map(async i=>{try{await i.decode();return {alt:i.alt,ok:i.naturalWidth>0};}catch{return {alt:i.alt,ok:false};}})));
 check('media-decoded',decoded.every(i=>i.ok),decoded);
 report.modules=await page.locator('[data-module-id]').evaluateAll(es=>es.map(e=>e.dataset.moduleId));
 if(requestedModules.some(id=>!report.modules.includes(id)))throw Error('Requested preview module not present');
 const previewModules=requestedModules.length?requestedModules:await page.evaluate(()=>[...new Set([document.querySelector('[data-module-id]')?.dataset.moduleId,document.querySelector('.qt-t-task-heading,[data-qt-type="feature"],.qt-t-steps,.qt-t-tasks,.qt-t-production')?.closest('[data-module-id]')?.dataset.moduleId,document.querySelector('figure[data-media-id]')?.closest('[data-module-id]')?.dataset.moduleId].filter(Boolean))]);
 const widths=[...new Set(profile==='full'?[1440,1024,1001,1000,768,701,700,390,375,320,...extraWidths]:(extraWidths.length?extraWidths:[320]))];
 const captureWidths=profile==='full'?[1440,1001,1000,768,701,700,390,320,...extraWidths]:widths;
 report.coverage.requiredWidths=widths;report.coverage.modules=profile==='full'?report.modules:previewModules;
 const measured=new Set();

 for(const width of (profile==='full'?[...widths,...widths.slice(0,-1).reverse()]:widths)){
  const measureStart=performance.now();
  await page.setViewportSize({width,height:950});await page.waitForTimeout(120);
  const result=await page.evaluate(typeSpec=>{
   const visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';
   const overflow=[],clippedText=[],clippedDecoration=[],manualClipping=[];
   function clip(e,rect,hardOnly=false){
    let r={left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom};
    for(let a=e.parentElement;a;a=a.parentElement){
     const s=getComputedStyle(a),b=a.getBoundingClientRect();
     const x=hardOnly?/^(hidden|clip)$/.test(s.overflowX):/^(hidden|clip|scroll|auto)$/.test(s.overflowX);
     const y=hardOnly?/^(hidden|clip)$/.test(s.overflowY):/^(hidden|clip|scroll|auto)$/.test(s.overflowY);
     if(x){r.left=Math.max(r.left,b.left+a.clientLeft);r.right=Math.min(r.right,b.left+a.clientLeft+a.clientWidth);}
     if(y){r.top=Math.max(r.top,b.top+a.clientTop);r.bottom=Math.min(r.bottom,b.top+a.clientTop+a.clientHeight);}
    }
    return r;
   }
   for(const e of document.querySelectorAll('main *')){
    if(!visible(e))continue;
    const raw=e.getBoundingClientRect(),r=clip(e,raw),name=e.tagName+'.'+e.getAttribute('class');
    if(r.right>r.left&&r.bottom>r.top&&(r.right>innerWidth+1||r.left<-1))overflow.push(name);
    if((raw.right>innerWidth+1||raw.left<-1)&&r.right<=innerWidth+1&&r.left>=-1&&e.closest('[aria-hidden="true"]'))clippedDecoration.push(name);
    const cs=getComputedStyle(e);
    if(cs.clipPath!=='none'||cs.maskImage&&cs.maskImage!=='none')manualClipping.push(name);
    if(e.closest('[aria-hidden="true"],svg,script,style')||cs.display==='none')continue;
    for(const n of e.childNodes){
     if(n.nodeType!==Node.TEXT_NODE||!n.textContent.trim())continue;
     const range=document.createRange();range.selectNodeContents(n);
     for(const text of range.getClientRects()){
      let hard=clip(e,text,true);
      // Include clipping on the text-bearing element itself; ancestor geometry alone misses it.
      if(/^(hidden|clip)$/.test(cs.overflowX)){hard.left=Math.max(hard.left,raw.left+e.clientLeft);hard.right=Math.min(hard.right,raw.left+e.clientLeft+e.clientWidth);}
      if(/^(hidden|clip)$/.test(cs.overflowY)){hard.top=Math.max(hard.top,raw.top+e.clientTop);hard.bottom=Math.min(hard.bottom,raw.top+e.clientTop+e.clientHeight);}
      if(hard.right<text.right-1||hard.left>text.left+1||hard.top>text.top+1||hard.bottom<text.bottom-1){clippedText.push({element:name,text:n.textContent.trim().slice(0,80)});break;}
     }
    }
   }
   const images=[...document.images].filter(i=>visible(i)&&(!i.complete||!i.naturalWidth||i.getBoundingClientRect().width<1||i.getBoundingClientRect().height<1)).map(i=>i.alt);
   const h1=document.querySelector('h1'),h2=document.querySelector('main h2'),h3=document.querySelector('main h3');
   const fontErrors=[],typeRoles=[],typeMap=new Map();
   const sizeKey=innerWidth<=typeSpec.breakpoint?'h5':'web';
   for(const [name,role] of Object.entries(typeSpec.roles))for(const selector of role.selectors)for(const e of document.querySelectorAll(selector))typeMap.set(e,name);
   for(const e of document.querySelectorAll('main [data-qt-type]')){
    const name=e.dataset.qtType;
    if(!typeSpec.roles[name])fontErrors.push({text:e.textContent.slice(0,60),reason:'unknown typography role',role:name});
    else typeMap.set(e,name);
   }
   const textElements=[...document.querySelectorAll('main,main *')].filter(e=>visible(e)&&!e.closest('svg,[aria-hidden="true"],script,style')&&(typeMap.has(e)||[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())));
   for(const e of textElements){
    let ancestor=e;while(ancestor&&!typeMap.has(ancestor))ancestor=ancestor.parentElement;
    const roleName=typeMap.get(ancestor);if(!roleName)continue;
    const role=typeSpec.roles[roleName],computed=getComputedStyle(e),expected=role[sizeKey]+'px';
    if(computed.fontSize!==expected)fontErrors.push({text:e.textContent.trim().slice(0,60),role:roleName,actual:computed.fontSize,expected});
    if(typeMap.has(e)){
     if(parseInt(computed.fontWeight)!==role.weight||Math.abs(parseFloat(computed.lineHeight)-role[sizeKey]*role.line_height)>.15)fontErrors.push({text:e.textContent.trim().slice(0,60),role:roleName,actualWeight:computed.fontWeight,expectedWeight:role.weight,actualLineHeight:computed.lineHeight,expectedLineHeight:role[sizeKey]*role.line_height});
     typeRoles.push({role:roleName,text:e.textContent.trim().slice(0,45),size:computed.fontSize,lineHeight:computed.lineHeight,weight:computed.fontWeight});
    }
   }
   const hierarchy=['page','section','feature','card','body','meta'].map(r=>typeSpec.roles[r][sizeKey]);
   if(hierarchy.some((size,i)=>i>0&&hierarchy[i-1]<=size))fontErrors.push({reason:'role scale does not form a descending reading hierarchy',hierarchy});
   const contrast=[],manualContrast=[];
   const rgb=s=>s.match(/[\d.]+/g)?.map(Number);
   const blend=(a,b)=>a.slice(0,3).map((v,i)=>v*(a[3]??1)+b[i]*(1-(a[3]??1)));
   function background(e){
    if(!e)return [255,255,255];const s=getComputedStyle(e);
    if(s.backgroundImage!=='none'||s.opacity!=='1'||s.filter!=='none'||s.mixBlendMode!=='normal')return null;
    const c=rgb(s.backgroundColor);if(!c||c.length<3)return null;
    if((c[3]??1)===1)return c;
    const parent=background(e.parentElement);return parent?blend(c,parent):null;
   }
   const luminance=c=>c.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
   for(const e of document.querySelectorAll('main *')){
    if(!visible(e)||getComputedStyle(e).display==='none'||!e.getBoundingClientRect().height||!Array.from(e.childNodes).some(n=>n.nodeType===3&&n.textContent.trim()))continue;
    const s=getComputedStyle(e),bg=background(e),fg=rgb(s.color),text=e.textContent.trim().slice(0,60);
    if(!bg||!fg||fg.length<3){manualContrast.push(text);continue;}
    const a=luminance(blend(fg,bg)),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    const large=parseFloat(s.fontSize)>=24||(parseFloat(s.fontSize)>=18.66&&parseInt(s.fontWeight)>=700),minimum=large?3:4.5;
    if(ratio+.001<minimum)contrast.push({text,ratio,minimum,color:s.color,background:bg});
   }
   const overlaps=[];
   for(const slot of document.querySelectorAll('.qt-t-person-slot')){
    const group=slot.closest('[data-qt-fit]');if(!group)continue;
    const r=slot.getBoundingClientRect();
    for(const text of group.querySelectorAll('h1,h2,h3,p,button,a,.qt-t-media')){
     if(slot.contains(text))continue;const t=text.getBoundingClientRect();
     if(Math.min(r.right,t.right)-Math.max(r.left,t.left)>1&&Math.min(r.bottom,t.bottom)-Math.max(r.top,t.top)>1)overlaps.push(text.textContent.slice(0,40));
    }
   }
   const hit=[...document.querySelectorAll('main button,main summary,main nav a,main .qt-btn,main .qt-t-route a,main .qt-t-sources a')].filter(e=>visible(e)&&e.getBoundingClientRect().height<43).map(e=>e.textContent.slice(0,30));
   const alignment=[];
   const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};};
   for(const g of document.querySelectorAll('[data-qt-group]')){
    const r=rect(g),p=g.parentElement,s=getComputedStyle(p),pr=rect(p);
    const left=pr.x+parseFloat(s.borderLeftWidth)+parseFloat(s.paddingLeft),right=pr.right-parseFloat(s.borderRightWidth)-parseFloat(s.paddingRight);
    if(Math.abs(r.x-left)>2||Math.abs(r.right-right)>2)alignment.push({type:'group-boundary',id:g.id,box:r,left,right});
    const rows=new Map();for(const child of [...g.children].filter(e=>visible(e)&&!e.hasAttribute('data-qt-empty'))){const c=rect(child),key=Math.round(c.y);if(!rows.has(key))rows.set(key,[]);rows.get(key).push(c);}
    for(const row of rows.values())if(g.dataset.qtAlign!=='natural'&&row.length>1&&Math.max(...row.map(r=>r.bottom))-Math.min(...row.map(r=>r.bottom))>2)alignment.push({type:'group-bottom',row});
   }
   for(const group of document.querySelectorAll('.qt-t-media-group:not([data-qt-align=natural])')){
    const rows=new Map();for(const fig of group.querySelectorAll('figure')){const r=rect(fig);const key=Math.round(r.y);if(!rows.has(key))rows.set(key,[]);rows.get(key).push(fig);}
    for(const row of rows.values())for(const selector of [':scope > :first-child','figcaption']){
     const boxes=row.map(f=>f.querySelector(selector)).filter(Boolean).map(rect);
     if(boxes.length>1&&(Math.max(...boxes.map(r=>r.y))-Math.min(...boxes.map(r=>r.y))>2||Math.max(...boxes.map(r=>r.bottom))-Math.min(...boxes.map(r=>r.bottom))>2))alignment.push({type:'media-slot/caption',selector,boxes});
    }
   }
   return {fontErrors,typeRoles,contrast,manualContrast,clippedText,clippedDecoration,manualClipping,alignment,groups:[...document.querySelectorAll('[data-qt-group]')].map(g=>({id:g.id,box:rect(g),columns:getComputedStyle(g).gridTemplateColumns})),bodyWidth:document.documentElement.scrollWidth,overflow,images,overlaps,hit,h1:getComputedStyle(h1).fontSize,h2:h2?getComputedStyle(h2).fontSize:null,h3:h3?getComputedStyle(h3).fontSize:null,maxContent:document.querySelector('main').getBoundingClientRect().width};
  },typeSpec);
  result.alignment.push(...await page.evaluate(alignmentIssues));
  check('button-colors-'+width,(await page.evaluate(buttonIssues)).length===0,await page.evaluate(buttonIssues));
  check('layout-'+width,result.bodyWidth<=width+1&&!result.overflow.length&&!result.clippedText.length&&!result.images.length&&!result.overlaps.length&&!result.hit.length&&!result.alignment.length&&result.maxContent<=1200.1&&!result.fontErrors.length,result);
  report.geometry.push({width,...result});
  check('text-readability-'+width,!result.fontErrors.length&&!result.contrast.length,{fontErrors:result.fontErrors,roles:result.typeRoles,contrast:result.contrast,requiresManualBackgroundReview:result.manualContrast});
  report.timings.measurement_ms+=performance.now()-measureStart;
  if(!measured.has(width)){
   measured.add(width);report.reading.push(await page.evaluate(readingMetrics));
   const captureStart=performance.now();
   if(captureWidths.includes(width)){
    if(profile==='full'){
     await page.evaluate(()=>scrollTo(0,0));await page.evaluate(()=>new Promise(requestAnimationFrame));
     const file=path.join(out,`page-${width}.png`);await page.screenshot({path:file,fullPage:true});report.screenshots.push(file);
    }
    for(const section of await page.locator('[data-module-id]').all()){
     const id=await section.getAttribute('data-module-id');if(profile==='preview'&&!previewModules.includes(id))continue;
     await captureModule(page,section,width,out,report);
    }
   }
   report.timings.capture_ms+=performance.now()-captureStart;
   if(profile==='full'){
    const interactionStart=performance.now();
    await buttonStates(page,width,check,report);await checkEvidence(page,width,check,report,out);
    report.timings.interaction_ms+=performance.now()-interactionStart;
   }
  }
 }
 if(profile==='full'){
 // All public targets, including footer duplicates, use the same locked behavior.
 await page.setViewportSize({width:1440,height:950});
 const targets=await page.locator('a[data-qt-target]').evaluateAll(es=>es.map(e=>e.dataset.qtTarget));
 for(let i=0;i<targets.length;i++){
  const link=page.locator('a[data-qt-target]').nth(i);await link.click();
  await page.locator('#qt-placeholder-dialog').waitFor({state:'visible'});
  const correct=await page.locator('#qt-dialog-target').textContent();await page.keyboard.press('Escape');
  await page.waitForTimeout(80);
  check('public-'+i,correct==='#'+targets[i]&&await link.evaluate(e=>document.activeElement===e),{target:targets[i],route:correct});
 }
 await checkOfficialHeader(page,check,report,out,offline);
 report.modules=await page.locator('[data-module-id]').evaluateAll(es=>es.map(e=>e.dataset.moduleId));
 const anchors=await page.locator('main a[href^="#"]:not([data-qt-target])').evaluateAll(es=>es.map((e,i)=>({index:i,href:e.getAttribute('href')})));
 for(const anchor of anchors){
  const previous=await page.evaluate(()=>location.hash),link=page.locator('main a[href^="#"]:not([data-qt-target])').nth(anchor.index);
  if(!await link.isVisible())continue;
  const exists=await page.evaluate(h=>!!document.getElementById(decodeURIComponent(h.slice(1))),anchor.href);
  if(!exists){check('subject-anchor-'+anchor.index,false,{href:anchor.href,reason:'missing target'});continue;}
  await link.click();await page.waitForTimeout(100);
  const state=await page.evaluate(h=>{const t=document.getElementById(decodeURIComponent(h.slice(1))),r=t.getBoundingClientRect();return {hash:location.hash,top:r.top,bottom:r.bottom};},anchor.href);
  let restored=true;
  if(previous!==anchor.href){await page.goBack();await page.waitForTimeout(100);restored=await page.evaluate(h=>location.hash===h,previous);}
  check('subject-anchor-'+anchor.index,state.hash===anchor.href&&state.top>=59&&restored,{...state,href:anchor.href,historyRestored:restored});
 }
 await page.setViewportSize({width:390,height:950});await page.waitForTimeout(120);
 const footerGroups=page.locator('.qt-footer-column');
 for(let i=0;i<await footerGroups.count();i++){
  const g=footerGroups.nth(i),summary=g.locator('summary');if(!await summary.count())continue;
  if(await g.evaluate(e=>e.open)){await summary.click();await page.waitForTimeout(80);}
  await summary.focus();await page.keyboard.press('Enter');await page.waitForTimeout(80);
  const opened=await g.evaluate(e=>e.open&&e.querySelector('summary').getAttribute('aria-expanded')==='true');
  const link=g.locator('a').first();await link.click();await page.keyboard.press('Escape');await page.waitForTimeout(100);
  const focused=await link.evaluate(e=>document.activeElement===e);
  await summary.focus();await page.keyboard.press('Enter');await page.waitForTimeout(80);
  check('mobile-footer-'+i,opened&&focused&&!await g.evaluate(e=>e.open)&&await summary.evaluate(e=>e.getBoundingClientRect().height>=44),{opened,focused,closed:!await g.evaluate(e=>e.open)});
 }
 await page.setViewportSize({width:1440,height:950});
 const moduleId=await page.locator('[data-module-id]').first().getAttribute('id');
 await page.evaluate(id=>{location.hash=id;},moduleId);await page.waitForTimeout(80);
 await page.locator('a[data-qt-target="consult"]').click();await page.keyboard.press('Escape');await page.waitForTimeout(100);
 check('section-history-focus',await page.locator('a[data-qt-target="consult"]').evaluate(e=>document.activeElement===e)&&await page.evaluate(id=>location.hash==='#'+id,moduleId),'section hash restored and opener focused');
 const toggle=page.locator('[data-qt-review-toggle]');
 if(await toggle.count()){
  const before=await page.locator('[data-fact-state],.qt-t-placeholder,[data-source-id]').allTextContents();
  await toggle.click();
  const stable=JSON.stringify(before)===JSON.stringify(await page.locator('[data-fact-state],.qt-t-placeholder,[data-source-id]').allTextContents());
  check('review-display-only',stable&&await page.locator('[data-review-only]:visible').count()===0,'facts/placeholders/source states retained; review hidden');await toggle.click();
 }
 for(const region of await page.locator('.qt-t-scroll').all()){
  const viewport=region.locator('.qt-t-scroll-viewport');await viewport.focus();
  await page.keyboard.press('End');await page.waitForTimeout(80);
  const atEnd=await region.locator('[data-scroll-next]').isDisabled();
  await page.keyboard.press('Home');await page.waitForTimeout(80);
  const atStart=await region.locator('[data-scroll-prev]').isDisabled();
  await region.locator('[data-scroll-expand]').click();
  const expanded=await viewport.evaluate(e=>getComputedStyle(e).overflow==='visible'&&getComputedStyle(e).maxHeight==='none');
  await region.locator('[data-scroll-expand]').click();
  check('local-scroll-'+(await region.getAttribute('data-axis')),atEnd&&atStart&&expanded,{atEnd,atStart,expanded,status:await region.locator('[data-scroll-status]').textContent()});
 }
 // Exercise real reload/back paths, not merely the presence of history handlers.
 const moduleCount=await page.locator('[data-module-id]').count();
 await page.evaluate(id=>{location.hash=id;},moduleId);await page.reload();await page.evaluate(()=>document.fonts.ready);
 check('reload-section-content',await page.evaluate(id=>location.hash==='#'+id,moduleId)&&await page.locator('[data-module-id]').count()===moduleCount&&!await page.locator('#qt-placeholder-dialog').evaluate(e=>e.open),'section hash and complete body survive actual reload');
 await page.locator('a[data-qt-target="consult"]').click();await page.reload();
 check('reload-prototype-route',await page.locator('#qt-placeholder-dialog').evaluate(e=>e.open)&&await page.locator('#qt-dialog-target').textContent()==='#consult','actual reload restores the public prototype route');
 await page.goBack();await page.waitForTimeout(100);
 const openerAfterReload=page.locator('a[data-qt-target="consult"]');await openerAfterReload.click();await page.goBack();await page.waitForTimeout(100);
 check('back-section-focus',await page.evaluate(id=>location.hash==='#'+id,moduleId)&&!await page.locator('#qt-placeholder-dialog').evaluate(e=>e.open)&&await openerAfterReload.evaluate(e=>document.activeElement===e),'actual browser Back closes modal, restores section hash and current opener focus');
 }
 report.services={officialSearchLayer:report.checks.find(c=>c.id==='official-search-open')?.status||'not-run',searchInput:offline?'not-run':report.official_services?.search||{status:'not-run'},searchSubmission:'not-run',realLogin:'not-run',networkMode:offline?'offline fallback':'official allowlist'};
 report.network=networkAudit;
 check('official-network-scope',!networkAudit.blocked.some(r=>!['xhr','fetch','script','image','ping'].includes(r.kind)),{blocked:networkAudit.blocked});
 check('console',errors.length===0,{errors});
 report.layers.layout={status:profile==='preview'?'not-run':report.checks.some(c=>(c.id.startsWith('layout-')||c.id.startsWith('text-readability-')||c.id==='media-decoded')&&c.status==='fail')?'fail':'pass',scope:'ten-width round trip, visible bounds and text clipping; complex mask/gradient checks require manual review'};
 report.layers.function={status:profile==='preview'?'not-run':report.checks.some(c=>!c.id.startsWith('layout-')&&!c.id.startsWith('text-readability-')&&c.status==='fail')?'fail':'pass',scope:'only interactions present on this page'};
 const complete=profile==='full'&&captureWidths.every(w=>report.modules.every(id=>report.captures.some(c=>c.width===w&&c.module===id&&c.complete)));
 if(profile==='full')check('complete-module-captures',complete,{widths:captureWidths,modules:report.modules,captures:report.captures});
 report.scope=profile==='full'?'Complete technical Chromium coverage; semantic/visual/user acceptance require separate review':'Partial preview for early 320px title/media review; never complete acceptance';
 report.not_run.push('semantic title phrase breaks','illustration relevance and visible subject weight');

 report.status=report.checks.some(c=>c.status==='fail')?'fail':'pass';
 await context.close();
}catch(e){report.status=browser?'fail':'not-run';report.error=String(e);report.checks.push({id:browser?'browser-execution':'browser-runtime',status:browser?'fail':'not-run',evidence:String(e)});}
finally{if(browser)await browser.close();report.screenshot_sha256=Object.fromEntries(await Promise.all(report.screenshots.map(async f=>[path.basename(f),createHash('sha256').update(await fs.readFile(f)).digest('hex')])));report.timings.total_ms=performance.now()-started;await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify({status:report.status,checks:report.checks.length,failed:report.checks.filter(c=>c.status==='fail'),error:report.error,report:path.join(out,'report.json')}));
process.exitCode=report.status==='pass'?0:1;
