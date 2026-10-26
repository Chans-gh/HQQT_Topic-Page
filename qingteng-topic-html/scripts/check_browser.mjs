#!/usr/bin/env node
/** Actual Chromium checks. Allows scoped official services; never installs dependencies. */
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {installNetworkPolicy,checkOfficialHeader,safeUrl} from './browser_header.mjs';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
const [input,outArg,flag]=process.argv.slice(2);
const offline=flag==='--offline';
if(flag&&!offline){console.error('Unknown option: '+flag);process.exit(2);}
if(!input||!outArg){console.error('Usage: node check_browser.mjs HTML OUTPUT_DIR [--offline]');process.exit(2);}
const out=path.resolve(outArg),skill=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const resolvedOut=await fs.realpath(out).catch(()=>out);
if(resolvedOut===skill||resolvedOut.startsWith(skill+path.sep)||resolvedOut===path.dirname(path.resolve(input))&&path.basename(input)==='report.json'){console.error('Output must be outside Skill and must not overwrite inputs');process.exit(2);}
await fs.mkdir(out,{recursive:true});
const report={html_sha256:createHash('sha256').update(await fs.readFile(input)).digest('hex'),scope:'automated Chromium checks only',layers:Object.fromEntries(['content','visual','layout','function','delivery'].map(k=>[k,{status:'not-run'}])),geometry:[],status:'not-run',engine:'Chromium',checks:[],screenshots:[],not_run:['Safari','iOS real device','Android real device','semantic/factual review','manual screenshot review']};
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
 const url=pathToFileURL(path.resolve(input)).href;
 await page.goto(url);await page.evaluate(()=>document.fonts.ready);
 const widths=[1440,1024,1001,1000,768,701,700,390,375,320];
 for(const width of [...widths,...widths.slice(0,-1).reverse()]){
  await page.setViewportSize({width,height:950});await page.waitForTimeout(120);
  const result=await page.evaluate(()=>{
   const visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';
   const overflow=[...document.querySelectorAll('main *')].filter(e=>visible(e)&&!e.closest('.qt-t-scroll-viewport')&&e.getBoundingClientRect().right>innerWidth+1).map(e=>e.tagName+'.'+e.className);
   const images=[...document.images].filter(i=>visible(i)&&(!i.complete||!i.naturalWidth||i.getBoundingClientRect().width<1||i.getBoundingClientRect().height<1)).map(i=>i.alt);
   const h1=document.querySelector('h1'),h2=document.querySelector('main h2'),h3=document.querySelector('main h3');
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
    for(const row of rows.values())if(row.length>1&&Math.max(...row.map(r=>r.bottom))-Math.min(...row.map(r=>r.bottom))>2)alignment.push({type:'group-bottom',row});
   }
   for(const group of document.querySelectorAll('.qt-t-media-group')){
    const rows=new Map();for(const fig of group.querySelectorAll('figure')){const r=rect(fig);const key=Math.round(r.y);if(!rows.has(key))rows.set(key,[]);rows.get(key).push(fig);}
    for(const row of rows.values())for(const selector of [':scope > :first-child','figcaption']){
     const boxes=row.map(f=>f.querySelector(selector)).filter(Boolean).map(rect);
     if(boxes.length>1&&(Math.max(...boxes.map(r=>r.y))-Math.min(...boxes.map(r=>r.y))>2||Math.max(...boxes.map(r=>r.bottom))-Math.min(...boxes.map(r=>r.bottom))>2))alignment.push({type:'media-slot/caption',selector,boxes});
    }
   }
   return {alignment,groups:[...document.querySelectorAll('[data-qt-group]')].map(g=>({id:g.id,box:rect(g),columns:getComputedStyle(g).gridTemplateColumns})),bodyWidth:document.documentElement.scrollWidth,overflow,images,overlaps,hit,h1:getComputedStyle(h1).fontSize,h2:h2?getComputedStyle(h2).fontSize:null,h3:h3?getComputedStyle(h3).fontSize:null,maxContent:document.querySelector('main').getBoundingClientRect().width};
  });
  check('layout-'+width,result.bodyWidth<=width+1&&!result.overflow.length&&!result.images.length&&!result.overlaps.length&&!result.hit.length&&!result.alignment.length&&result.maxContent<=1200.1&&result.h1===(width<=700?'31px':'38px')&&(!result.h2||result.h2==='26px')&&(!result.h3||result.h3==='16px'),result);
  report.geometry.push({width,...result});
  if([1440,390].includes(width)&&!report.screenshots.some(s=>s.endsWith(`page-${width}.png`))){
   await page.evaluate(()=>scrollTo(0,0));await page.evaluate(()=>new Promise(requestAnimationFrame));
   const file=path.join(out,`page-${width}.png`);await page.screenshot({path:file,fullPage:true});report.screenshots.push(file);
   for(const section of await page.locator('[data-module-id]').all()){const id=await section.getAttribute('data-module-id');const file=path.join(out,`module-${id}-${width}.png`);await section.screenshot({path:file,style:'#qt-official-header { visibility:hidden!important }'});report.screenshots.push(file);}
  }
 }
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
 const zoom=page.locator('[data-qt-zoom]').first();
 if(await zoom.count()){
  await zoom.click();const dialog=page.locator('.qt-t-lightbox');await dialog.locator('button[data-original]').click();
  const original=await dialog.locator('.qt-t-original').getAttribute('data-original');await page.keyboard.press('Escape');await page.waitForTimeout(80);
  check('image-original-focus',original==='true'&&await zoom.evaluate(e=>document.activeElement===e),'original size toggle and Escape return focus');
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
 report.network=networkAudit;
 check('official-network-scope',!networkAudit.blocked.some(r=>!['xhr','fetch','script','image','ping'].includes(r.kind)),{blocked:networkAudit.blocked});
 check('console',errors.length===0,{errors});
 report.layers.layout={status:report.checks.some(c=>c.id.startsWith('layout-')&&c.status==='fail')?'fail':'pass'};
 report.layers.function={status:report.checks.some(c=>!c.id.startsWith('layout-')&&c.status==='fail')?'fail':'pass',scope:'only interactions present on this page'};
 report.screenshot_sha256=Object.fromEntries(await Promise.all(report.screenshots.map(async f=>[path.basename(f),createHash('sha256').update(await fs.readFile(f)).digest('hex')])));
 report.status=report.checks.some(c=>c.status==='fail')?'fail':'pass';
 await context.close();
}catch(e){report.status=browser?'fail':'not-run';report.error=String(e);report.checks.push({id:browser?'browser-execution':'browser-runtime',status:browser?'fail':'not-run',evidence:String(e)});}
finally{if(browser)await browser.close();await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify({status:report.status,checks:report.checks.length,failed:report.checks.filter(c=>c.status==='fail'),error:report.error,report:path.join(out,'report.json')}));
process.exitCode=report.status==='pass'?0:1;
