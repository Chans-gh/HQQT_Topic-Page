/** Header-specific browser checks; remote service evidence is reported separately. */
export const officialHost=host=>/(^|\.)hqqt\.com$|(^|\.)hqwx\.com$/.test(host)||host==='oss-hqwx-edu24ol.oss-cn-beijing.aliyuncs.com';
export const safeUrl=value=>{const url=new URL(value);return url.origin+url.pathname;};
export async function installNetworkPolicy(context,offline=false){
 const audit={mode:offline?'offline-fallback':'online',allowed:[],blocked:[],responses:[]};
 await context.route(/^https?:/,async route=>{
  const request=route.request(),url=new URL(request.url());
  const allowed=url.protocol==='https:'&&officialHost(url.hostname);
  const entry={url:safeUrl(url.href),kind:request.resourceType()};
  if(allowed){audit.allowed.push(entry);if(offline)return route.abort();return route.continue();}
  audit.blocked.push(entry);return route.abort();
 });
 return audit;
}

export async function checkOfficialHeader(page,check,report,out,offline=false){
 const header=page.locator('#qt-official-header');
 check('official-header-init',await header.count()===1&&await header.getAttribute('data-runtime')==='ready',await header.getAttribute('data-version'));
 await page.evaluate(()=>window.QingTengHeader.init());
 check('official-header-idempotent',await header.count()===1&&await page.locator('#qt-header-jquery').count()===1,'one mounted header and pinned jQuery');
 const links=await header.locator('a[href]').evaluateAll(es=>es.map(e=>({label:e.textContent.trim()||e.title||e.getAttribute('aria-label'),href:e.href})));
 check('official-links',links.every(e=>e.href.startsWith('https://'))&&links.some(e=>e.href==='https://www.hqqt.com/course/1')&&links.some(e=>e.href==='https://www.hqqt.com/live'),links);
 for(const width of [1440,1240,1024,1000,768,700,390,375,320]){
  await page.setViewportSize({width,height:950});
  const bounds=await header.evaluate(root=>{
   const box=root.getBoundingClientRect(),inner=root.querySelector('.main-width').getBoundingClientRect();
   const overflow=[...root.querySelectorAll('.header-content a,.header-content button')].filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>innerWidth+1;}).map(e=>e.className);
   const controls=[...root.querySelectorAll('.logo a,.header-right .search-block,.header-right .login-btn-01,.header-right .user-info,.qt-menu-button')].filter(e=>e.getClientRects().length);
   const intersections=[];
   for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){const a=controls[i].getBoundingClientRect(),b=controls[j].getBoundingClientRect();if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)intersections.push([controls[i].className,controls[j].className]);}
   const learning=root.querySelector('.header-right .learning-center');
   return {height:box.height,width:inner.width,overflow,intersections,mobileLearningHidden:!learning.getClientRects().length};
  });
  check('header-size-'+width,bounds.height===60&&bounds.width<=1200.1&&!bounds.overflow.length&&!bounds.intersections.length&&(width>700||bounds.mobileLearningHidden),bounds);
 }
 await page.setViewportSize({width:390,height:950});
 const menu=header.locator('.qt-menu-button');await menu.click();
 check('header-h5-menu',await menu.getAttribute('aria-expanded')==='true'&&await header.locator('#qt-official-nav').isVisible(),'official navigation retained on mobile');
 await page.keyboard.press('Escape');
 check('header-h5-menu-close',await menu.getAttribute('aria-expanded')==='false'&&await menu.evaluate(e=>document.activeElement===e),'Escape closes and restores focus');
 const search=header.locator('.search-block');await search.click();
 const dialog=header.locator('#qt-official-search');
 check('official-search-open',await dialog.evaluate(e=>e.open)&&await dialog.locator('iframe').getAttribute('src')==='https://www.hqqt.com/search/cover?third=1','official iframe, no prototype search interception');
 if(!offline){
  await dialog.locator('iframe').contentFrame().locator('input').first().waitFor({state:'visible',timeout:20000}).catch(()=>{});
  const frames=page.frames().filter(f=>f.url().startsWith('https://www.hqqt.com/search/cover'));
  const inputs=frames.length?await frames[0].locator('input').count().catch(()=>0):0;
  report.official_services={search:{status:inputs>0?'pass':'unavailable',requested:true,frame_present:!!frames.length,input_count:inputs},account:{state:await header.getAttribute('data-auth'),real_authenticated_session_tested:false}};
  if(!inputs)report.not_run.push('official search input unavailable within 20s; fallback link remains usable');
 }else report.official_services={mode:'offline-fallback',real_service_validation:false};
 await dialog.locator('.qt-search-close').click();
 check('official-search-close',!await dialog.evaluate(e=>e.open)&&await search.evaluate(e=>document.activeElement===e),'close restores focus');
 await page.setViewportSize({width:1440,height:950});
 await page.evaluate(()=>window.scrollTo(0,300));
 check('header-sticky',await header.evaluate(e=>Math.abs(e.getBoundingClientRect().top)<1),'60px sticky header');
 await page.evaluate(()=>window.scrollTo(0,0));
 report.not_run.push('real authenticated official account on deployment domain');
}
