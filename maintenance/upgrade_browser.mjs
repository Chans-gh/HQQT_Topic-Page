#!/usr/bin/env node
/** Synthetic upgrade matrix. Explicit runtime override; no real auth or image generation. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [dirArg,skillArg,baselineArg]=process.argv.slice(2);
if(!dirArg||!skillArg)throw Error('Usage: upgrade_browser.mjs OUTPUT_FROM_upgrade_regression SKILL [READ_ONLY_OLD_HTML]');
const dir=path.resolve(dirArg),skill=path.resolve(skillArg);
const loaded=await import(process.env.QT_PLAYWRIGHT_MODULE?pathToFileURL(process.env.QT_PLAYWRIGHT_MODULE).href:'playwright');
const {chromium}=loaded.chromium?loaded:loaded.default;
const browser=await chromium.launch({headless:true});const ctx=await browser.newContext({offline:true,reducedMotion:'reduce'});const page=await ctx.newPage();
const report={status:'not-run',checks:[],geometry:[],header:[],image_generation_calls:0,not_run:['real authenticated session','real devices','real image generation','real business retest']};
const headerOnly=process.argv.includes('--header-only');
if(headerOnly){const prior=JSON.parse(await fs.readFile(path.join(dir,'matrix-report.json'),'utf8'));await fs.writeFile(path.join(dir,'matrix-initial.json'),JSON.stringify(prior,null,2));report.geometry=prior.geometry;report.checks=prior.checks.filter(c=>!c.id.startsWith('T09-')&&!c.id.startsWith('header-')&&!c.id.startsWith('search-')&&c.id!=='console');}
const check=(id,pass,evidence)=>report.checks.push({id,status:pass?'pass':'fail',evidence});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const widths=[1440,1024,1001,1000,768,701,700,390,375,320];const roundtrip=[...widths,...widths.slice(0,-1).reverse()];
const css=await fs.readFile(path.join(skill,'assets/components/topic.css'),'utf8'),js=await fs.readFile(path.join(skill,'assets/components/topic.js'),'utf8');
const shell=await fs.readFile(path.join(skill,'assets/templates/public-shell.html'),'utf8');
const imageData=async name=>'data:image/svg+xml;base64,'+(await fs.readFile(path.join(skill,'assets/examples',name))).toString('base64');
const portrait=await imageData('document-demo.svg'),person=await imageData('person-wide-demo.svg'),wide=await imageData('workspace-demo.svg');
function wrap(content){return shell.replace(/<!-- QT_PAGE_CONTENT_START -->[\s\S]*?<!-- QT_PAGE_CONTENT_END -->/,`<!-- QT_PAGE_CONTENT_START --><main class="qt-t-topic qt-wrap qt-page">${content}</main><!-- QT_PAGE_CONTENT_END -->`).replace('</head>',`<style>${css}</style></head>`).replace('</body>',`<script>${js}</script></body>`);}
const frame=async()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
for(const n of (headerOnly?[]:[...Array(11).keys(),12])){
 const cards=(text)=>Array.from({length:n},(_,i)=>`<article class="qt-t-card" data-test-item><h3>对象${i+1}</h3><p>${text(i)}</p></article>`).join('')||'<p data-qt-empty>暂无内容</p>';
 const short=cards(()=> '核对结果。'),mixed=cards(i=>i%2?'核对真实材料中的单位与条件，保留完成操作和证据。'.repeat(8):'短说明。'),long=cards(()=> '核对真实材料中的单位与条件，保留完成操作和证据。'.repeat(15)+'LongUnbrokenEnglishString'.repeat(10));
 const scroll=(axis)=>`<div class="qt-t-scroll" data-axis="${axis}" data-expanded="false"><div class="qt-t-scroll-controls"><button data-scroll-prev>上一组</button><span data-scroll-status></span><button data-scroll-next>下一组</button><button data-scroll-expand>完整展开</button></div><div class="qt-t-scroll-viewport">${short}</div></div>`;
 const fragment=`<section><h1>数量与容量合成矩阵${n}</h1><h2>短文</h2><div data-test-count="${n}" class="qt-t-group" data-qt-group>${short}</div><h2>混合</h2><div data-test-count="${n}" class="qt-t-group" data-qt-group>${mixed}</div><h2>长文</h2><div data-test-count="${n}" class="qt-t-group" data-qt-group>${long}</div><div class="qt-t-fit qt-t-paper" data-qt-fit="media" id="media-fit"><figure class="qt-t-media"><img src="${portrait}" alt="合成文档"></figure><div><h3>独立解释</h3><p>核对输入口径与必要条件。</p></div></div><div class="qt-t-fit qt-t-paper" data-qt-fit="person" id="person-fit"><div><p>说明与操作不进入人物安全槽。</p></div><figure class="qt-t-person-slot"><img src="${person}" alt="合成人物示意"></figure></div><div class="qt-t-group qt-t-media-group" data-qt-group id="media-group"><figure class="qt-t-media"><button data-qt-zoom><img src="${portrait}" alt="竖图"></button><figcaption>短图注</figcaption></figure><figure class="qt-t-media"><img src="${wide}" alt="宽图"><figcaption>长图注，完整说明来源支持的范围和必要条件，不截断来换取底边对齐。</figcaption></figure></div>${scroll('x')}${scroll('y')}</section>`;
 const file=path.join(dir,`matrix-${n}.html`);await fs.writeFile(file,wrap(fragment));await page.goto(pathToFileURL(file).href);await page.evaluate(()=>document.fonts.ready);await frame();
 for(const width of roundtrip){
  await page.setViewportSize({width,height:950});await frame();
  const g=await page.evaluate(n=>{
   const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom};};
   const groups=[...document.querySelectorAll('[data-test-count]')].map(g=>({n:g.querySelectorAll('[data-test-item]').length,box:rect(g),parent:rect(g.parentElement),cols:getComputedStyle(g).gridTemplateColumns}));
   const images=[...document.querySelectorAll('main img')].map(i=>({alt:i.alt,...rect(i),loaded:i.complete&&i.naturalWidth>0}));
   const clipped=[...document.querySelectorAll('main h1,main h2,main h3,main p')].filter(e=>!e.closest('.qt-t-scroll-viewport')&&e.scrollWidth>e.clientWidth+2).map(e=>e.textContent.slice(0,20));
   return {n,width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,groups,images,clipped};
  },n);
  report.geometry.push(g);check(`T04-06-count-${n}-${width}-${report.geometry.length}`,!g.overflow&&!g.clipped.length&&g.groups.every(x=>x.n===n&&Math.abs(x.box.w-x.parent.w)<2)&&g.images.every(i=>i.loaded&&i.w>0&&i.h>0),{n,width});
  for(const region of await page.locator('.qt-t-scroll').all()){
   const view=region.locator('.qt-t-scroll-viewport');await view.focus();await page.keyboard.press('End');const end=await region.locator('[data-scroll-next]').isDisabled();await page.keyboard.press('Home');const start=await region.locator('[data-scroll-prev]').isDisabled();
   await region.locator('[data-scroll-expand]').click();await frame();const expanded=await view.evaluate(e=>getComputedStyle(e).maxHeight==='none'&&getComputedStyle(e).overflow==='visible');await region.locator('[data-scroll-expand]').click();await frame();
   const status=await region.locator('[data-scroll-status]').textContent();check(`scroll-${n}-${width}-${await region.getAttribute('data-axis')}`,start&&end&&expanded&&(n===0?status==='暂无内容':status.includes(`共 ${n} 项`)),{status});
  }
 }
 // Mutations, a narrow real parent, delayed image insertion and removal all use shared markers.
 await page.setViewportSize({width:1440,height:950});
 for(const mutation of ['edit','narrow','restore','reload-image','remove-media','remove-person']){
  await page.evaluate(m=>{
   const fit=document.querySelector('#media-fit'),p=fit.querySelector('p');
   if(m==='edit')p.textContent='连续编辑，保留完整操作和条件。'.repeat(30);
   if(m==='narrow')fit.parentElement.style.width='280px';
   if(m==='restore')fit.parentElement.style.width='';
   if(m==='reload-image'){const i=fit.querySelector('img'),src=i.src;i.removeAttribute('src');requestAnimationFrame(()=>{i.src=src;});}
   if(m==='remove-media')fit.querySelector('figure').remove();
   if(m==='remove-person')document.querySelector('#person-fit figure').remove();
  },mutation);await frame();await frame();
  const result=await page.evaluate(()=>({images:[...document.querySelectorAll('main img')].map(i=>({w:i.getBoundingClientRect().width,h:i.getBoundingClientRect().height,loaded:i.complete&&i.naturalWidth>0})),mediaCols:document.querySelector('#media-fit').dataset.layout,personCols:document.querySelector('#person-fit').dataset.layout,overflow:document.documentElement.scrollWidth>innerWidth+1}));
  check(`mutation-${n}-${mutation}`,!result.overflow&&result.images.every(i=>i.w>0&&i.h>0&&i.loaded)&&(mutation!=='remove-media'||result.mediaCols==='stacked')&&(mutation!=='remove-person'||result.personCols==='stacked'),result);
 }
}
// Header uses a synthetic same-origin page and a no-network jQuery ajax substitute.
await ctx.close();
for(const state of ['anonymous','authenticated','long-name','failure','timeout']){
 const context=await browser.newContext({reducedMotion:'reduce'});await context.route('**/*',route=>route.request().url()==='https://synthetic.test/fixture'?route.fulfill({contentType:'text/html',body:wrap('<h1>认证替身</h1>')}):route.request().url().startsWith('https://www.hqqt.com/search/cover')?new Promise(()=>{}):route.abort());
 await context.addInitScript(state=>{
  document.cookie='passport=synthetic-only; path=/';
  let value;
  Object.defineProperty(window,'jQuery',{configurable:true,get(){return value;},set(v){value=v;v.ajax=function(options){window.__qtAjaxTimeout=options.timeout;if(state==='timeout'){setTimeout(()=>options.error({},'timeout'),options.timeout);return;}if(state==='failure'){options.error({},'error');return;}options.success(state==='anonymous'?{status:0}:{status:1,data:[{nickName:state==='long-name'?'超长昵称<script>不是HTML</script>'.repeat(8):'合成学员',faceUrl:'https://invalid.example/avatar.png'}]});};}});
 },state);
 const p=await context.newPage();await p.clock.install();await p.goto('https://synthetic.test/fixture');if(state==='timeout')await p.clock.fastForward(11000);
 const expected=['authenticated','long-name'].includes(state)?'authenticated':['failure','timeout'].includes(state)?'unavailable':'anonymous';
 for(const width of [...new Set([320,375,390,699,700,701,999,1000,1001,1024,1240,1440])]){
  await p.setViewportSize({width,height:950});await p.clock.runFor(30);
  const g=await p.locator('#qt-official-header').evaluate(root=>{
   const controls=[...root.querySelectorAll('.logo a,.search-block,.login-btn-01,.user-info,.qt-menu-button')].filter(e=>e.getClientRects().length);
   const rect=e=>{const r=e.getBoundingClientRect();return {label:e.className,left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};};const boxes=controls.map(rect),overlap=[];
   for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],b=boxes[j];if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)overlap.push([a.label,b.label]);}
   return {auth:root.dataset.auth,boxes,overlap,height:root.getBoundingClientRect().height,overflow:boxes.filter(r=>r.left<0||r.right>innerWidth+1),name:root.querySelector('.user-name').textContent,unsafe:!!root.querySelector('.user-name script')};
  });report.header.push({state,width,...g});check(`T09-${state}-${width}`,g.auth===expected&&g.height===60&&!g.overlap.length&&!g.overflow.length&&!g.unsafe,{auth:g.auth,overlap:g.overlap,overflow:g.overflow});
 }
 await p.setViewportSize({width:320,height:950});const menu=p.locator('.qt-menu-button');await menu.click();await p.keyboard.press('Escape');check('header-menu-focus-'+state,await menu.getAttribute('aria-expanded')==='false'&&await menu.evaluate(e=>e===document.activeElement),'Escape restores opener');
 if(['authenticated','long-name'].includes(state)){const user=p.locator('.user-info');await user.click();const bounds=await p.locator('#qt-official-user').boundingBox();await p.keyboard.press('Escape');check('header-auth-menu-'+state,bounds.x>=0&&bounds.x+bounds.width<=321&&await user.evaluate(e=>e===document.activeElement),bounds);}
 const search=p.locator('.search-block');await search.click();await p.clock.fastForward(13000);check('search-timeout-fallback-'+state,await p.locator('.qt-search-toolbar a').count()>0&&await p.locator('#qt-official-header').getAttribute('data-search')==='timeout','iframe never resolves; official fallback remains');await p.keyboard.press('Escape');check('search-focus-'+state,await search.evaluate(e=>e===document.activeElement),'Escape returns focus');
 await p.screenshot({path:path.join(dir,`header-${state}-320.png`)});await context.close();
}
if(baselineArg&&!baselineArg.startsWith('--')){const c=await browser.newContext({offline:true});const p=await c.newPage();await p.setViewportSize({width:320,height:950});await p.goto(pathToFileURL(path.resolve(baselineArg)).href);await p.evaluate(()=>document.fonts.ready);report.old_header=await p.locator('#qt-official-header').evaluate(r=>{const a=r.querySelector('.login-btn-01').getBoundingClientRect(),b=r.querySelector('.qt-menu-button').getBoundingClientRect();return {login:{x:a.x,width:a.width,right:a.right},menu:{x:b.x,width:b.width,right:b.right},overlap:Math.min(a.right,b.right)-Math.max(a.left,b.left)};});await p.screenshot({path:path.join(dir,'old-header-320-readonly.png')});await c.close();}
check('console',errors.length===0,errors);report.status=report.checks.some(c=>c.status==='fail')?'fail':'pass';
await browser.close();await fs.writeFile(path.join(dir,'matrix-report.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:report.status,checks:report.checks.length,geometry:report.geometry.length,header:report.header.length,failed:report.checks.filter(c=>c.status==='fail')}));process.exitCode=report.status==='pass'?0:1;
