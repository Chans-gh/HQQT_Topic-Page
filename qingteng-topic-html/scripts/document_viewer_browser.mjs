#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const css=fs.readFileSync(path.join(root,'assets/components/topic.css'),'utf8');
const runtime=fs.readFileSync(path.join(root,'assets/components/topic.js'),'utf8');
const body=`<main class="qt-t-topic"><section class="qt-section" data-module-id="M02"><h1>原稿浏览回归</h1>
 <div class="qt-t-document-viewer" data-qt-document-viewer data-expanded="false">
  <div class="qt-t-scroll-controls"><button class="qt-btn qt-btn-secondary" type="button" data-doc-prev>上一页</button><span data-doc-status role="status"></span><button class="qt-btn qt-btn-secondary" type="button" data-doc-next>下一页</button><button class="qt-btn qt-btn-secondary" type="button" data-doc-expand aria-expanded="false">完整展开</button></div>
  <div class="qt-t-document-viewer-layout"><nav class="qt-t-document-index" aria-label="原稿页码"><ol><li><a href="#DOC-01-P01"><span>01</span><strong>封面</strong></a></li><li><a href="#DOC-01-P02"><span>02</span><strong>内页</strong></a></li></ol></nav>
  <div class="qt-t-document-pages" tabindex="0" role="region" aria-label="原稿页面"><article id="DOC-01-P01" data-doc-page="1" style="min-height:650px"><h2>封面</h2><p>第一页一直保留。</p></article><article id="DOC-01-P02" data-doc-page="2" style="min-height:650px"><h2>内页</h2><p>第二页一直保留。</p></article></div></div>
 </div></section></main>`;
const documentFor=withScript=>`<!doctype html><meta charset="utf-8"><style>${css}</style>${body}${withScript?`<script>${runtime}<\/script>`:''}`;
const options={headless:true};
if(process.env.QT_CHROMIUM_EXECUTABLE)options.executablePath=process.env.QT_CHROMIUM_EXECUTABLE;
const browser=await chromium.launch(options);
try{
 const page=await browser.newPage({viewport:{width:390,height:720}});
 await page.setContent(documentFor(true),{waitUntil:'load'});
 const visible=await page.locator('[data-doc-page]').evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).display!=='none'&&!node.hidden));
 if(!visible.every(Boolean))throw new Error('viewer hid source pages');
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1))throw new Error('viewer caused page-level horizontal overflow');
 if(await page.locator('[data-doc-status]').textContent()!=='第 1 / 2 页')throw new Error('initial page status is wrong');
 await page.locator('[data-doc-next]').click();
 await page.waitForFunction(()=>document.querySelector('[data-doc-status]').textContent==='第 2 / 2 页');
 await page.waitForFunction(()=>document.querySelector('.qt-t-document-pages').scrollTop>100);
 await page.locator('[data-doc-expand]').click();
 if(await page.locator('[data-qt-document-viewer]').getAttribute('data-expanded')!=='true')throw new Error('complete expansion failed');
 if(await page.locator('.qt-t-document-pages').evaluate(node=>getComputedStyle(node).overflow)!=='visible')throw new Error('expanded viewer still clips pages');

 const fallback=await browser.newPage({javaScriptEnabled:false,viewport:{width:390,height:720}});
 await fallback.setContent(documentFor(false),{waitUntil:'load'});
 await fallback.locator('a[href="#DOC-01-P02"]').click();
 if(!fallback.url().endsWith('#DOC-01-P02'))throw new Error('no-script source-page anchor failed');
 const fallbackVisible=await fallback.locator('[data-doc-page]').evaluateAll(nodes=>nodes.map(node=>getComputedStyle(node).display!=='none'&&!node.hidden));
 if(!fallbackVisible.every(Boolean))throw new Error('no-script viewer hid source pages');
 await fallback.close();
 console.log('✅ Chromium original-document viewer checks passed');
} finally {
 await browser.close();
}
